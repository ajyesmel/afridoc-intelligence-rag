# Déploiement privé — AfriDoc Intelligence RAG

## Pourquoi héberger AfriDoc sur son serveur ?

Une PME, une banque, une société de conseil, une administration, une institution de formation ou un particulier peuvent vouloir interroger leur propre documentation sans la transférer à une application SaaS publique. Le serveur interne apporte la maîtrise de l'hébergement, du stockage, des sauvegardes et du réseau, mais **ne dispense pas** d'une politique de sécurité et de conformité.

### Trois niveaux possibles

| Mode | Les documents sortent-ils du serveur pour générer la réponse ? | Conséquence |
|---|---|---|
| `LLM_PROVIDER=off` | Non, pour la génération LLM (aucun appel LLM) | Extraits sources, pas de synthèse générative |
| `LLM_PROVIDER=local` | Non vers un fournisseur externe, si URL interne et sortie réseau bloquée | Synthèse avec modèle local installé ; qualité/matériel à valider |
| `LLM_PROVIDER=groq` | Oui, les extraits utiles sont envoyés à un fournisseur externe | Accord de sécurité et vérification contractuelle requis |

**Prudence :** `ENABLE_SEMANTIC_EMBEDDINGS=true` peut télécharger un modèle lors de la première exécution. Préinstaller et valider les poids du modèle pour les réseaux isolés, ou conserver le mode lexical sans téléchargement. Les images Docker et le modèle Ollama doivent être récupérés dans une chaîne d'approvisionnement approuvée.

## Prérequis

- Hôte Linux administré (VM, serveur sur site ou VPS), Docker Engine et Docker Compose Plugin ; réseau et sauvegardes disponibles.
- Ressources CPU, RAM et stockage dimensionnées selon la taille des fichiers. Un LLM privé ajoute des besoins en mémoire/VRAM ; consulter les exigences du modèle choisi.
- DNS interne et reverse proxy HTTPS (Caddy, Nginx ou passerelle d'entreprise) pour les utilisateurs distants ; **aucun accès direct au port 8000 depuis Internet**.
- Secret API fort, mot de passe PostgreSQL, certificats, règles pare-feu et politique de rétention.

## Installation de référence

```bash
git clone <URL_DEPOT>
cd afridoc-intelligence-rag
cp .env.enterprise.example .env.enterprise
```

Configurer dans `.env.enterprise` : `APP_API_KEY` (secret aléatoire fort), `POSTGRES_PASSWORD`, puis **exactement le même mot de passe** dans l'URL `DATABASE_URL` (caractères spéciaux encodés comme URL). Garder `LLM_PROVIDER=off` pour le premier essai et `ENABLE_SEMANTIC_EMBEDDINGS=false`.

```bash
docker compose --env-file .env.enterprise -f compose.enterprise.yaml config
docker compose --env-file .env.enterprise -f compose.enterprise.yaml up -d --build
docker compose --env-file .env.enterprise -f compose.enterprise.yaml ps
curl -fsS http://127.0.0.1:8000/healthz
```

L'API est liée à `127.0.0.1:8000`. PostgreSQL utilise le volume `pgdata` sans `ports:`. Les documents transitent par l'API FastAPI et sont stockés en SQL ; protéger les exports et les sauvegardes autant que les fichiers d'origine. Aucun service de création de comptes utilisateurs n'est fourni.

## Activer un LLM local via Ollama

1. Dans `.env.enterprise` : `LLM_PROVIDER=local`, `LOCAL_LLM_BASE_URL=http://ollama:11434/v1` et `LOCAL_LLM_MODEL=qwen2.5:3b` (exemple uniquement).
2. Démarrer le service de modèle (profil Docker facultatif) :

```bash
docker compose --env-file .env.enterprise -f compose.enterprise.yaml --profile local-llm up -d --build
docker compose --env-file .env.enterprise -f compose.enterprise.yaml exec ollama ollama pull qwen2.5:3b
```

3. Vérifier qu'un appel documentaire aboutit et mesurer les erreurs, temps de réponse et citations sur un jeu représentatif. L'API Ollama compatible OpenAI doit être accessible depuis le conteneur API. Aucun endpoint de modèle n'est publié sur l'IP de l'hôte dans cet exemple.

Pour un modèle hébergé ailleurs dans le réseau interne, remplacer `LOCAL_LLM_BASE_URL` par l'URL autorisée. Pour la production, préférer HTTPS, authentification au service de modèle et contrôle des sorties réseau. Pour un réseau isolé, charger les images/poids depuis un dépôt interne approuvé plutôt que de compter sur `ollama pull`.

## Intégrer à l'authentification de l'entreprise

Le projet inclut **uniquement une clé d'API partagée** : ce n'est pas une authentification multi-utilisateur. Avant d'autoriser les salariés à importer des documents confidentiels, mettre en place SSO/OIDC, rôles et permissions par dossier, isolation entre services ou clients, journaux d'accès, chiffrement, antivirus/inspection des PDF et gestion des droits de suppression. Si une même instance doit servir plusieurs départements, ajouter un identifiant de tenant et appliquer l'isolation dans chaque requête SQL et chaque recherche.

### Exploitation et continuité

- Sauvegarder les volumes PostgreSQL avec procédure de restauration testée, et protéger les secrets de sauvegarde.
- Fixer et analyser les versions d'images ; ne pas conserver des images `latest` sans politique de mise à jour.
- Surveiller `/healthz`, les ressources, la saturation des logs, la volumétrie et les échecs d'inférence.
- Appliquer HTTPS et limitation de débit au reverse proxy ; restreindre le trafic sortant aux services autorisés.
- Tester les injections de prompt, la qualité factuelle et les fuites entre utilisateurs avant une vraie mise en service.

## Périmètre de cette livraison

Un exemple **exécutable sur un hôte Docker** avec données et modèle contrôlables ; ce n'est pas une certification de sécurité, ni une architecture haute disponibilité, ni une solution prête à recevoir des données réglementées sans modifications.
