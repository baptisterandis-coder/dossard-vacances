"""Calendrier officiel de la Fédération Française d'Athlétisme (athle.fr).

Hors stade uniquement : route, trail, cross, marche. La liste est interrogée
ligue par ligue et semaine par semaine (le site plafonne à 250 résultats par
recherche) ; chaque fiche est ensuite lue pour les distances, le dénivelé,
le prix d'inscription et le site de l'organisateur.
"""
import datetime as dt
import re
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from common import get, pad, session

BASE = "https://www.athle.fr"
LIGUES = ["ARA", "BFC", "BRE", "CEN", "COR", "G-E", "H-F", "I-F", "N-A", "NOR", "OCC", "P-L", "PCA"]
MOIS = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
        "aout": 8, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12}
CAP = 250  # plafond de résultats du site


def saison(d):
    """La saison FFA N va du 1er septembre N-1 au 31 août N."""
    return d.year + 1 if d.month >= 9 else d.year


def list_url(d1, d2, extra):
    return (f"{BASE}/bases/liste.aspx?frmpostback=true&frmbase=calendrier&frmmode=1&frmespace=0"
            f"&frmsaisonffa={saison(d1)}&frmdate1={d1.isoformat()}&frmdate2={d2.isoformat()}&{extra}")


def parse_date(txt, ref):
    """'25-26 septembre' ou '30 septembre-02 octobre' -> (début, fin), en prenant l'année la plus proche de ref."""
    t = txt.lower()
    days = [int(x) for x in re.findall(r"\d{1,2}", t)]
    months = [MOIS[m] for m in re.findall(r"[a-zéû]+", t) if m in MOIS]
    if not days or not months:
        return None, None
    m_end = months[-1]
    m_start = months[0] if len(months) > 1 else m_end

    def pick(day, month):
        cands = [dt.date(y, month, day) for y in (ref.year - 1, ref.year, ref.year + 1)
                 if _valid(y, month, day)]
        return min(cands, key=lambda c: abs((c - ref).days)) if cands else None

    return pick(days[0], m_start), pick(days[-1], m_end)


def _valid(y, m, d):
    try:
        dt.date(y, m, d)
        return True
    except ValueError:
        return False


def parse_list(html, ref):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        a0 = tr.find("a", title=re.compile(r"^Comp.tition num.ro"))
        if not a0:
            continue
        td = tr.find_all("td")
        if len(td) < 5:
            continue
        ffa_id = re.sub(r"\D", "", a0["title"])
        d1, d2 = parse_date(td[0].get_text(" ", strip=True), ref)
        links = td[2].find_all("a")
        ville = (td[2].contents[0].strip() if td[2].contents and isinstance(td[2].contents[0], str)
                 else td[2].get_text(" ", strip=True).split(" ")[0])
        det = tr.find("a", href=re.compile(r"^/competitions/"))
        out.append({
            "id": ffa_id,
            "nom": td[1].get_text(" ", strip=True),
            "debut": d1, "fin": d2,
            "ville": ville,
            "dep": links[0].get_text(strip=True) if links else "",
            "ligue": links[1].get_text(strip=True) if len(links) > 1 else "",
            "type": td[3].get_text(" / ", strip=True),
            "niveau": td[4].get_text(" ", strip=True),
            "det": det["href"] if det else None,
        })
    return out


def keep(row):
    t = row["type"]
    return bool(re.match(r"(Running|Cross|Marche)", t)) and "Animation Jeunes" not in t and row["debut"]


def crawl_list(start, end, log=print):
    s = session()
    rows = {}

    def fetch(d1, d2, extra):
        r = get(s, list_url(d1, d2, extra))
        time.sleep(0.2)
        return parse_list(r.text, d1) if r is not None else None

    # semaines (coupées au 1er septembre, changement de saison)
    weeks, w = [], start
    while w <= end:
        we = min(w + dt.timedelta(days=6), end)
        sept = dt.date(w.year, 9, 1)
        if w < sept <= we:
            weeks += [(w, sept - dt.timedelta(days=1)), (sept, we)]
        else:
            weeks.append((w, we))
        w = we + dt.timedelta(days=1)

    for i, (a, b) in enumerate(weeks):
        for lig in LIGUES:
            got = fetch(a, b, f"frmligue={lig}")
            if got is None:
                log(f"  échec {a} {lig}")
                continue
            if len(got) >= CAP:  # trop de résultats : on redécoupe jour par jour
                d = a
                got = []
                while d <= b:
                    part = fetch(d, d, f"frmligue={lig}") or []
                    if len(part) >= CAP:
                        log(f"  plafond atteint le {d} en {lig} : des courses peuvent manquer")
                    got += part
                    d += dt.timedelta(days=1)
            for r in got:
                rows.setdefault(r["id"], r)
        if i % 5 == 0:
            log(f"  semaine {a} : {len(rows)} compétitions")
    return [r for r in rows.values() if keep(r)]


def parse_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    eps = []
    sec = soup.find(id="epreuves")
    for card in (sec.select(".club-card") if sec else []):
        nom = card.find("h3").get_text(" ", strip=True) if card.find("h3") else ""
        p = card.find("p", class_="text-dark-grey")
        dist_txt = p.get_text(" ", strip=True) if p else ""
        txt = card.get_text(" ", strip=True)
        dm = re.search(r"-\s*(\d+)\s*m", dist_txt)
        dp = re.search(r"(\d+)\s*m D\+", dist_txt)
        px = re.search(r"Montant Inscription\s*:\s*([\d.,]+)", txt)
        eps.append({
            "nom": re.sub(r"^\d{1,2}:\d{2}\s*-\s*", "", nom),
            "m": int(dm.group(1)) if dm else None,
            "dplus": int(dp.group(1)) if dp else None,
            "prix": float(px.group(1).replace(",", ".")) if px else None,
        })
    site = None
    m = re.search(r"Site internet\s*:\s*(\S+)", soup.get_text("\n"))
    if m and m.group(1) != "-" and re.match(r"https?://[^/\s]+\.[^/\s]+", m.group(1)):
        site = m.group(1)
    return eps, site


def crawl_details(rows, log=print, workers=4):
    s = session()

    def one(r):
        if not r.get("det"):
            return
        resp = get(s, BASE + r["det"])
        time.sleep(0.15)
        if resp is not None:
            r["epreuves"], r["site"] = parse_detail(resp.text)

    with ThreadPoolExecutor(workers) as ex:
        for i, _ in enumerate(ex.map(one, rows)):
            if i % 250 == 0:
                log(f"  fiches : {i}/{len(rows)}")
    return rows


TRAIL_RE = re.compile(r"trail|nature|montagne", re.I)


def to_slim(r, geo):
    """Format compact partagé avec la page web."""
    nom = re.sub(r"^Annul[ée]\s*-\s*", "", r["nom"], flags=re.I)
    eps = [e for e in r.get("epreuves", []) if not e["m"] or e["m"] >= 1500]
    t = r["type"]
    if t.startswith("Cross"):
        kind = "c"
    elif t.startswith("Marche"):
        kind = "m"
    elif TRAIL_RE.search(nom) or any(TRAIL_RE.search(e["nom"]) or (e["dplus"] or 0) >= 100 for e in eps):
        kind = "t"
    else:
        kind = "r"
    g = geo.locate(r["ville"], r["dep"]) or {}
    out = {"id": r["id"], "n": nom, "d": r["debut"].isoformat()}
    if r["fin"] and r["fin"] != r["debut"]:
        out["f"] = r["fin"].isoformat()
    out.update({"v": g.get("nom") or r["ville"].title(), "dp": r["dep"], "la": g.get("lat"), "lo": g.get("lon"), "t": kind})
    if re.match(r"^Annul", r["nom"], re.I):
        out["x"] = 1
    dists, seen = [], set()
    for e in eps:
        if not e["m"]:
            continue
        v = [e["m"], e["dplus"]] if (e["dplus"] or 0) >= 50 else e["m"]
        k = str(v)
        if k not in seen:
            seen.add(k)
            dists.append(v)
    if dists:
        out["e"] = dists
    prix = {}
    for e in eps:
        if e["m"] and e["prix"] and e["prix"] > 0:
            prix[e["m"]] = min(prix.get(e["m"], 1e9), e["prix"])
    if prix:
        out["p"] = [[m, p] for m, p in prix.items()]
    if r.get("site"):
        out["s"] = r["site"]
    if r.get("det"):
        out["l"] = r["det"].rsplit("/", 1)[-1]
    return out
