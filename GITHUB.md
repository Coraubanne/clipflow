# Publication de ClipFlow sur GitHub

Le dépôt GitHub est public. Toute release doit rester reproductible, documentée et exempte de donnée locale ou de secret.

## À chaque nouvelle version

1. Mettre à jour les versions dans `PROJECT_VERSION.json`, `TubeSave.spec` et les manifestes concernés.
2. Exécuter les tests :

   ```sh
   (cd outputs/ytdlp && .venv/bin/python -m unittest discover -s tests -v)
   ```

3. Reconstruire l’application puis créer l’installateur macOS, l’archive de mise à jour et son empreinte avec `scripts/build_distribution.sh`.
4. Enregistrer les changements dans Git avec un message clair.
5. Publier la version et ses fichiers de distribution :

   ```sh
   scripts/publish_github_release.sh
   ```

Le script pousse la branche `main`, utilise le champ `release_tag` de `PROJECT_VERSION.json` et ajoute trois éléments à la Release GitHub : `ClipFlow-Installer.dmg` pour les utilisateurs, puis le ZIP versionné et son fichier `.sha256` pour le système de mise à jour automatique. Après le tag de transition `v69` associé à ClipFlow 2.9.1, les tags suivent le format sémantique `vMAJEUR.MINEUR.CORRECTIF`. L’empreinte est obligatoire pour que le système de mise à jour accepte la release. Le script refuse de publier un dossier qui contient des modifications non enregistrées.

## Sauvegarde hors GitHub

Cette commande produit aussi un ZIP autonome contenant le code, l'historique Git et la dernière distribution prête à installer :

```sh
scripts/create_project_backup.sh
```

GitHub protège le code et son historique ; le ZIP autonome facilite une restauration immédiate sans reconstruire l’application.
