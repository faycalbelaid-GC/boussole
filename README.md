# Boussole

Offres de doctorat, master, postdoc et bourses dans le monde entier, **mises à jour chaque nuit, gratuitement**. Le site permet aussi de suivre ses candidatures, ses dates limites et de préparer ses documents.

Site en ligne : https://faycalbelaid-gc.github.io/boussole/

## Comment ça marche

```
Chaque nuit (GitHub Actions, gratuit)
  └─ collector/collect.py visite les sources de collector/sources.json
       ├─ fils RSS (universités, sites de bourses)
       └─ pages de résultats publiques (jobs.ac.uk, FindAPhD, EURAXESS, Academic Positions…)
  └─ trie par règles : niveau, domaine, pays, date limite, financement
  └─ met à jour site/data/offres.json et site/data/meta.json
  └─ republie le site (GitHub Pages, gratuit)
```

- Aucune IA payante : le tri se fait par mots-clés et expressions régulières.
- Le collecteur respecte le fichier `robots.txt` de chaque site, attend 2 secondes entre deux pages et ne passe qu'une fois par nuit.
- Les offres closes disparaissent d'elles-mêmes ; une offre sans date limite disparaît si on ne la revoit pas pendant 45 jours.
- Les données des visiteurs (objectif, tracker, documents) restent dans leur navigateur : pas de compte, rien n'est envoyé.

## Lancer une mise à jour à la main

Onglet **Actions** → « Mise à jour nocturne et mise en ligne » → **Run workflow**. Le rapport de chaque source (nombre d'offres, erreurs) s'affiche dans le journal et dans `site/data/meta.json`.

## Ajouter ou couper une source

Modifier `collector/sources.json` :

- `type: "rss"` + `urls` : un fil RSS ou Atom.
- `type: "html"` + `urls` + `pattern` : une page de résultats publique ; `pattern` est la forme des liens vers les annonces (expression régulière). Si une page ne donne rien, le journal affiche des exemples de liens pour aider à régler `pattern`.
- `enabled: false` coupe une source.

## Recommandé : les plateformes qui bloquent les robots, via leurs alertes email

FindAPhD, jobs.ac.uk, EURAXESS, Academic Positions, LinkedIn, Nature Careers, ScholarshipDb, FindAMasters, Jobbnorge, Varbi, ABG et AcademicTransfer refusent les programmes automatiques, mais envoient gratuitement leurs nouvelles offres par email. Le collecteur lit ces emails chaque nuit : ce sont les plateformes elles-mêmes qui vous transmettent leurs offres, rien n'est contourné.

1. Créez une adresse Gmail dédiée (par exemple `boussole.alertes@gmail.com`) et activez la validation en deux étapes.
2. Avec cette adresse, créez des alertes sur chaque plateforme (gratuit) : FindAPhD (« PhD alerts »), jobs.ac.uk (« Job alerts », catégorie PhDs), EURAXESS (« Job alerts »), Academic Positions, LinkedIn (« Créer une alerte » sur une recherche « PhD »), Nature Careers, ScholarshipDb… Choisissez vos domaines et pays.
3. Gmail : Compte Google → Sécurité → **Mots de passe des applications** → créez-en un.
4. GitHub : Settings → Secrets and variables → Actions → **New repository secret** : `GMAIL_USER` (l'adresse) et `GMAIL_APP_PASSWORD` (le mot de passe d'application).

Le collecteur lira alors chaque nuit les alertes des 3 derniers jours et ajoutera les offres au site, avec un lien vers l'annonce d'origine.

## Tester une seule source

Actions → « Mise à jour nocturne et mise en ligne » → Run workflow → champ « Tester seulement ces sources » : identifiants de `sources.json` séparés par des virgules (par exemple `phdfinder,tg-azarapply`). Utile pour régler une source sans resolliciter toutes les autres.

## Coûts

| Élément | Coût |
| --- | --- |
| Hébergement (GitHub Pages) | 0 € |
| Collecte nocturne (GitHub Actions, dépôt public) | 0 € |
| Nom de domaine personnalisé (facultatif) | environ 10 € par an |

## Crédits

Interface retravaillée selon la méthode [unslop](https://github.com/heydamir/unslop) de Damir Sokolovsky (CC BY 4.0). Chaque offre renvoie vers son annonce d'origine : vérifiez toujours les conditions sur la page officielle.
