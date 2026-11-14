# Sauvegarde du projet ClipFlow

Cette sauvegarde permet de réinstaller la version actuelle ou de reprendre le développement sur un autre Mac.

## Versions sauvegardées

- Produit : ClipFlow 2.13.1, version sémantique
- Application macOS : ClipFlow 2.13.1 (build 59), Apple Silicon ARM64
- Extension Chrome : ClipFlow 2.13.1, Manifest V3
- Module Premiere Pro : ClipFlow Premiere 1.0.4
- Moteur : yt-dlp 2026.10.26
- Environnement de référence : Python 3.13.0 et macOS 26.6.2

## Contenu

- `outputs/ytdlp` : moteur Python, pont natif Chrome, configuration PyInstaller, tests et ressources graphiques.
- `outputs/ClipFlow Chrome` : extension Chrome complète.
- `outputs/ClipFlow Premiere` : module UXP pour Premiere Pro.
- `.git` : dépôt Git local avec tout l’historique utile, afin de reprendre le suivi des modifications immédiatement.
- `outputs/ClipFlow-Installer.dmg` : installateur macOS unique destiné aux utilisateurs.
- `outputs/ClipFlow-complet-v2.13.1.zip` : version prête à partager ou réinstaller sans reconstruire le projet.
- `RECUPERATION_CLIPFLOW.md`, `GITHUB.md` et `PROJECT_VERSION.json` : notices et état de la sauvegarde.

Les environnements virtuels, caches Python et fichiers temporaires de compilation sont volontairement exclus. Ils sont volumineux, spécifiques à l’ordinateur et peuvent être recréés à partir des fichiers de dépendances.

La sauvegarde ne contient ni vidéos téléchargées, ni cookies Chrome, ni historique de navigation, ni réglages personnels.

## Réinstallation rapide

1. Ouvrir `outputs/ClipFlow-Installer.dmg`.
2. Lancer **Installer ClipFlow**. En cas d’avertissement macOS, faire un clic en maintenant la touche Contrôle, choisir **Ouvrir**, puis confirmer.
3. Suivre l’unique étape Chrome affichée par l’installateur pour charger le dossier `ClipFlow Chrome`.

Le ZIP versionné reste disponible pour la mise à jour automatique et la récupération technique, mais ce n’est plus le parcours d’installation normal.

## Reprendre le développement

Depuis le dossier `outputs/ytdlp` :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/pyinstaller --clean --noconfirm TubeSave.spec
```

L’application reconstruite se trouvera dans `outputs/ytdlp/dist/ClipFlow.app`.

Pour tester une nouvelle version de l’extension, rechargez `outputs/ClipFlow Chrome` depuis `chrome://extensions`. Conservez la clé publique du manifeste : elle maintient l’identifiant Chrome attendu par le pont natif.

Pour publier une nouvelle version sur GitHub, suivez `GITHUB.md`. Le dépôt public reçoit pour chaque release l’installateur DMG, puis le ZIP complet et son empreinte SHA-256 nécessaires à la mise à jour automatique.

## Conseil de conservation

Gardez au moins deux copies de l’installateur et de l’archive technique : une dans un stockage cloud et une sur un disque externe. Le ZIP est autonome ; le dossier de travail Codex d’origine n’est pas nécessaire pour le restaurer.
