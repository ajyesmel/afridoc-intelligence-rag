# Checklist de démonstration technique

- [ ] Créer un `.env` local avec une nouvelle clé API aléatoire (ne pas la committer).
- [ ] Installer les dépendances dans un environnement virtuel isolé.
- [ ] Exécuter `pytest -q` et conserver une trace des résultats.
- [ ] Exécuter `python scripts/seed_demo.py` pour les données fictives.
- [ ] Démarrer l'API avec `uvicorn app.api:app --env-file .env --reload`.
- [ ] Vérifier `/healthz`, `/docs`, puis l'interface utilisateur.
- [ ] Tester le cas d'usage complet dans l'interface et l'absence d'autorisation avec une clé erronée.
- [ ] Exécuter `docker compose up --build` sur une machine équipée de Docker.
- [ ] Pour Azure ou AWS : préparer les rôles, secrets, la base PostgreSQL managée et les coûts.
- [ ] Après déploiement effectif : tester les URLs HTTPS, logs, accès à la base, sécurité et coûts.
- [ ] Mettre à jour le CV avec l'URL GitHub et seulement les déploiements prouvés.
