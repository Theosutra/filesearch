"""
Script pour lister tous les File Search Stores existants
"""
import os
from google import genai
import dotenv

# Charger les variables d'environnement
dotenv.load_dotenv()


def list_file_search_stores():
    """Liste tous les File Search Stores"""
    # Vérifier la clé API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Erreur: GEMINI_API_KEY non trouvée dans les variables d'environnement")
        return
    
    # Initialiser le client
    client = genai.Client(api_key=api_key)
    
    try:
        print("🔍 Recherche des File Search Stores...\n")
        
        stores = list(client.file_search_stores.list())
        
        if not stores:
            print("❌ Aucun File Search Store trouvé")
            return
        
        print(f"✅ {len(stores)} magasin(s) trouvé(s):\n")
        print("="*60)
        
        for i, store in enumerate(stores, 1):
            print(f"\n{i}. {store.display_name if hasattr(store, 'display_name') else 'Sans nom'}")
            print(f"   Nom: {store.name}")
            if hasattr(store, 'create_time'):
                print(f"   Créé le: {store.create_time}")
        
        print("\n" + "="*60)
        print("\n💡 Utilisez le 'Nom' (format: fileSearchStores/xxxxx) dans query_documents.py")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des magasins: {e}")


if __name__ == "__main__":
    list_file_search_stores()

