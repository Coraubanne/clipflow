# Sauvegarde du projet ClipFlow

Cette sauvegarde permet de réinstaller la version actuelle ou de reprendre le développement sur un autre Mac.

## Versions sauvegardées

- Application macOS : ClipFlow 1.41 (build 42), Apple Silicon ARM64
- Extension Chrome : ClipFlow 2.8.6, Manifest V3
- Module Premiere Pro : ClipFlow Premiere 1.0.4
- Moteur : yt-dlp 2026.08.19
- Environnement de référence : Python 3.13.0 et macOS 26.6.2

## Contenu

- `outputs/ytdlp` : moteur Python, pont natif Chrome, configuration PyInstaller, tests et ressources graphiques.
- `outputs/ClipFlow Chrome` : extension Chrome complète.
- `outputs/ClipFlow Premiere` : module UXP pour Premiere Pro.
- `.git` : dépôt Git local avec tout l’historique utile, afin de reprendre le suivi des modifications immédiatement.
- `distribution/ClipFlow-complet-v59.zip` : version prête à réinstaller sans reconstruire le projet.
- `RECUPERATION_CLIPFLOW.md`, `GITHUB.md` et `PROJECT_VERSION.json` : notices et état de la sauvegarde.

Les environnements virtuels, caches Python et fichiers temporaires de compilation sont volontairement exclus. Ils sont volumineux, spécifiques à l’ordinateur et peuvent être recréés à partir des fichiers de dépendances.

La sauvegarde ne contient ni vidéos téléchargées, ni cookies Chrome, ni historique de navigation, ni réglages personnels.

## Réinstallation rapide

1. Décompresser `distribution/ClipFlow-complet-v59.zip`.
2. Copier `ClipFlow.app` dans `/Applications`.
3. Faire un clic droit sur l’application, choisir **Ouvrir**, puis confirmer si macOS le demande. ClipFlow reste invisible lorsqu’il fonctionne.
4. Conserver le dossier `ClipFlow Chrome` dans un emplacement permanent.
5. Ouvrir `chrome://extensions`, activer le mode développeur, choisir **Charger l’extension non empaquetée**, puis sélectionner ce dossier.

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

Pour publier une nouvelle version sur GitHub, suivez `GITHUB.md`. Le dépôt est prévu pour rester privé et chaque Release reçoit le ZIP complet correspondant.

## Conseil de conservation

Gardez au moins deux copies de l’archive finale : une dans un stockage cloud et une sur un disque externe. Le ZIP est autonome ; le dossier de travail Codex d’origine n’est pas nécessaire pour le restaurer.
