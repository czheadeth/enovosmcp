# Enovos MCP Service

Service MCP (Model Context Protocol) pour Enovos permettant d'exposer des outils de consultation client (consommation et contrats) à des LLMs comme Claude ou ChatGPT.

## Prérequis

- Python 3.10 ou supérieur
- pip (gestionnaire de paquets Python)

## Installation

1. **Installer Python** (si pas déjà installé)
   - Télécharger depuis [python.org](https://www.python.org/downloads/)
   - Lors de l'installation, cocher "Add Python to PATH"

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

### Lancer le serveur MCP

```bash
python src/server.py
```

Le serveur expose 4 outils (tools) :

| Tool | Description |
|------|-------------|
| `get_customer_consumption` | Récupère la consommation énergétique d'un client |
| `get_customer_contract` | Récupère les détails du contrat d'un client |
| `get_customer_info` | Récupère les informations de base d'un client |
| `list_customers` | Liste tous les clients disponibles |

### Données mockées disponibles

Clients de test : `C001`, `C002`, `C003`

## Connexion à ChatGPT

### Option A : Mode local via Cursor

Cursor supporte MCP nativement. Ajoutez cette configuration dans vos paramètres MCP de Cursor :

```json
{
  "mcpServers": {
    "enovos": {
      "command": "python",
      "args": ["src/server.py"],
      "cwd": "C:\\Users\\User\\Documents\\projects\\enovosmcp"
    }
  }
}
```

### Option B : Mode distant pour ChatGPT Web

1. **Exposer le serveur via HTTPS**
   - Option simple : utiliser [ngrok](https://ngrok.com/)
   ```bash
   ngrok http 8000
   ```
   - Option production : déployer sur un serveur cloud (AWS, Azure, etc.)

2. **Configurer ChatGPT**
   - Accéder à **Settings** → **Connectors** → **Advanced** → **Developer mode**
   - Activer le mode développeur
   - Ajouter votre serveur MCP distant dans l'onglet "Connectors"
   - URL : l'URL HTTPS fournie par ngrok ou votre serveur

3. **Utiliser dans ChatGPT**
   - Ouvrir une nouvelle conversation
   - Sélectionner votre connecteur Enovos
   - Demander par exemple : "Quelle est la consommation du client C001 ?"

## Structure du projet

```
enovosmcp/
├── src/
│   ├── __init__.py
│   ├── server.py          # Serveur MCP principal
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── consumption.py # Tool consommation
│   │   └── contract.py    # Tool contrat
│   └── data/
│       ├── __init__.py
│       └── mock_data.py   # Données mockées
├── requirements.txt
└── README.md
```

## Exemple d'utilisation

Une fois connecté, vous pouvez poser des questions comme :

- "Liste tous les clients Enovos"
- "Quelle est la consommation du client C001 ?"
- "Montre-moi le contrat du client C002"
- "Quelles sont les informations du client C003 ?"

## Développement

### Ajouter un nouveau tool

1. Créer une fonction dans `src/tools/`
2. Ajouter le décorateur `@mcp.tool()` dans `src/server.py`
3. Documenter la fonction avec une docstring claire

### Connecter des données réelles

Remplacer les fonctions dans `src/data/mock_data.py` par des appels à votre API Enovos réelle.

