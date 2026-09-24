# Dossard Vacances

Trouve les courses à pied, trails, cross et triathlons autour de ton lieu de vacances, pendant ton séjour ou à quelques jours près.

- `site/` : le site (une page HTML) ; ses données `site/data/courses.json` sont produites par la collecte
- `scraper/` : la collecte des calendriers officiels FFA et FFTri
- `tests/` : tests des analyseurs sur de vrais extraits des pages FFA et FFTri
- `.github/workflows/mise-a-jour.yml` : chaque lundi matin, la collecte tourne puis le site est republié

## Lancer une mise à jour à la main
Onglet **Actions** → **Mise à jour des courses** → **Run workflow**. Compter 30 à 60 minutes.

## Si ça ne marche pas
- **Étape « Tests » en rouge** : la FFA ou la FFTri a changé la structure de ses pages, les analyseurs sont à adapter.
- **Étape « Collecte » en rouge** : lire le journal de l'étape. « Moins de 500 courses FFA : collecte suspecte » est un garde-fou volontaire : le site en ligne n'est pas remplacé par des données incomplètes.

## Avant d'en parler autour de toi
Les données viennent des calendriers de la FFA et de la FFTri. Pour un usage perso, pas de souci ; pour un site public (et à plus forte raison avec de la publicité), il faut leur accord. La page est marquée `noindex` : elle n'apparaît pas dans les moteurs de recherche.

## Lancer la collecte sur un PC (facultatif)
```
pip install -r scraper/requirements.txt
python scraper/build.py --mois 11                # tout
python scraper/build.py --mois 2 --sans-fiches   # test rapide
python -m http.server -d site                    # puis http://localhost:8000
```
