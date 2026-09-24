"""Tests des analyseurs sur des extraits réels des pages FFA et FFTri (septembre 2026)."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scraper"))
import ffa  # noqa: E402
import fftri  # noqa: E402

FFA_LIST = """<table><tr class=""><td><a title="Compétition numéro : 323555" href="/bases/liste.aspx?x">24 septembre</a></td><td>Je Cours Pour Toi</td><td>Loos<br><a title="dep" href="/bases/liste.aspx?frmdepartement=059">059</a> - <a title="lig" href="/bases/liste.aspx?frmligue=H-F">H-F</a></td><td>Running<br>Meeting - Course - Cross</td><td>Départemental</td><td>&nbsp;</td><td><a href="/competitions/492846237843914828801849299828847834" target="_blank">+</a></td></tr>
<tr><td><a title="Compétition numéro : 1">30 décembre-02 janvier</a></td><td>Annulé - Corrida Test</td><td>Lille<br><a>059</a> - <a>H-F</a></td><td>Stade<br>Meeting</td><td>Régional</td></tr></table>"""

FFA_DETAIL = """<section id="epreuves"><div class="epreuve-grid"><div class="club-card"><div class="club-card-header"><h3>18:30 - Trail 25km - Trail XS</h3></div><div><p class="text-dark-grey">TCF / TCM - 25000 m / 600 m D+ / 31000 m effort</p><div class="epreuve-info"><p>Montant Inscription : 25</p></div></div></div>
<div class="club-card"><div class="club-card-header"><h3>1/2 Marathon</h3></div><div><p class="text-dark-grey">TCF / TCM - 21100 m</p><p>Certificat de mesurage : X</p><p>Montant Inscription : 30,50</p></div></div></section>
<p>Site internet : https://artemistrailfestival.fr/</p>"""

TRI = """<div class="js-infinite-scroll"><div class="compact-event-list"><article class="compact-event-card" data-lat="50.5205576" data-lng="1.6263551"><div class="compact-event-card__media"><span class="compact-event-card__status ">J-3</span></div><div class="compact-event-card__body"><div class="compact-event-card__date">27 SEPT. 2026</div><h3>Triathlon d'Etaples sur Mer (62)</h3><div class="compact-event-card__location">ÉTAPLES · 62630</div><div class="compact-event-card__formats"><span class="format-badge">TRI - L</span><span class="format-badge">TRI - M</span><span class="format-badge">TRI - J-1</span></div><a href="https://fftri.t2area.com/calendrier/triathlon-d-etaples-sur-mer.html" class="event-link">Voir l'événement</a></div></article>
<article class="compact-event-card" data-lat="50.17" data-lng="3.23"><div class="compact-event-card__body"><div class="compact-event-card__date">26 SEPT. 2026</div><h3>Aquathlon de Cambrai (59)</h3><div class="compact-event-card__location">CAMBRAI · 59400</div><span class="format-badge">AQUA - J-1</span><span class="format-badge">AQUA - XXS-J</span><a href="https://fftri.t2area.com/calendrier/aquathlon-de-cambrai.html" class="event-link">Voir</a></div></article>
<article class="compact-event-card" data-lat="48.87" data-lng="2.63"><span class="compact-event-card__status">Annulée</span><div class="compact-event-card__date">28 FÉV. 2027</div><h3>Cross Duathlon de Melun (77)</h3><div class="compact-event-card__location">LE MÉE-SUR-SEINE · 77350</div><span class="format-badge">X-DUA - S</span><span class="format-badge">B&amp;R - XS-OP-EQ</span><a href="https://fftri.t2area.com/calendrier/cross-duathlon-de-melun.html" class="event-link">Voir</a></article></div></div>
<p>3 manifestations</p>"""


class FakeGeo:
    def locate(self, v, d):
        return {"nom": "Loos", "lat": 50.6078, "lon": 3.0215}


def test_ffa_list():
    rows = ffa.parse_list(FFA_LIST, dt.date(2026, 9, 20))
    assert len(rows) == 2
    r = rows[0]
    assert r["id"] == "323555" and r["ville"] == "Loos" and r["dep"] == "059" and r["ligue"] == "H-F"
    assert r["debut"] == dt.date(2026, 9, 24) and r["type"].startswith("Running")
    assert r["det"].startswith("/competitions/")
    assert ffa.keep(r) and not ffa.keep(rows[1])
    d1, d2 = ffa.parse_date("30 décembre-02 janvier", dt.date(2026, 12, 28))
    assert d1 == dt.date(2026, 12, 30) and d2 == dt.date(2027, 1, 2)
    d1, _ = ffa.parse_date("10 janvier", dt.date(2026, 12, 28))
    assert d1 == dt.date(2027, 1, 10)


def test_ffa_detail_and_slim():
    eps, site = ffa.parse_detail(FFA_DETAIL)
    assert eps[0] == {"nom": "Trail 25km - Trail XS", "m": 25000, "dplus": 600, "prix": 25.0}
    assert eps[1]["m"] == 21100 and eps[1]["prix"] == 30.5
    assert site == "https://artemistrailfestival.fr/"
    row = ffa.parse_list(FFA_LIST, dt.date(2026, 9, 20))[0]
    row["epreuves"], row["site"] = eps, site
    s = ffa.to_slim(row, FakeGeo())
    assert s["t"] == "t" and s["e"] == [[25000, 600], 21100] and [21100, 30.5] in s["p"]
    assert s["la"] == 50.6078 and s["l"] == "492846237843914828801849299828847834"


def test_fftri():
    ev, n, soup = fftri.parse_cards(TRI)
    assert n == 3 and len(ev) == 2  # Cambrai (jeunes uniquement) écarté
    e = ev[0]
    assert e["d"] == "2026-09-27" and e["v"] == "Étaples" and e["dp"] == "062"
    assert e["fm"] == ["TRI L", "TRI M"] and e["dc"] == "Triathlon" and e["la"] == 50.5206
    m = ev[1]
    assert m["d"] == "2027-02-28" and m.get("x") == 1 and m["dp"] == "077"
    assert m["fm"] == ["X-DUA S", "B&R XS équipe"] and m["v"] == "Le Mée-sur-Seine"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
