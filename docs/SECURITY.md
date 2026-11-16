# Sécurité et limites opérationnelles

Cette application est **un projet de référence fonctionnel**, non un système certifié pour les données bancaires, médicales ou personnelles. Les jeux de données inclus sont inventés.

## Contrôles implémentés

- API protégée par clé (`X-API-Key`), comparaison constante, clé exigée via variable d'environnement.
- Endpoints d'import bornés en taille et en format ; requêtes SQL paramétrées via SQLAlchemy.
- Aucune exécution de code arbitraire ou de commande système issue des prompts.
- Pas de secrets dans les exemples, fichiers `.env` ignorés par Git.
- Traces explicites, réponse JSON et vérification des contraintes de données.
- Les modèles hébergés sont facultatifs ; les démos restent utilisables sans compte externe.

## Mesures obligatoires avant mise en production

1. **Authentification par utilisateur** : remplacer la clé partagée par OIDC/JWT, scopes, ACL par espace documentaire/client et politiques RBAC.
2. **Protection des données** : obtenir consentement, règles de rétention et suppression, chiffrement au repos et en transit ; documenter les transferts hors pays, notamment vers le fournisseur LLM.
3. **Réseau** : HTTPS, ingress contrôlé, WAF/API Gateway, rate limiting, egress restreint, base managée en sous-réseau privé.
4. **Qualité** : tests de charge, suites anti-injection, essais de restauration, alertes et validation métier.
5. **Secrets** : Azure Key Vault ou AWS Secrets Manager, rotation, identités managées, jamais de jeton GitHub dans un dépôt.
6. **Stockage et migrations** : PostgreSQL avec backups, Alembic, supervision des transactions et politique de rétention.

### RAG et hallucinations
Le mode sans LLM retourne des extraits et citations. Avec Groq, la vérification de références garantit uniquement que les identifiants cités existent, pas que chaque affirmation est vraie : appliquer une évaluation d’ancrage et une relecture humaine pour les réponses sensibles. Le texte des documents est traité comme données non fiables ; les PDF scannés requièrent de l’OCR non fourni. Le moteur TF-IDF fourni est conçu pour de petits corpus ; prévoir index vectoriel persistant pour la production.



## Déploiement privé et LangGraph v2

La configuration d'entreprise est fournie dans `compose.enterprise.yaml` et `docs/ON_PREMISE.md`. PostgreSQL et Ollama n'exposent aucun port public ; l'API est liée à l'interface loopback. Le modèle local est optionnel et doit être protégé par segmentation réseau, contrôle egress, gestion des modèles et revue de confidentialité. `LLM_PROVIDER=off` supprime les appels de génération LLM ; `local` nécessite un service compatible OpenAI interne.

LangGraph orchestre uniquement les nœuds explicitement prévus, **sans** donner d'accès à des outils systèmes. Ce projet n'inclut ni SSO, ni contrôle d'accès nominatif, ni ACL par document/dataset. Les déploiements d'entreprise nécessitent impérativement ces éléments avant d'exposer l'application à plusieurs utilisateurs.
