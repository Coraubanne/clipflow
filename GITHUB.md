# Publication de ClipFlow sur GitHub

Le dépôt GitHub doit rester **privé** tant que ClipFlow n'est pas signé, documenté pour un public externe et débarrassé de toute dépendance locale éventuelle.

## À chaque nouvelle version

1. Mettre à jour les versions dans `PROJECT_VERSION.json`, `TubeSave.spec` et les manifestes concernés.
2. Exécuter les tests :

   ```sh
   (cd outputs/ytdlp && .venv/bin/python -m unittest discover -s tests -v)
   ```

3. Reconstruire l’application et l’archive `outputs/ClipFlow-complet-vNUMERO.zip`.
4. Enregistrer les changements dans Git avec un message clair.
5. Publier la version et son ZIP :

   ```sh
   scripts/publish_github_release.sh
   ```

Le script pousse la branche `main`, crée un tag `vNUMERO` et ajoute le ZIP à une Release GitHub. Il refuse de publier un dossier qui contient des modifications non enregistrées.

## Sauvegarde hors GitHub

Cette commande produit aussi un ZIP autonome contenant le code, l'historique Git et la dernière distribution prête à installer :

```sh
scripts/create_project_backup.sh
```

GitHub protège le code et son historique ; le ZIP autonome facilite une restauration immédiate sans reconstruire l’application.
