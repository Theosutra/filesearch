"""
Script pour importer tous les documents du répertoire Data dans Google File Search
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Optional
from google import genai
from google.genai import types
import dotenv

# Forcer l'encodage UTF-8 pour éviter les problèmes avec les caractères accentués
if sys.platform == 'win32':
    # Sur Windows, forcer UTF-8 pour les sorties
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Charger les variables d'environnement
dotenv.load_dotenv()

# Configuration
DATA_DIR = Path("Data")
SUPPORTED_EXTENSIONS = {
    # Documents
    '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
    # Textes
    '.txt', '.md', '.rtf', '.html', '.xml',
    # Autres formats supportés
    '.csv', '.json'
}

# Taille maximale par fichier (100 Mo)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Paramètres de chunking (optionnels - l'API gère automatiquement si non spécifiés)
# Définir à None pour utiliser les paramètres par défaut de l'API
CHUNKING_CONFIG = {
    'white_space_config': {
        'max_tokens_per_chunk': 200,  # Nombre maximal de jetons par segment
        'max_overlap_tokens': 20      # Nombre maximal de jetons qui se chevauchent
    }
}
# Pour désactiver le chunking personnalisé, mettre CHUNKING_CONFIG = None

# Mapping des extensions vers les types MIME
MIME_TYPES = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.rtf': 'text/rtf',
    '.html': 'text/html',
    '.xml': 'application/xml',
    '.csv': 'text/csv',
    '.json': 'application/json',
}


def get_mime_type(file_path: Path) -> str:
    """Détermine le type MIME d'un fichier basé sur son extension"""
    ext = file_path.suffix.lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')


def get_all_documents(data_dir: Path) -> List[Path]:
    """Récupère tous les fichiers supportés dans le répertoire Data"""
    documents = []
    
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_size = file_path.stat().st_size
                if file_size <= MAX_FILE_SIZE:
                    documents.append(file_path)
                else:
                    print(f"⚠️  Fichier trop volumineux ignoré: {file_path} ({file_size / 1024 / 1024:.2f} Mo)")
    
    return sorted(documents)


def create_file_search_store(client: genai.Client, store_name: str) -> str:
    """Crée un nouveau File Search Store"""
    print(f"📦 Création du magasin File Search: {store_name}")
    try:
        file_search_store = client.file_search_stores.create(
            config={'display_name': store_name}
        )
        print(f"✅ Magasin créé: {file_search_store.name}")
        return file_search_store.name
    except Exception as e:
        print(f"❌ Erreur lors de la création du magasin: {e}")
        raise


def upload_file_to_store(
    client: genai.Client,
    file_path: Path,
    store_name: str,
    max_retries: int = 3
) -> Optional[str]:
    """Upload et importe un fichier dans le File Search Store"""
    relative_path = file_path.relative_to(DATA_DIR)
    # Utiliser as_posix() pour obtenir un chemin avec des slashes normaux
    display_name = relative_path.as_posix()
    
    # Normaliser le display_name pour éviter les problèmes d'encodage ASCII
    # Le SDK semble avoir des problèmes avec les caractères accentués dans display_name
    import unicodedata
    # Essayer d'abord avec le nom original, mais avoir un fallback
    safe_display_name = unicodedata.normalize('NFKD', display_name)
    # Si le nom contient des caractères non-ASCII, créer une version ASCII-safe
    try:
        safe_display_name.encode('ascii')
        # Pas de problème, utiliser le nom original
        final_display_name = display_name
    except UnicodeEncodeError:
        # Problème d'encodage, utiliser une version sans accents
        final_display_name = safe_display_name.encode('ascii', 'ignore').decode('ascii')
        print(f"  ⚠️  Nom simplifié pour éviter les problèmes d'encodage: {final_display_name}")
    
    try:
        # Déterminer le type MIME du fichier
        mime_type = get_mime_type(file_path)
        
        # Préparer la configuration
        upload_config = {
            'display_name': final_display_name,
            'mime_type': mime_type
        }
        
        # Ajouter la configuration de chunking si elle est définie
        if CHUNKING_CONFIG is not None:
            upload_config['chunking_config'] = CHUNKING_CONFIG
        
        # Ouvrir le fichier en mode binaire pour éviter les problèmes d'encodage du chemin
        # Le SDK peut accepter soit un chemin (string/Path), soit un objet fichier
        with open(file_path, 'rb') as file_obj:
            operation = client.file_search_stores.upload_to_file_search_store(
                file=file_obj,
                file_search_store_name=store_name,
                config=upload_config
            )
        
        # Attendre la fin de l'opération
        retry_count = 0
        while not operation.done:
            time.sleep(2)
            try:
                operation = client.operations.get(operation)
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Erreur lors de l'import de {display_name}: {e}")
                    return None
                time.sleep(5)
        
        if hasattr(operation, 'response') and operation.response:
            file_name = operation.response.name if hasattr(operation.response, 'name') else "importé"
            return file_name
        return "importé"
        
    except UnicodeEncodeError as e:
        # Si erreur d'encodage malgré la normalisation, essayer avec un nom encore plus simplifié
        print(f"⚠️  Erreur d'encodage persistante pour {display_name}, nouvelle tentative...")
        # Créer un nom de fichier sans accents pour le display_name
        import unicodedata
        safe_name = unicodedata.normalize('NFKD', display_name).encode('ascii', 'ignore').decode('ascii')
        try:
            # Déterminer le type MIME du fichier
            mime_type = get_mime_type(file_path)
            
            # Préparer la configuration
            upload_config = {
                'display_name': safe_name,
                'mime_type': mime_type
            }
            
            # Ajouter la configuration de chunking si elle est définie
            if CHUNKING_CONFIG is not None:
                upload_config['chunking_config'] = CHUNKING_CONFIG
            
            with open(file_path, 'rb') as file_obj:
                operation = client.file_search_stores.upload_to_file_search_store(
                    file=file_obj,
                    file_search_store_name=store_name,
                    config=upload_config
                )
                # Attendre la fin de l'opération
                retry_count = 0
                while not operation.done:
                    time.sleep(2)
                    try:
                        operation = client.operations.get(operation)
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"❌ Erreur lors de l'import de {safe_name}: {e}")
                            return None
                        time.sleep(5)
                
                if hasattr(operation, 'response') and operation.response:
                    file_name = operation.response.name if hasattr(operation.response, 'name') else "importé"
                    return file_name
                return "importé"
        except Exception as e2:
            print(f"❌ Erreur lors de l'upload de {display_name}: {e2}")
            return None
    except Exception as e:
        print(f"❌ Erreur lors de l'upload de {display_name}: {e}")
        return None


def main():
    """Fonction principale"""
    # Vérifier la clé API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Erreur: GEMINI_API_KEY non trouvée dans les variables d'environnement")
        print("   Créez un fichier .env avec: GEMINI_API_KEY=votre_cle")
        return
    
    # Initialiser le client
    client = genai.Client(api_key=api_key)
    
    # Vérifier que le répertoire Data existe
    if not DATA_DIR.exists():
        print(f"❌ Le répertoire {DATA_DIR} n'existe pas")
        return
    
    # Récupérer tous les documents
    print(f"🔍 Recherche des documents dans {DATA_DIR}...")
    documents = get_all_documents(DATA_DIR)
    
    if not documents:
        print("❌ Aucun document trouvé")
        return
    
    print(f"✅ {len(documents)} document(s) trouvé(s)")
    
    # Afficher la liste des documents
    print("\n📄 Documents à importer:")
    for i, doc in enumerate(documents, 1):
        size_mb = doc.stat().st_size / 1024 / 1024
        print(f"  {i}. {doc.relative_to(DATA_DIR)} ({size_mb:.2f} Mo)")
    
    # Demander confirmation
    response = input(f"\n❓ Voulez-vous importer ces {len(documents)} documents ? (o/n): ")
    if response.lower() not in ['o', 'oui', 'y', 'yes']:
        print("❌ Import annulé")
        return
    
    # Créer ou réutiliser un magasin File Search
    store_name = "Appels-d-offres-CD21"
    store_name_id = None
    
    # Vérifier si un magasin existe déjà
    try:
        stores = list(client.file_search_stores.list())
        for store in stores:
            if hasattr(store, 'display_name') and store.display_name == store_name:
                store_name_id = store.name
                print(f"✅ Magasin existant trouvé: {store_name_id}")
                reuse = input("   Voulez-vous utiliser ce magasin existant ? (o/n): ")
                if reuse.lower() not in ['o', 'oui', 'y', 'yes']:
                    store_name_id = None
                break
    except Exception as e:
        print(f"⚠️  Impossible de lister les magasins existants: {e}")
    
    # Créer un nouveau magasin si nécessaire
    if not store_name_id:
        try:
            store_name_id = create_file_search_store(client, store_name)
        except Exception as e:
            print(f"❌ Impossible de créer le magasin: {e}")
            return
    
    # Importer les documents
    print(f"\n📤 Import de {len(documents)} document(s)...")
    successful = 0
    failed = 0
    
    for i, doc_path in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] Import de: {doc_path.relative_to(DATA_DIR)}")
        result = upload_file_to_store(client, doc_path, store_name_id)
        
        if result:
            successful += 1
            print(f"  ✅ Importé avec succès")
        else:
            failed += 1
            print(f"  ❌ Échec de l'import")
        
        # Petite pause pour éviter de surcharger l'API
        if i < len(documents):
            time.sleep(1)
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DE L'IMPORT")
    print("="*60)
    print(f"✅ Documents importés avec succès: {successful}")
    print(f"❌ Documents en échec: {failed}")
    print(f"📦 Magasin File Search: {store_name_id}")
    print("\n💡 Vous pouvez maintenant utiliser ce magasin pour interroger vos documents !")


if __name__ == "__main__":
    main()

