# Mon PEA

Un petit site web **local** pour suivre les ETF d'un PEA : ajout et suppression d'achats, gains depuis le début, courbe d'évolution, répartition, mode clair et sombre.

Rien n'est hébergé en ligne : le site tourne sur ton ordinateur et tes données restent dans un fichier à côté du code.

## Fonctionnalités

- Ajout d'un achat : ETF, quantité, prix d'achat par part, frais, date
- Menu déroulant pour réutiliser les ETF déjà saisis
- Suppression d'un achat avec confirmation
- Valeur actuelle, total investi, plus-value en € et en %
- Courbe d'évolution de la valeur du portefeuille face à la somme investie (1M, 3M, 6M, 1A, Tout)
- Répartition par ETF
- Mode clair et sombre
- Cours mis à jour à la première ouverture de la journée, ou à la demande avec le bouton « Actualiser les cours »

## Prérequis

- Python 3 (aucune bibliothèque obligatoire)
- Une connexion internet pour récupérer les cours

## Lancement

```bash
python3 server.py
```

Sous Windows : `python server.py`.

Le site s'ouvre automatiquement sur http://127.0.0.1:8765. Pour l'arrêter, ferme le terminal ou fais `Ctrl+C`.

## Ajouter un ETF

Le site utilise les cours de Yahoo Finance, il faut donc le **symbole Yahoo** de l'ETF (et non l'ISIN). Pour un ETF coté à Paris, c'est le code suivi de `.PA`, par exemple :

| ETF | Symbole |
| --- | --- |
| Amundi PEA Monde (MSCI World) | `DCAM.PA` |
| Amundi MSCI World | `CW8.PA` |

## Erreur de certificat SSL (surtout sur Mac)

Si le bandeau affiche `CERTIFICATE_VERIFY_FAILED`, ton Python ne trouve pas les certificats pour vérifier le site de Yahoo. Deux solutions, une seule suffit :

1. Installer `certifi` : `pip3 install certifi` (le serveur l'utilise automatiquement s'il est présent)
2. Lancer `Install Certificates.command` situé dans le dossier Python de tes Applications

## Tes données

Tout est enregistré dans `data.json`, créé automatiquement à côté de `server.py` au premier achat ajouté. Il contient tes achats (quantités, prix, frais, dates) ainsi que les cours récupérés.

- Ce fichier est dans le `.gitignore` : il n'est jamais envoyé sur GitHub
- Pense à en faire une copie de temps en temps (cloud, clé USB) : si le dossier est supprimé, les données le sont aussi

## Structure

```
server.py     serveur local (Python, bibliothèque standard) : stockage et cours
index.html    interface (HTML, CSS et JavaScript dans un seul fichier)
data.json     tes données (créé automatiquement, non versionné)
```

## Limites

- Les cours viennent de Yahoo Finance, un accès gratuit et non officiel : ils peuvent différer légèrement de ceux de ta banque ou être indisponibles ponctuellement
- Les cours ne sont pas en temps réel
- Le site ne gère ni les dividendes ni la fiscalité du PEA : c'est un suivi de plus-value brute
- Ce projet est un outil de suivi personnel, pas un conseil en investissement
