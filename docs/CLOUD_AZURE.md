# Déployer AfriDoc Intelligence RAG sur Azure Container Apps

**Architecture cible :** GitHub → build Docker → Azure Container Registry → Azure Container Apps → Azure Database for PostgreSQL Flexible Server. Les secrets passent par Azure Container Apps secrets (préférablement Azure Key Vault avec identité managée). Activez les logs Azure Monitor et un quota budgétaire.

## Prérequis

- Abonnement Azure autorisé à créer des ressources, Azure CLI, accès `az login`.
- Base PostgreSQL managée accessible depuis Container Apps (réseau privé recommandé), schéma applicatif créé par SQLAlchemy au démarrage pour la démo. Prévoir Alembic en production.
- Chaîne `DATABASE_URL=postgresql+psycopg://utilisateur:motdepasse@hote:5432/base?sslmode=require` (voir exigences TLS de votre fournisseur).
- Choisir une région Azure prenant en charge Container Apps et PostgreSQL, vérifier les tarifs et le quota. `southafricanorth` est un exemple, pas une affirmation de proximité optimale.

## Pipeline GitHub Actions optionnel

Le dépôt contient `.github/workflows/deploy-azure.yml` pour un déclenchement **manuel** depuis GitHub Actions. Configurer d'abord l'identité fédérée Azure (OIDC), les secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `APP_API_KEY`, `DATABASE_URL`, éventuellement `GROQ_API_KEY`, et les variables `AZURE_RESOURCE_GROUP`, `AZURE_APP_NAME`, `AZURE_LOCATION`. La première création du resource group et de PostgreSQL se fait hors du workflow. Aucun déploiement automatique payant n'est déclenché par un simple push.

## Déploiement de démonstration contrôlé

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
export AZURE_RESOURCE_GROUP="rg-afridoc"
export AZURE_APP_NAME="afridoc-api"
export AZURE_LOCATION="southafricanorth"
export APP_API_KEY="<GENERER_UN_SECRET_FORT>"
export DATABASE_URL="postgresql+psycopg://<UTILISATEUR>:<MOT_DE_PASSE>@<HOTE>:5432/<BASE>?sslmode=require"
# Facultatif : export GROQ_API_KEY="<CLE_GROQ>"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION"
./scripts/deploy-azure.sh
```

Le script `az containerapp up --source .` construit et déploie le conteneur ; il configure ensuite les secrets et les variables d'environnement. **Vérifier la suppression des secrets des journaux de shell, des fichiers `.env` et des copies d'écran.** Pour les déploiements répétés, adopter OIDC et une chaîne CI/CD vérifiée plutôt que de garder des identifiants locaux.

## Vérifier

```bash
FQDN=$(az containerapp show --name "$AZURE_APP_NAME" --resource-group "$AZURE_RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv)
curl "https://$FQDN/healthz"
curl -H "X-API-Key: $APP_API_KEY" "https://$FQDN/v1/documents"
```

## Exploitation et durcissement

Utiliser PostgreSQL pour éviter la perte des données lors des redémarrages. Restreindre l'accès réseau aux services privés, activer TLS, sauvegardes, supervision, alertes coûts et rotation des clés. L'application Web de démonstration utilise une clé partagée : pour un véritable SaaS, remplacer par Microsoft Entra ID/OIDC, RBAC, quotas et audit centralisé. Une solution de stockage de fichiers (Azure Blob Storage) et un moteur de recherche vectorielle dédié sont des améliorations à envisager à grande échelle.

Les PDF scannés nécessitent un module OCR supplémentaire ; ils ne sont pas pris en charge par le déploiement de base.

Référence officielle : https://learn.microsoft.com/en-us/azure/container-apps/containerapp-up
