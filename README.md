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

## Facultatif : offres LinkedIn via vos alertes emploi

LinkedIn interdit l'aspiration de ses pages. La méthode gratuite et autorisée :

1. Créez une adresse Gmail dédiée et activez la validation en deux étapes.
2. Sur LinkedIn, créez des alertes emploi (« PhD sport science », etc.) envoyées à cette adresse.
3. Dans Gmail : Compte Google → Sécurité → **Mots de passe des applications** → créez-en un.
4. Sur GitHub : Settings → Secrets and variables → Actions → ajoutez `GMAIL_USER` (l'adresse) et `GMAIL_APP_PASSWORD` (le mot de passe d'application).

Le collecteur lira alors chaque nuit les alertes des 3 derniers jours.

## Coûts

| Élément | Coût |
| --- | --- |
| Hébergement (GitHub Pages) | 0 € |
| Collecte nocturne (GitHub Actions, dépôt public) | 0 € |
| Nom de domaine personnalisé (facultatif) | environ 10 € par an |

## Crédits

Interface retravaillée selon la méthode [unslop](https://github.com/heydamir/unslop) de Damir Sokolovsky (CC BY 4.0). Chaque offre renvoie vers son annonce d'origine : vérifiez toujours les conditions sur la page officielle.
