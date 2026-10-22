# ClipFlow

ClipFlow est une application macOS en français, basée sur le projet officiel `yt-dlp`, qui détecte et télécharge les vidéos compatibles depuis de nombreux sites.

## Installation

1. Copiez `ClipFlow.app` dans le dossier Applications. Elle fonctionne ensuite comme un agent invisible lié à Chrome : aucune fenêtre ni icône dans le Dock ne s'affiche.
2. Dans Chrome, ouvrez `chrome://extensions`, activez le mode développeur puis chargez le dossier `ClipFlow Chrome` comme extension non empaquetée.
3. Épinglez ClipFlow à la barre d’outils. Sur une page vidéo, cliquez sur son icône puis sur **Télécharger**.

ClipFlow choisit automatiquement la meilleure qualité MP4 H.264 disponible. L’option **Audio uniquement — MP3 sans vidéo** produit uniquement un MP3. La roue des réglages permet de choisir le dossier de destination et d’activer ou désactiver le **Son de fin**. Les fichiers temporaires restent dans le dossier caché `.tubesave-incomplete`; seul le fichier terminé apparaît dans le dossier choisi.

## Dailymotion

La version 1.43 inclut le moteur d’imitation navigateur `curl-cffi` recommandé par `yt-dlp`. Lorsqu’une page générique publique est protégée par Cloudflare, comme certaines pages intégrant Vimeo, ClipFlow active automatiquement cette imitation au lieu de demander une connexion inutile. Lorsqu’un manifeste Dailymotion refuse la requête normale, ClipFlow réessaie automatiquement comme Chrome. L’extension 2.8.6 transmet l’adresse de la vidéo Dailymotion à l’extracteur spécialisé et donne aux flux HLS/DASH détectés (notamment Vimeo) le vrai titre de la page ainsi qu’un identifiant stable, ce qui évite les collisions entre fichiers génériques nommés `playlist`. Chrome est désormais la seule interface visible : le moteur ClipFlow fonctionne avec un interpréteur d’événements non graphique et ne crée plus d’application macOS visible, même brièvement. Le service d’arrière-plan de l’extension suit maintenant le pourcentage même lorsque son panneau est fermé et restaure la valeur courante à la réouverture. Le moteur ne retire qu’une demande de la file lorsqu’il est libre, se rétablit après une erreur interne et s’arrête automatiquement après une courte période d’inactivité : une ancienne instance ne peut plus laisser les nouveaux téléchargements bloqués à 1 %. Sur YouTube, une réponse temporairement limitée à 360p déclenche automatiquement une nouvelle analyse avant tout téléchargement ; la basse définition n’est retenue qu’après vérification qu’aucun flux HD n’existe. Lorsqu’un import Premiere Pro est demandé, ClipFlow termine ou libère cette étape sous 30 secondes avant de traiter la demande suivante.

## Premiere Pro

Le module `ClipFlow Premiere` est prévu pour Premiere Pro 25.6 ou plus récent. La destination **Premiere Pro** enregistre le média dans `Médias ClipFlow`, à côté du projet `.prproj` ouvert, puis demande son importation. Le panneau **Fenêtre → Plug-ins UXP → ClipFlow** doit rester chargé dans Premiere. ClipFlow attend jusqu’à trois minutes pour les imports volumineux et ne signale plus le téléchargement comme échoué lorsque seul Premiere tarde à confirmer l’ajout.

## Limites

ClipFlow ne contourne pas les DRM. Téléchargez uniquement les vidéos que vous avez le droit d’enregistrer. Cette application autonome cible les Mac Apple Silicon (ARM64).
