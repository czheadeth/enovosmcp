# Enovos MCP Service

Service MCP (Model Context Protocol) pour Enovos permettant d'exposer des outils de consultation client (consommation et contrats) à des LLMs comme Claude ou ChatGPT.

## Prérequis

- Python 3.10 ou supérieur
- pip (gestionnaire de paquets Python)

## Installation locale

1. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

2. **Lancer le serveur**
   ```bash
   python -m src.server
   ```

## Tools disponibles

| Tool | Description |
|------|-------------|
| `get_customer_consumption` | Récupère la consommation énergétique d'un client |
| `get_customer_contract` | Récupère les détails du contrat d'un client |
| `get_customer_info` | Récupère les informations de base d'un client |

**Clients de test** : `C001`, `C002`, `C003`

---

## Déploiement sur AWS EC2

### 1. Créer une instance EC2

1. AWS Console → EC2 → **Lancer une instance**
2. **AMI** : Amazon Linux 2023
3. **Type** : t2.micro ou t3.micro
4. **Paire de clés** : Créer une nouvelle (RSA, .pem)
5. **Groupe de sécurité** : Ouvrir les ports 22 (SSH), 8000 (HTTP)

### 2. Se connecter en SSH

```bash
ssh -i votre-cle.pem ec2-user@IP_PUBLIQUE_EC2
```

### 3. Installer le serveur

```bash
# Installer Python 3.11
sudo yum update -y
sudo yum install -y python3.11 python3.11-pip git

# Cloner le repo
git clone https://github.com/czheadeth/enovosmcp.git
cd enovosmcp

# Installer les dépendances
python3.11 -m pip install -r requirements.txt

# Lancer le serveur en arrière-plan
nohup python3.11 -m src.server > server.log 2>&1 &

# Vérifier que ça tourne
curl http://localhost:8000/
```

### 4. Installer ngrok (pour HTTPS)

ChatGPT exige HTTPS. ngrok fournit un tunnel HTTPS gratuit.

```bash
# Télécharger ngrok
curl -O https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xzf ngrok-v3-stable-linux-amd64.tgz

# Configurer le token (récupérer sur https://dashboard.ngrok.com/get-started/your-authtoken)
./ngrok config add-authtoken VOTRE_TOKEN_NGROK

# Lancer ngrok
./ngrok http 8000
```

Vous obtiendrez une URL HTTPS comme : `https://xxxx.ngrok-free.app`

### 5. Garder ngrok actif après déconnexion

```bash
# Installer screen
sudo yum install screen -y

# Lancer ngrok dans un screen
screen -S ngrok
./ngrok http 8000

# Détacher le screen : Ctrl+A puis D
# Revenir au screen : screen -r ngrok
```

---

## Connexion à ChatGPT

### 1. Activer le mode développeur

1. ChatGPT → **Settings** → **Applis et connecteurs**
2. **Advanced** → Activer **Developer mode**

### 2. Ajouter le connecteur

1. Cliquer **Add connector**
2. **Nom** : `Enovos`
3. **URL du serveur MCP** :
   ```
   https://VOTRE_URL_NGROK/mcp/sse
   ```
4. **Authentification** : Aucune
5. Cliquer **Créer**

### 3. Tester

Dans une conversation ChatGPT :
- "Quelle est ma consommation d'énergie ?"
- "Montre-moi mon contrat"
- "Quelles sont mes informations client ?"

---

## Structure du projet

```
enovosmcp/
├── src/
│   ├── server.py          # Serveur MCP principal
│   ├── tools/
│   │   ├── consumption.py # Tool consommation
│   │   └── contract.py    # Tool contrat
│   └── data/
│       └── mock_data.py   # Données mockées
├── Dockerfile             # Pour déploiement container
├── requirements.txt
└── README.md
```

---

## Développement

### Ajouter un nouveau tool

```python
@mcp.tool(annotations={"readOnlyHint": True})
def mon_nouveau_tool(param: str = "default") -> dict:
    """
    UTILISE CET OUTIL quand l'utilisateur demande:
    - quelque chose
    - autre chose
    
    Description du retour.
    """
    return {"result": "data"}
```

### Connecter des données réelles

Remplacer les fonctions dans `src/data/mock_data.py` par des appels à votre API Enovos réelle.

---

## Commandes utiles EC2

```bash
# Voir les logs du serveur
tail -f server.log

# Redémarrer le serveur
pkill -f "python3.11 -m src.server"
nohup python3.11 -m src.server > server.log 2>&1 &

# Mettre à jour le code
cd ~/enovosmcp
git pull
pkill -f "python3.11 -m src.server"
nohup python3.11 -m src.server > server.log 2>&1 &
```
