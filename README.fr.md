# ClipFlow

<img src="outputs/ytdlp/assets/ClipFlow.png" width="88" align="right" alt="Icône ClipFlow">

Collectez des vidéos web pour le montage, la recherche d’archives et la production documentaire. ClipFlow repère les médias compatibles dans le navigateur et les enregistre sur votre Mac. Il peut aussi importer le fichier terminé dans votre projet Premiere Pro.

**[Télécharger ClipFlow pour macOS](https://github.com/Coraubanne/clipflow/releases/latest/download/ClipFlow-Installer.dmg)** · [Notes de version](https://github.com/Coraubanne/clipflow/releases/latest) · [English](README.md)

Apple Silicon · macOS 12+ · Chrome ou Firefox 140+

## Installer ClipFlow

1. Téléchargez `ClipFlow-Installer.dmg`, ouvrez-le et lancez **Installer ClipFlow**. L’installateur ajoute l’application en arrière-plan, les fichiers du navigateur et le panneau Creator Bridge.
2. Chargez ClipFlow dans votre navigateur.

   | Navigateur | Configuration |
   | --- | --- |
   | Google Chrome | Ouvrez `chrome://extensions`, activez le **Mode développeur**, cliquez sur **Charger l’extension non empaquetée** et choisissez `~/Documents/ClipFlow/ClipFlow Chrome`. |
   | Firefox | Ouvrez `about:debugging#/runtime/this-firefox`, cliquez sur **Charger un module complémentaire temporaire** et choisissez `~/Documents/ClipFlow/ClipFlow-Firefox-unsigned.xpi`. Rechargez-le après avoir quitté puis relancé Firefox. |

L’option GitHub **Code → Download ZIP** télécharge le code source. Pour installer ClipFlow, utilisez le DMG. L’extension Firefox est actuellement distribuée en version de test non signée. [Guide Mozilla sur les modules temporaires](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/)

## Télécharger une vidéo

1. Ouvrez la page de la vidéo et lancez sa lecture si ClipFlow a besoin de détecter le flux.
2. Ouvrez ClipFlow depuis la barre d’outils, vérifiez la miniature et cliquez sur **Télécharger**.
3. Retrouvez le fichier dans **Téléchargements** ou changez la destination dans les réglages. L’option **Audio seul** enregistre un MP3.

ClipFlow cherche la meilleure qualité qu’il peut livrer en MP4, jusqu’en 4K lorsqu’un flux compatible est disponible. Il privilégie la piste audio d’origine si la source l’identifie et demande confirmation avant de convertir un WebM détecté. Les fichiers sont nommés sur le modèle `Chaîne — Titre de la vidéo [identifiant].mp4`.

Quand ClipFlow détecte un flux 4K au format MKV ou des pistes 4K qu’il peut assembler en MKV, un bouton supplémentaire lance le téléchargement et la conversion en MP4 2160p. Le fichier final porte le suffixe `4K`.

La compatibilité dépend du lecteur et des formats proposés par le site. Utilisez ClipFlow pour les médias que vous êtes autorisé à télécharger. Les flux protégés par DRM sont incompatibles. [Conditions d’utilisation](LEGAL.fr.md)

## Envoyer un fichier vers Premiere Pro

Ouvrez un projet enregistré dans **Premiere Pro 25.6 ou ultérieur**, puis affichez **Fenêtre → Plug-ins UXP → Creator Bridge**. Choisissez **Premiere Pro** comme destination dans ClipFlow avant de lancer le téléchargement. ClipFlow enregistre le fichier à côté du projet et demande à Creator Bridge de l’ajouter au panneau Projet. [Creator Bridge](https://github.com/Coraubanne/CreatorBridge)

## Mettre à jour

Ouvrez **Réglages → Chercher une mise à jour**. Le compagnon vérifie l’empreinte SHA-256 de l’archive GitHub avant de l’installer. Lorsque Premiere Pro est la destination choisie, ClipFlow vérifie aussi Creator Bridge séparément. Pour Firefox, récupérez le XPI à jour sur la page de la release et chargez-le comme module temporaire. [Historique des versions](CHANGELOG.md)

## Projet et assistance

- [Signaler un bug reproductible](https://github.com/Coraubanne/clipflow/issues) · [Politique de contribution](CONTRIBUTING.md)
- [Vie privée](PRIVACY.md) · [Signaler une vulnérabilité](SECURITY.md)
- [Publication et sauvegardes](GITHUB.md) · [Tests GitHub Actions](https://github.com/Coraubanne/clipflow/actions/workflows/test.yml)
- [Licence MIT](LICENSE) · [Composants tiers](THIRD_PARTY_NOTICES.md)

<details>
<summary>Compiler et tester</summary>

Le paquet Firefox est produit à partir du code partagé dans `outputs/ClipFlow Chrome`. Le compagnon macOS utilise [yt-dlp](https://github.com/yt-dlp/yt-dlp) et FFmpeg.

```sh
git submodule update --init
cd outputs/ytdlp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests
.venv/bin/pyinstaller --clean --noconfirm TubeSave.spec
```

</details>
