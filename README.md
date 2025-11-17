# Import de documents dans Google File Search

Ce projet permet d'importer tous les documents du répertoire `Data` dans Google File Search pour pouvoir les interroger avec l'API Gemini.

## Prérequis

- Python 3.8 ou supérieur
- Une clé API Google Gemini (niveau Tier 1 recommandé pour 10 Go de stockage)
- Les documents à importer dans le répertoire `Data`

## Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Créer un fichier `.env` à partir de `.env.example` :
```bash
# Sur Windows (PowerShell)
Copy-Item .env.example .env

# Sur Linux/Mac
cp .env.example .env
```

3. Éditer le fichier `.env` et ajouter votre clé API et le STORE_ID :
```env
GEMINI_API_KEY=votre_cle_api_google_gemini
STORE_ID=appelsdoffrescd21-zgoa3k9yv6bx
```

**Note** : 
- Le `STORE_ID` est optionnel. S'il n'est pas défini, le script vous demandera de l'entrer à chaque exécution.
- Vous pouvez utiliser soit l'ID seul (`appelsdoffrescd21-zgoa3k9yv6bx`) soit le format complet (`fileSearchStores/appelsdoffrescd21-zgoa3k9yv6bx`)

## Utilisation

### 1. Importer les documents

Lancer le script d'import :
```bash
python import_documents.py
```

Le script va :
- Scanner récursivement le répertoire `Data`
- Lister tous les fichiers supportés (PDF, DOCX, XLSX, etc.)
- Créer un File Search Store
- Importer tous les documents
- Afficher un résumé de l'import

**Note** : Le nom du magasin créé sera affiché à la fin. Vous en aurez besoin pour interroger les documents.

### 2. Interroger les documents

Une fois les documents importés, vous pouvez les interroger :
```bash
python query_documents.py
```

Entrez le nom du File Search Store (format: `fileSearchStores/xxxxx`) puis posez vos questions.

## Formats de fichiers supportés

- **Documents** : PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT
- **Textes** : TXT, MD, RTF, HTML, XML
- **Données** : CSV, JSON

Taille maximale par fichier : 100 Mo

## Limites

Avec un abonnement Tier 1 :
- **Stockage total** : 10 Go
- **Taille max par fichier** : 100 Mo
- **Recommandation** : < 20 Go par magasin pour des performances optimales

## Configuration du chunking

Le script utilise une configuration de chunking personnalisée pour segmenter les documents :

- **`max_tokens_per_chunk`** : 200 jetons par segment (configurable dans `import_documents.py`)
- **`max_overlap_tokens`** : 20 jetons de chevauchement entre segments (configurable)

Ces paramètres peuvent être modifiés dans le fichier `import_documents.py` en éditant la variable `CHUNKING_CONFIG`. Pour utiliser les paramètres par défaut de l'API, définissez `CHUNKING_CONFIG = None`.

## Tarification

- **Embeddings à l'indexation** : 0,15 $ par million de jetons
- **Stockage** : Gratuit
- **Embeddings à la requête** : Gratuit
- **Jetons de documents récupérés** : Facturés comme jetons de contexte standards

## Exemples de questions

- "Quelles sont les conditions particulières mentionnées dans les documents ?"
- "Résumez les offres de COLLECTEAM"
- "Quels sont les tarifs proposés par RELYENS ?"
- "Listez tous les documents liés à la santé"

## Structure du projet

```
Alcega/
├── Data/                          # Répertoire contenant les documents à importer
│   ├── Enveloppe_2_COLLECTEAM/
│   ├── Enveloppe_3_ALTERNATIVE COURTAGE/
│   └── ...
├── import_documents.py            # Script d'import des documents
├── query_documents.py             # Script d'interrogation des documents
├── list_stores.py                 # Script pour lister les magasins File Search
├── requirements.txt               # Dépendances Python
├── .env                           # Variables d'environnement (non versionné)
├── .env.example                   # Exemple de configuration
├── .gitignore                     # Fichiers à ignorer par Git
└── README.md                      # Documentation
```

## Dépannage

### Erreur : "GEMINI_API_KEY non trouvée"
Vérifiez que le fichier `.env` existe et contient votre clé API.

### Erreur : "Fichier trop volumineux"
Les fichiers de plus de 100 Mo ne peuvent pas être importés. Divisez-les ou compressez-les.

### Erreur lors de l'import
Vérifiez votre quota et votre abonnement. Avec Tier 1, vous avez 10 Go de stockage total.

### Erreur : "FileSearchStore name does not match expected format"
Vérifiez que le `STORE_ID` dans votre `.env` est au bon format (sans espaces, caractères spéciaux). Le script nettoie automatiquement le format, mais assurez-vous qu'il n'y a pas de caractères invalides.

### Citations non affichées
Les citations peuvent ne pas s'afficher selon la structure de la réponse de l'API. Le script affiche des informations de debug pour aider à identifier le problème.

