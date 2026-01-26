# Agent MCP Article Summarizer

Application Python utilisant FastAPI, LangChain et LangGraph pour consulter des serveurs MCP (Model Context Protocol) et générer un résumé ainsi qu'une liste des 10 articles les plus intéressants publiés dans les 3 jours précédents.

## Fonctionnalités

- Consultation de serveurs MCP pour récupérer des articles récents
- Filtrage des articles selon des tags définis dans `assets/tags.txt`
- Classement et sélection des 10 articles les plus pertinents
- Génération d'un résumé global et d'explications de pertinence via Azure OpenAI
- API REST avec FastAPI pour déclencher la recherche

## Structure du projet

```
agent-infos/
├── src/                 # Package principal
│   ├── agents/          # Agents et logique métier
│   │   ├── mcp_agent.py     # Agent principal avec LangGraph
│   │   ├── mcp_client.py    # Client MCP pour communiquer avec les serveurs
│   │   └── article_processor.py  # Traitement et filtrage des articles
│   ├── api/             # Endpoints FastAPI
│   │   └── routes.py    # Routes de l'API
│   ├── app/             # Application principale
│   │   └── main.py      # Point d'entrée FastAPI
│   └── config/          # Configuration
│       ├── settings.py  # Paramètres de l'application
│       └── llm_config.py  # Configuration du LLM Azure
├── assets/              # Fichiers statiques
│   └── tags.txt        # Liste des tags de recherche
├── .env                 # Variables d'environnement (à créer)
├── .env.example         # Exemple de fichier .env
├── pyproject.toml       # Dépendances Python
└── README.md           # Ce fichier
```

## Installation

1. Cloner le projet ou naviguer dans le répertoire

2. Créer un environnement conda (recommandé):
```bash
conda create -n agent-infos python=3.11
conda activate agent-infos
```

3. Installer les dépendances:
```bash
pip install -e .
```

Ou avec pip directement:
```bash
pip install fastapi uvicorn langchain langchain-openai langgraph pydantic pydantic-settings python-dotenv httpx python-dateutil
```

4. Créer le fichier `.env` à partir de `.env.example`:
```bash
cp .env.example .env
```

5. Configurer les variables d'environnement dans `.env`:
```env
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-chat
AZURE_OPENAI_API_VERSION=2025-01-01-preview
LANGCHAIN_API_KEY=your_langchain_api_key_here
MCP_SERVERS=https://mcp-server1.example.com,https://mcp-server2.example.com
```

6. Configurer les tags dans `assets/tags.txt` (un tag par ligne)

## Utilisation

### Démarrer l'application

```bash
python -m src.app.main
```

Ou avec uvicorn directement:
```bash
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Utiliser l'API

Une fois l'application démarrée, vous pouvez:

1. **Vérifier la santé de l'application:**
```bash
curl http://localhost:8000/api/health
```

2. **Générer un résumé et obtenir les top articles:**
```bash
curl -X GET http://localhost:8000/api/articles
```

La réponse sera au format JSON:
```json
{
  "summary": "Résumé global des thèmes principaux...",
  "top_articles": [
    {
      "title": "Titre de l'article",
      "url": "https://example.com/article",
      "published_at": "2024-01-15T10:00:00",
      "source": "https://mcp-server.example.com",
      "tags": ["Python", "IA"],
      "relevance_reason": "Article intéressant car..."
    }
  ]
}
```

## Configuration des serveurs MCP

Les serveurs MCP peuvent être configurés de deux façons:

1. **Via variable d'environnement** (recommandé):
```env
MCP_SERVERS=https://server1.com,https://server2.com
```

2. **Via le code** dans `config/settings.py` (modifier la valeur par défaut)

Le client MCP supporte le protocole JSON-RPC 2.0 et essaie automatiquement différentes méthodes pour récupérer les articles:
- `fetch_articles` tool
- `search_articles` tool
- `list_resources` method

## Développement

### Tests

```bash
pytest
```

### Formatage du code

```bash
black .
isort .
```

### Vérification de type

```bash
mypy .
```

## Technologies utilisées

- **FastAPI**: Framework web moderne et rapide
- **Uvicorn**: Serveur ASGI
- **LangChain**: Framework pour applications LLM
- **LangGraph**: Orchestration d'agents avec graphes d'état
- **Pydantic**: Validation de données
- **httpx**: Client HTTP asynchrone
- **Azure OpenAI**: Service LLM pour la génération de résumés

## Bonnes pratiques implémentées

- Séparation des responsabilités (agents, API, config)
- Type hints partout
- Validation avec Pydantic
- Gestion d'erreurs robuste
- Logging structuré
- Support async/await pour les opérations I/O
- Configuration centralisée
- Documentation des fonctions et classes

## Licence

MIT
