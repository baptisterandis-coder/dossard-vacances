"""Calendrier officiel de la Fédération Française de Triathlon (fftri.t2area.com).

Le formulaire de filtres est envoyé une fois (la sélection est gardée en
session), puis la liste se lit par pages de 10 via ?limitstart=N.
Les coordonnées GPS sont fournies par le site.
"""
import re
import time

from bs4 import BeautifulSoup

from common import get, pad, session

BASE = "https://fftri.t2area.com"
MOIS = {"JANV.": 1, "JAN.": 1, "FÉVR.": 2, "FÉV.": 2, "FEV.": 2, "MARS": 3, "AVR.": 4, "MAI": 5, "JUIN": 6,
        "JUIL.": 7, "AOÛT": 8, "AOUT": 8, "SEPT.": 9, "OCT.": 10, "NOV.": 11, "DÉC.": 12, "DEC.": 12}
DISC = {"TRI": "Triathlon", "DUA": "Duathlon", "AQUA": "Aquathlon", "B&R": "Bike & Run", "RAID": "Raid",
        "X-DUA": "Cross duathlon", "X-TRI": "Cross triathlon", "S&R": "Swimrun", "S&B": "Swim & Bike",
        "TRI-N": "Triathlon des neiges", "DUA-N": "Duathlon des neiges"}
YOUTH = re.compile(r"(^|-)J(-|$)|J-\d")


def title_city(s):
    s = s.lower()
    s = re.sub(r"(^|[\s\-'’])(\w)", lambda m: m.group(1) + m.group(2).upper(), s)
    return re.sub(r"-(Et|En|Sur|Sous|Les|Le|La|De|Du|Des|Lès|Lez|Aux)-", lambda m: m.group(0).lower(), s)


def parse_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.compact-event-card")
    out = []
    for a in cards:
        ds = a.select_one(".compact-event-card__date").get_text(" ", strip=True).upper()
        m = re.search(r"(\d+)(?:\s*(?:-|AU)\s*(\d+))?\s+(\S+)\s+(\d{4})", ds)
        if not m or m.group(3) not in MOIS:
            continue
        mo, year = MOIS[m.group(3)], m.group(4)
        d1 = f"{year}-{pad(mo)}-{pad(m.group(1))}"
        nom = a.find("h3").get_text(" ", strip=True)
        dep = re.search(r"\((\d{2,3}[AB]?)\)\s*$", nom)
        nom = re.sub(r"\s*\(\d{2,3}[AB]?\)\s*$", "", nom)
        loc = a.select_one(".compact-event-card__location").get_text(" ", strip=True)
        ville, _, cp = [x.strip() for x in loc.partition("·")]
        fmts = [b.get_text(" ", strip=True) for b in a.select(".format-badge")]
        adult = [f for f in fmts if not YOUTH.search(f.split(" - ", 1)[-1])]
        if not adult:
            continue  # épreuves réservées aux jeunes
        discs = list(dict.fromkeys(DISC.get(f.split(" - ")[0], f.split(" - ")[0]) for f in adult))
        link = a.select_one("a.event-link")["href"]
        status = a.select_one(".compact-event-card__status")
        r = {
            "id": "tri-" + link.rsplit("/", 1)[-1].replace(".html", "") + "-" + d1[2:].replace("-", ""),
            "n": nom, "d": d1,
            "v": title_city(ville),
            "dp": (dep.group(1) if dep else cp[:2]).zfill(3),
            "la": round(float(a["data-lat"]), 4) if a.get("data-lat") else None,
            "lo": round(float(a["data-lng"]), 4) if a.get("data-lng") else None,
            "t": "x",
            "dc": " · ".join(discs),
            "fm": [f.replace(" - ", " ").replace("-OP", "").replace("-EQ", " équipe") for f in adult],
            "u": link,
        }
        if m.group(2):
            r["f"] = f"{year}-{pad(mo)}-{pad(m.group(2))}"
        if status and re.search(r"annul", status.get_text(), re.I):
            r["x"] = 1
        out.append(r)
    return out, len(cards), soup


def crawl(start, end, log=print):
    s = session()
    r = get(s, BASE + "/calendrier.html")
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    data = []
    for inp in form.find_all(["input", "select"]):
        name = inp.get("name")
        if not name or inp.get("type") == "checkbox":
            continue  # cases décochées = toutes les ligues, disciplines et distances
        data.append((name, inp.get("value", "")))
    data = [(k, v) for k, v in data if k not in ("filter_date_start", "filter_date_end")]
    data += [("filter_date_start", start.isoformat()), ("filter_date_end", end.isoformat())]
    resp = s.post(form.get("action") or BASE + "/calendrier.html", data=data, timeout=30)
    events, n, page = parse_cards(resp.text)
    total = re.search(r"(\d+)\s*manifestations", page.get_text(" "))
    total = int(total.group(1)) if total else 0
    log(f"  FFTri : {total} manifestations annoncées")
    start_at = n
    while start_at < total:
        time.sleep(0.3)
        r = get(s, f"{BASE}/calendrier.html?limitstart={start_at}")
        if r is None:
            break
        more, n, _ = parse_cards(r.text)
        if not n:
            break
        events += more
        start_at += n
    uniq = {e["id"]: e for e in events}
    return list(uniq.values())
