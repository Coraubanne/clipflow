# Publication de ClipFlow sur GitHub

Le dépôt GitHub est public. Toute release doit rester reproductible, documentée et exempte de donnée locale ou de secret.

## À chaque nouvelle version

1. Mettre à jour les versions dans `PROJECT_VERSION.json`, `TubeSave.spec` et les manifestes concernés.
2. Exécuter les tests :

   ```sh
   (cd outputs/ytdlp && .venv/bin/python -m unittest discover -s tests -v)
   ```

3. Reconstruire l’application puis créer l’archive et son empreinte avec `scripts/build_distribution.sh`.
4. Enregistrer les changements dans Git avec un message clair.
5. Publier la version et son ZIP :

   ```sh
   scripts/publish_github_release.sh
   ```

Le script pousse la branche `main`, crée un tag `vNUMERO` et ajoute le ZIP ainsi que son fichier `.sha256` à une Release GitHub. L’empreinte est obligatoire pour que l’installateur automatique accepte la release. Le script refuse de publier un dossier qui contient des modifications non enregistrées.

## Sauvegarde hors GitHub

Cette commande produit aussi un ZIP autonome contenant le code, l'historique Git et la dernière distribution prête à installer :

```sh
scripts/create_project_backup.sh
```

GitHub protège le code et son historique ; le ZIP autonome facilite une restauration immédiate sans reconstruire l’application.
