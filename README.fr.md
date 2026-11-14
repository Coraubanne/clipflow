<p align="center">
  <img src="outputs/ytdlp/assets/ClipFlow.png" width="112" alt="Icône ClipFlow">
</p>

<h1 align="center">ClipFlow</h1>

<p align="center">
  Collecte média pour monteurs, documentalistes audiovisuels et équipes de films documentaires.
</p>

<p align="center">
  <a href="https://github.com/Coraubanne/clipflow/releases/latest"><img alt="Dernière version" src="https://img.shields.io/github/v/release/Coraubanne/clipflow?style=flat-square"></a>
  <a href="https://github.com/Coraubanne/clipflow/actions/workflows/test.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/Coraubanne/clipflow/test.yml?branch=main&style=flat-square&label=tests"></a>
  <img alt="macOS Apple Silicon" src="https://img.shields.io/badge/macOS-Apple%20Silicon-111111?style=flat-square&logo=apple">
  <img alt="Chrome Manifest V3" src="https://img.shields.io/badge/Chrome-Manifest%20V3-4285F4?style=flat-square&logo=googlechrome&logoColor=white">
  <a href="LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/licence-MIT-2ea44f?style=flat-square"></a>
</p>

<p align="center">
  <a href="README.md">English</a> · <strong>Français</strong>
</p>

<p align="center">
  <a href="https://github.com/Coraubanne/clipflow/releases/latest/download/ClipFlow-Installer.dmg"><img alt="Télécharger ClipFlow pour macOS" src="https://img.shields.io/badge/Telecharger_ClipFlow_pour_macOS-007AFF?style=for-the-badge&logo=apple&logoColor=white"></a>
</p>

> **Pour les utilisateurs :** téléchargez `ClipFlow-Installer.dmg` avec le bouton ci-dessus. N’utilisez pas **Code → Download ZIP** sur GitHub : cette commande récupère le code source et tous les fichiers de développement du projet.

ClipFlow transforme la collecte de vidéos web en un flux de postproduction propre. Son extension Chrome identifie les médias compatibles dans l’onglet actif, son moteur macOS local récupère la meilleure source compatible avec [yt-dlp](https://github.com/yt-dlp/yt-dlp), et son panneau Premiere Pro optionnel peut enregistrer le fichier à côté du projet actif puis l’importer automatiquement.

Le projet est pensé pour les monteurs, documentalistes audiovisuels, recherchistes, journalistes, producteurs d’archives et équipes de postproduction qui doivent collecter rapidement des médias qu’ils sont autorisés à utiliser.

## Points forts

- Détecte les vidéos de page compatibles, médias directs, flux HLS/DASH et lecteurs intégrés.
- Affiche une grande miniature à côté de chaque vidéo et capture localement le lecteur visible lorsqu’un site ne fournit qu’une image générique.
- Sélectionne la meilleure qualité MP4/H.264 disponible, y compris la 4K lorsqu’une source compatible existe.
- Nomme chaque fichier terminé `Chaîne — Titre de la vidéo [identifiant].mp4`, avec le créateur ou le site comme repli fiable.
- Privilégie la langue audio originale lorsque la source l’expose.
- Distingue clairement la langue de l’interface de celle des vidéos et affiche la version installée de l’extension.
- Propose un mode audio MP3 uniquement.
- Cache les fragments temporaires et ne montre que les fichiers terminés.
- Fonctionne comme agent macOS invisible ; Chrome reste l’interface principale.
- Propose une interface automatique, française ou anglaise depuis les réglages de l’extension.
- Peut enregistrer à côté du projet Premiere Pro et demander l’import automatique via le panneau UXP.
- Vérifie les mises à jour GitHub par empreinte SHA-256 puis actualise ensemble l’app, l’extension et le panneau Premiere.
- Ne contient ni télémétrie ni publicité.

## Chaîne de travail

| Étape | Composant | Rôle |
| --- | --- | --- |
| Détection | Extension Chrome | Analyse uniquement l’onglet actif lorsque l’utilisateur ouvre ClipFlow. |
| Récupération | App macOS en arrière-plan | Utilise yt-dlp et FFmpeg pour télécharger, assembler ou convertir les médias compatibles. |
| Classement | Système de fichiers local | Écrit le résultat dans Téléchargements, un dossier choisi ou le dossier du projet Premiere. |
| Montage | Panneau Premiere Pro | Peut importer le fichier terminé dans le projet actif. |

## Installation

ClipFlow cible actuellement les Mac Apple Silicon et est distribué hors du Mac App Store et du Chrome Web Store.

1. Téléchargez l’unique fichier [`ClipFlow-Installer.dmg`](https://github.com/Coraubanne/clipflow/releases/latest/download/ClipFlow-Installer.dmg).
2. Ouvrez l’image disque puis lancez **Installer ClipFlow**. Il installe l’app macOS, place l’extension Chrome dans `Documents/ClipFlow` et installe le module Premiere Pro.
   Si macOS bloque ce premier lancement, faites un clic en maintenant la touche Contrôle sur **Installer ClipFlow**, choisissez **Ouvrir**, puis confirmez. Une future version notariée supprimera cette étape supplémentaire.
3. Lorsque le message apparaît, ouvrez `chrome://extensions`, activez le **Mode développeur**, choisissez **Charger l’extension non empaquetée**, puis sélectionnez le dossier `ClipFlow Chrome` affiché par le Finder. Chrome interdit à une extension publique non empaquetée de s’activer silencieusement.
4. Épinglez ClipFlow à la barre d’outils. Ouvrez une page vidéo, lancez la lecture si nécessaire, ouvrez ClipFlow puis choisissez **Télécharger**.

Après la première installation, utilisez **Réglages → Chercher une mise à jour**. Les releases publiques peuvent être vérifiées et installées sans compte GitHub.

## Compatibilité

| Prérequis | Configuration prise en charge |
| --- | --- |
| Système | macOS 12 ou plus récent |
| Processeur | Apple Silicon (ARM64) |
| Navigateur | Google Chrome compatible Manifest V3 |
| Intégration Premiere | Adobe Premiere Pro 25.6 ou plus récent |
| Médias | Sources publiques ou autrement autorisées, sans DRM, prises en charge par yt-dlp ou exposées comme média web compatible |

La compatibilité des sites évolue et dépend en partie des extracteurs amont. Le fait qu’une vidéo soit visible dans un navigateur ne garantit pas qu’elle puisse être téléchargée.

## Vie privée et sécurité

ClipFlow traite localement les URL et les médias. Il n’exploite aucun service d’analyse, n’envoie pas l’historique de navigation et ne vend aucune donnée d’usage. L’extension utilise l’accès temporaire à l’onglet actif et une permission réseau limitée à TF1. L’accès à une session du navigateur n’est employé que lorsqu’un site compatible exige une authentification et que ClipFlow possède l’autorisation locale correspondante.

Chaque archive de release possède une empreinte SHA-256. Le système de mise à jour refuse une archive altérée, les chemins ZIP dangereux, les composants inattendus et une signature d’application invalide. Consultez [SECURITY.md](SECURITY.md) pour signaler une vulnérabilité de manière privée.

## Usage responsable

ClipFlow est un outil généraliste de flux média. Il ne déchiffre ni ne contourne les DRM. Utilisez-le uniquement pour les médias dont vous détenez les droits, appartenant au domaine public, couverts par une licence ou une exception applicable, ou que vous êtes autrement autorisé à télécharger. Vous restez responsable du respect du droit d’auteur, de la vie privée, des contrats et des règles des plateformes dans votre juridiction.

ClipFlow n’est ni affilié ni approuvé par YouTube, Google, Adobe, TF1, Vimeo, Dailymotion ou une autre plateforme. Lisez [LEGAL.fr.md](LEGAL.fr.md) avant toute utilisation.

## Développement

```bash
cd outputs/ytdlp
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests
.venv/bin/pyinstaller --clean --noconfirm TubeSave.spec
```

Le dépôt contient le moteur macOS, l’extension Chrome, le panneau Premiere UXP, les tests et l’outillage de publication. Les contributions de code externes ne sont pas acceptées ; les issues publiques restent disponibles pour les signalements de bugs reproductibles. Consultez [CONTRIBUTING.md](CONTRIBUTING.md).

ClipFlow suit désormais un versionnage sémantique pour ses versions visibles. La version 2.9.1 passe par un dernier tag technique historique afin que les installations en v68 migrent sans casser la mise à jour automatique ; les tags suivants utilisent directement le format `vMAJEUR.MINEUR.CORRECTIF`.

## Crédits

ClipFlow s’appuie sur [yt-dlp](https://github.com/yt-dlp/yt-dlp) et utilise FFmpeg pour le traitement des médias compatibles. Les projets tiers conservent leurs propres licences et marques ; consultez [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licence

Le code source original de ClipFlow est publié sous [licence MIT](LICENSE). Les composants tiers embarqués restent soumis à leurs licences respectives.
