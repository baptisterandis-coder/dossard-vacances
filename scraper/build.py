"""Construit site/data/courses.json à partir des calendriers FFA et FFTri.

Usage : python scraper/build.py [--mois 11] [--sans-fiches]
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import ffa  # noqa: E402
import fftri  # noqa: E402
from common import Geocoder  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "site", "data", "courses.json")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mois", type=int, default=11, help="nombre de mois à couvrir à partir d'aujourd'hui")
    ap.add_argument("--sans-fiches", action="store_true", help="ne pas lire les fiches FFA (plus rapide, sans distances ni prix)")
    args = ap.parse_args()

    start = dt.date.today()
    end = start + dt.timedelta(days=int(args.mois * 30.5))
    log(f"Période : {start} → {end}")

    geo = Geocoder()

    log("FFA : liste des compétitions")
    rows = ffa.crawl_list(start, end, log)
    log(f"FFA : {len(rows)} courses hors stade")
    if not args.sans_fiches:
        log("FFA : lecture des fiches")
        ffa.crawl_details(rows, log)
    log("Géocodage des communes")
    courses = []
    for i, r in enumerate(rows):
        courses.append(ffa.to_slim(r, geo))
        if i % 500 == 0:
            geo.save()
    geo.save()

    log("FFTri : calendrier")
    try:
        tri = fftri.crawl(start, end, log)
        log(f"FFTri : {len(tri)} épreuves")
        courses += tri
    except Exception as e:  # le triathlon ne doit pas bloquer la mise à jour
        log(f"FFTri : échec ({e})")

    # garde-fou : si la collecte a manifestement échoué, on ne remplace pas les données en ligne
    if len([c for c in courses if not c["id"].startswith("tri-")]) < 500:
        log("Moins de 500 courses FFA : collecte suspecte, fichier non remplacé.")
        sys.exit(1)

    courses.sort(key=lambda c: (c["d"], c["n"]))
    sans_gps = sum(1 for c in courses if c.get("la") is None)
    data = {
        "meta": {
            "maj": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "perimetre": f"France, {start.strftime('%m/%Y')} → {end.strftime('%m/%Y')}",
            "sources": ["Calendrier officiel FFA (athle.fr)", "Calendrier officiel FFTri (fftri.t2area.com)"],
            "total": len(courses),
            "sans_gps": sans_gps,
        },
        "courses": courses,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log(f"Écrit : {len(courses)} courses ({sans_gps} sans GPS), {os.path.getsize(OUT) // 1024} Ko")


if __name__ == "__main__":
    main()
