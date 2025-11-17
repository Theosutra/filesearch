"""
Script pour interroger les documents importés dans File Search
"""
import os
from google import genai
from google.genai import types
import dotenv

# Charger les variables d'environnement
dotenv.load_dotenv()


def query_documents(question: str, store_name: str):
    """Pose une question aux documents dans le File Search Store"""
    # Vérifier la clé API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Erreur: GEMINI_API_KEY non trouvée dans les variables d'environnement")
        return
    
    # Valider le format du store_name
    if not store_name or not store_name.startswith('fileSearchStores/'):
        print(f"❌ Erreur: Format de store_name invalide: {store_name}")
        print("   Le format attendu est: fileSearchStores/xxxxx")
        return
    
    # Initialiser le client
    client = genai.Client(api_key=api_key)
    
    try:
        # Générer la réponse avec File Search
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=question,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )]
            )
        )
        
        print("\n" + "="*60)
        print("💬 RÉPONSE")
        print("="*60)
        print(response.text)
        
        # Afficher les citations si disponibles
        citations_found = False
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            
            # Méthode 1: Via grounding_metadata
            if hasattr(candidate, 'grounding_metadata'):
                grounding = candidate.grounding_metadata
                
                # Essayer grounding_chunks
                if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                    citations_found = True
                    print("\n" + "="*60)
                    print("📚 CITATIONS")
                    print("="*60)
                    for i, chunk in enumerate(grounding.grounding_chunks, 1):
                        citation_text = None
                        citation_info = {}
                        
                        # Explorer toutes les propriétés du chunk
                        if hasattr(chunk, 'retrieved_context'):
                            ctx = chunk.retrieved_context
                            # Essayer toutes les propriétés possibles
                            for attr in ['uri', 'file_uri', 'display_name', 'file_name', 'name', 'title']:
                                if hasattr(ctx, attr):
                                    value = getattr(ctx, attr)
                                    if value:
                                        citation_info[attr] = value
                                        if not citation_text:
                                            citation_text = str(value)
                        
                        # Essayer directement sur le chunk
                        if not citation_text:
                            for attr in ['uri', 'file_uri', 'display_name', 'file_name', 'name', 'title', 'source']:
                                if hasattr(chunk, attr):
                                    value = getattr(chunk, attr)
                                    if value:
                                        citation_info[attr] = value
                                        if not citation_text:
                                            citation_text = str(value)
                        
                        # Si toujours rien, afficher les propriétés disponibles pour debug
                        if not citation_text:
                            # Essayer de convertir en dict pour voir toutes les propriétés
                            try:
                                if hasattr(chunk, '__dict__'):
                                    chunk_dict = chunk.__dict__
                                    citation_text = f"Chunk {i} (propriétés: {list(chunk_dict.keys())})"
                                else:
                                    citation_text = f"Chunk {i} (propriétés: {[a for a in dir(chunk) if not a.startswith('_')]})"
                            except:
                                citation_text = f"Chunk {i} - Structure inconnue"
                        
                        # Afficher la citation
                        if citation_info:
                            # Extraire le nom de fichier si disponible
                            file_name = citation_info.get('display_name') or citation_info.get('file_name') or citation_info.get('name') or citation_info.get('uri', '').split('/')[-1]
                            print(f"{i}. {file_name}")
                            if len(citation_info) > 1:
                                # Afficher les autres infos en petit
                                other_info = {k: v for k, v in citation_info.items() if k not in ['display_name', 'file_name', 'name']}
                                if other_info:
                                    print(f"   ({', '.join([f'{k}: {v}' for k, v in other_info.items()])})")
                        else:
                            print(f"{i}. {citation_text}")
                
                # Essayer web (si disponible)
                if hasattr(grounding, 'web') and grounding.web:
                    print("\n🌐 Sources web:")
                    for i, web_source in enumerate(grounding.web, 1):
                        uri = getattr(web_source, 'uri', 'URL inconnue')
                        title = getattr(web_source, 'title', '')
                        print(f"  {i}. {title} - {uri}")
            
            # Méthode 2: Via retrieved_context directement
            if hasattr(candidate, 'retrieved_context') and candidate.retrieved_context:
                citations_found = True
                if not citations_found:
                    print("\n" + "="*60)
                    print("📚 CITATIONS (via retrieved_context)")
                    print("="*60)
                for i, ctx in enumerate(candidate.retrieved_context, 1):
                    citation_text = "Source inconnue"
                    if hasattr(ctx, 'uri') and ctx.uri:
                        citation_text = ctx.uri
                    elif hasattr(ctx, 'file_uri') and ctx.file_uri:
                        citation_text = ctx.file_uri
                    elif hasattr(ctx, 'display_name') and ctx.display_name:
                        citation_text = ctx.display_name
                    print(f"{i}. {citation_text}")
        
        # Si aucune citation trouvée, afficher un message
        if not citations_found:
            print("\n" + "="*60)
            print("📚 CITATIONS")
            print("="*60)
            print("⚠️  Aucune citation disponible dans la réponse.")
            
            # Afficher les métadonnées brutes pour debug
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                print("\n🔍 Debug - Exploration de la structure:")
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if grounding:
                        print(f"   ✓ grounding_metadata trouvé")
                        if hasattr(grounding, 'grounding_chunks') and grounding.grounding_chunks:
                            print(f"   ✓ {len(grounding.grounding_chunks)} chunk(s) trouvé(s)")
                            # Afficher la structure du premier chunk
                            first_chunk = grounding.grounding_chunks[0]
                            print(f"   - Structure du premier chunk:")
                            print(f"     Type: {type(first_chunk)}")
                            print(f"     Propriétés: {[a for a in dir(first_chunk) if not a.startswith('_')]}")
                            if hasattr(first_chunk, '__dict__'):
                                print(f"     Valeurs: {first_chunk.__dict__}")
                        else:
                            print(f"   ✗ Pas de grounding_chunks")
                    else:
                        print(f"   ✗ grounding_metadata est None")
                else:
                    print(f"   ✗ Pas de grounding_metadata")
        
    except Exception as e:
        print(f"❌ Erreur lors de la requête: {e}")


def normalize_store_name(store_name: str) -> str:
    """Normalise le nom du magasin au format attendu par l'API"""
    if not store_name:
        raise ValueError("Le nom du magasin ne peut pas être vide")
    
    store_name = store_name.strip()
    
    # Supprimer les espaces et caractères de fin de ligne
    store_name = store_name.replace(' ', '').replace('\n', '').replace('\r', '')
    
    # Si le nom commence déjà par fileSearchStores/, vérifier le format
    if store_name.startswith('fileSearchStores/'):
        # Extraire l'ID après le préfixe
        store_id = store_name.replace('fileSearchStores/', '').strip()
        if not store_id:
            raise ValueError("L'ID du magasin est vide après le préfixe fileSearchStores/")
        # Nettoyer l'ID (supprimer caractères invalides)
        store_id = ''.join(c for c in store_id if c.isalnum() or c in ['-', '_'])
        if len(store_id) > 100:  # Limite de longueur de l'API
            raise ValueError(f"L'ID du magasin est trop long ({len(store_id)} caractères, max 100)")
        return f'fileSearchStores/{store_id}'
    
    # Sinon, ajouter le préfixe
    if not store_name:
        raise ValueError("L'ID du magasin ne peut pas être vide")
    
    # Nettoyer l'ID (supprimer caractères invalides)
    store_id = ''.join(c for c in store_name if c.isalnum() or c in ['-', '_'])
    if len(store_id) > 100:  # Limite de longueur de l'API
        raise ValueError(f"L'ID du magasin est trop long ({len(store_id)} caractères, max 100)")
    
    return f'fileSearchStores/{store_id}'


def main():
    """Fonction principale"""
    # Essayer de récupérer le STORE_ID depuis les variables d'environnement
    store_input = os.getenv('STORE_ID') or os.getenv('FILE_SEARCH_STORE_ID')
    
    if store_input:
        # Nettoyer le STORE_ID (supprimer espaces, retours à la ligne, etc.)
        store_input = store_input.strip().replace('\n', '').replace('\r', '')
        print(f"✅ STORE_ID trouvé dans .env: '{store_input}' (longueur: {len(store_input)})")
    else:
        # Si pas dans .env, demander à l'utilisateur
        store_input = input("📦 Nom du File Search Store (ex: fileSearchStores/xxxxx ou juste xxxxx): ").strip()
    
    if not store_input:
        print("❌ Nom du magasin requis")
        print("   Ajoutez STORE_ID=votre_store_id dans votre fichier .env")
        return
    
    # Normaliser le nom du magasin
    try:
        store_name = normalize_store_name(store_input)
        print(f"✅ Utilisation du magasin: {store_name}")
    except ValueError as e:
        print(f"❌ Erreur de format du STORE_ID: {e}")
        print(f"   Valeur actuelle: '{store_input}'")
        print("   Format attendu: appelsdoffrescd21-zgoa3k9yv6bx ou fileSearchStores/appelsdoffrescd21-zgoa3k9yv6bx")
        return
    
    print("\n💡 Tapez 'quit' ou 'exit' pour quitter")
    print("="*60)
    
    while True:
        question = input("\n❓ Votre question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 Au revoir !")
            break
        
        if not question:
            continue
        
        query_documents(question, store_name)


if __name__ == "__main__":
    main()

