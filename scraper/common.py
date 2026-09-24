"""Outils partagés : session HTTP polie, géocodage des communes, dates."""
import json
import os
import re
import time
import unicodedata

import requests

UA = "DossardVacances/1.0 (calendrier perso de courses ; contact via GitHub)"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    return s


def get(s, url, tries=3, **kw):
    """GET avec quelques essais et une pause entre chaque essai."""
    for t in range(tries):
        try:
            r = s.get(url, timeout=30, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 + 3 * t)
    return None


def pad(n):
    return str(n).zfill(2)


def norm(txt):
    txt = unicodedata.normalize("NFD", txt or "")
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", txt.lower().replace("-", " ").replace("'", " ")).strip()


# ---------------------------------------------------------------- géocodage
GEO_CACHE = os.path.join(CACHE_DIR, "geo.json")


class Geocoder:
    """Coordonnées du centre des communes via l'API ouverte geo.api.gouv.fr."""

    def __init__(self):
        self.s = session()
        try:
            with open(GEO_CACHE, encoding="utf-8") as f:
                self.cache = json.load(f)
        except (OSError, ValueError):
            self.cache = {}

    @staticmethod
    def dep_code(dep):
        dep = (dep or "").strip().upper()
        if re.fullmatch(r"0\d\d", dep):
            return dep[1:]
        if re.fullmatch(r"0?2[AB]", dep):
            return dep[-2:]
        return dep

    def locate(self, commune, dep):
        key = f"{commune}|{dep}"
        if key in self.cache:
            return self.cache[key]
        nom = re.sub(r"\bSt\b", "Saint", commune.replace("&amp;", "&"))
        nom = re.sub(r"\bSte\b", "Sainte", nom)
        code = self.dep_code(dep)
        res = None
        base = "https://geo.api.gouv.fr/communes"
        for params in (
            {"nom": nom, "codeDepartement": code, "fields": "nom,centre,codeDepartement", "limit": 1},
            {"nom": nom, "fields": "nom,centre,codeDepartement", "limit": 5},
        ):
            r = get(self.s, base, params=params)
            hits = r.json() if r is not None else []
            # sans département, on n'accepte qu'une commune du bon département
            hits = [h for h in hits if h.get("centre") and (params.get("codeDepartement") or h.get("codeDepartement") == code)]
            if hits:
                h = hits[0]
                lon, lat = h["centre"]["coordinates"]
                res = {"nom": h["nom"], "lat": round(lat, 4), "lon": round(lon, 4)}
                break
            time.sleep(0.05)
        self.cache[key] = res
        return res

    def save(self):
        with open(GEO_CACHE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
