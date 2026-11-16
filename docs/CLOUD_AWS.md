# Déployer AfriDoc Intelligence RAG sur AWS App Runner

**Architecture cible :** GitHub Actions/CLI → Amazon ECR → AWS App Runner → Amazon RDS for PostgreSQL. Secrets dans AWS Secrets Manager, rôle IAM d'exécution à privilèges minimaux, CloudWatch Logs pour le suivi.

## Prérequis

- AWS CLI v2 configuré (`aws configure` ou connexion SSO), Docker, permissions ECR/App Runner.
- RDS PostgreSQL accessible par un connecteur VPC App Runner si la base est privée. Activer les sauvegardes, TLS et une politique réseau restrictive.
- Deux secrets AWS Secrets Manager : `APP_API_KEY` et `DATABASE_URL` (URI PostgreSQL complète). Le secret Groq est facultatif.
- Un **rôle d'accès ECR** assumé par `build.apprunner.amazonaws.com`, autorisé à lire votre dépôt ECR (policy gérée `AWSAppRunnerServicePolicyForECRAccess`).
- Un **rôle IAM d'instance App Runner** assumé par `tasks.apprunner.amazonaws.com`, autorisé à lire uniquement les ARN précis des secrets requis.
- Vérifier la disponibilité App Runner et les coûts dans votre région AWS cible ; `eu-west-3` (Paris) est un exemple dont la disponibilité App Runner est documentée ; vérifier la disponibilité sur votre compte et la localisation des données.

## Pipeline GitHub Actions optionnel

Le dépôt fournit `.github/workflows/deploy-aws.yml` en `workflow_dispatch`, avec GitHub OIDC → rôle IAM `AWS_ROLE_ARN`. Définir les variables GitHub `AWS_REGION`, `AWS_APP_NAME`, `APPRUNNER_ECR_ROLE_ARN`, `APPRUNNER_INSTANCE_ROLE_ARN` et les secrets `APP_API_KEY_SECRET_ARN`, `DATABASE_URL_SECRET_ARN` (et `GROQ_API_KEY_SECRET_ARN` si nécessaire). Provisionner au préalable IAM, RDS, Secrets Manager et le réseau. Aucune infrastructure payante n'est créée par la CI de test.

## Création et lancement

```bash
export AWS_REGION="eu-west-3"
export AWS_APP_NAME="afridoc-api"
export APPRUNNER_ECR_ROLE_ARN="arn:aws:iam::<ACCOUNT_ID>:role/<APP_RUNNER_ECR_ROLE>"
export APPRUNNER_INSTANCE_ROLE_ARN="arn:aws:iam::<ACCOUNT_ID>:role/<APP_RUNNER_INSTANCE_ROLE>"
export APP_API_KEY_SECRET_ARN="arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:<API_SECRET>"
export DATABASE_URL_SECRET_ARN="arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:<DB_SECRET>"
# Facultatif : export GROQ_API_KEY_SECRET_ARN="arn:aws:secretsmanager:..."
./scripts/deploy-aws.sh
```

Le script prépare un dépôt ECR, construit l'image, l'envoie puis crée le service App Runner. Si le service existe, il demande un nouveau déploiement. Il ne crée **ni les rôles IAM, ni RDS, ni les secrets** : ces prérequis doivent être provisionnés et vérifiés séparément. Il ne gère pas les migrations de schéma.

## Vérifier et exploiter

Repérer l'URL de service dans AWS App Runner, tester `/healthz`, puis `/v1/documents` avec `X-API-Key`. Activer les alertes CloudWatch, la journalisation et le suivi des coûts. Mettre en place le connecteur VPC, le moindre privilège IAM, une sauvegarde et une rotation des secrets avant un traitement de données réelles.

Pour de fortes volumétries, utiliser S3 pour les documents sources et un index vectoriel persistant (pgvector/OpenSearch) plutôt que recalculer les embeddings à chaque requête.

Références officielles : https://docs.aws.amazon.com/apprunner/latest/dg/manage-create.html et https://docs.aws.amazon.com/general/latest/gr/apprunner.html
