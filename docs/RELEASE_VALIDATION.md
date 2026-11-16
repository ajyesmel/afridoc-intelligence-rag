# Validation de cette livraison

## Exécuté localement

- Tests unitaires / API sur Python présent dans l'environnement de préparation.
- Contrats de graphe vérifiés avec des doublures de l'interface StateGraph/LCEL pour couvrir les branches.
- Compilation syntaxique Python, validation des fichiers YAML et métadonnées `pyproject.toml`.

## À vérifier dans un environnement connecté

- Installer les bibliothèques officielles LangChain et LangGraph via `pip install -e ".[dev]"`.
- Exécuter tous les tests sur les véritables dépendances (`pytest -q`) ; la CI GitHub Actions inclut cette commande.
- Construire l'image (`docker build .`), puis vérifier l'API dans Docker Compose.
- Tester PostgreSQL de façon intégrée et le modèle Ollama/Groq avec des exemples autorisés.
- Tester les sauvegardes, SSO/ACL/tenants, sécurité et réseau avant un déploiement d'entreprise.

Cette validation locale ne constitue ni un test du framework réel, ni une certification de sécurité, ni une preuve de déploiement Azure/AWS.
