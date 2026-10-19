#!/usr/bin/env python3
"""Hlídač NRB – Úvěr Expanze: dá vědět, když se znovu otevře příjem žádostí nebo se na webu objeví něco nového.

Sleduje:
  1. texty o žádostech/výzvách na stránce Úvěr Expanze (hlavně zmizení hlášky „pozastaven“),
  2. nadpisy sekcí na té stránce (nová sekce / kategorie),
  3. odkazy na té stránce (nová podstránka, výzva, dokument),
  4. mapu webu nrb.cz (nové stránky týkající se Expanze, úvěrů, výzev, programů).
Při změně pošle notifikaci (ntfy / Telegram jako hlidac.py).
"""
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from hlidac import notify

URL = "https://www.nrb.cz/produkt/uver-expanze/"
WEB = "https://www.nrb.cz"
SITEMAPY = ["/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml"]
DATA = Path(__file__).parent / "data"
SNAPSHOT = DATA / "nrb_stav.txt"
STRUKTURA = DATA / "nrb_struktura.json"
TITLE = "NRB Úvěr Expanze"
KLICOVA_SLOVA = re.compile(
    r"žádost|výzv|příjem|přijím|alokac|vyčerpán|ukončen|pozastaven|otevřen|uzavřen|spuštěn|termín|podat",
    re.IGNORECASE)
ZAJIMAVE_URL = re.compile(r"expanz|uver|vyzv|program|produkt|dotac|zaruk", re.IGNORECASE)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}


class PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "header", "footer", "nav"}
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "tr", "br", "section", "a", "button", "span"}
    HEADINGS = {"h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0
        self.headings, self.links = [], set()
        self._heading = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag in self.HEADINGS:
            self._heading = []
        href = dict(attrs).get("href") if tag == "a" else None
        if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
            self.links.add(urljoin(URL, href).split("#")[0])

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif not self.skip:
            if tag in self.BLOCK:
                self.parts.append("\n")
            if tag in self.HEADINGS and self._heading is not None:
                text = re.sub(r"\s+", " ", "".join(self._heading)).strip()
                if text and text not in self.headings:
                    self.headings.append(text)
                self._heading = None

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self._heading is not None:
                self._heading.append(data)

    def relevant_lines(self):
        lines = [re.sub(r"\s+", " ", l).strip() for l in "".join(self.parts).split("\n")]
        return list(dict.fromkeys(l for l in lines if l and KLICOVA_SLOVA.search(l)))


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def sitemap_urls():
    """Všechny URL z mapy webu (projde i vnořené sitemapy). Vrátí None, když mapa webu neexistuje."""
    for path in SITEMAPY:
        try:
            xml = fetch(WEB + path)
        except Exception:
            continue
        if "<loc>" not in xml:
            continue
        urls, fronta, videno = set(), [xml], set()
        while fronta and len(videno) < 50:
            for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", fronta.pop()):
                loc = loc.replace("&amp;", "&")
                if loc.endswith(".xml") or "sitemap" in loc.rsplit("/", 1)[-1]:
                    if loc not in videno:
                        videno.add(loc)
                        try:
                            fronta.append(fetch(loc))
                        except Exception as e:
                            print("Sitemap nedostupná:", loc, e, file=sys.stderr)
                else:
                    urls.add(loc)
        return urls
    return None


def main():
    p = PageParser()
    p.feed(fetch(URL))
    DATA.mkdir(exist_ok=True)

    # 1) texty o příjmu žádostí
    stav = "\n".join(p.relevant_lines())
    predchozi = SNAPSHOT.read_text() if SNAPSHOT.exists() else None
    SNAPSHOT.write_text(stav)
    print(stav)

    zpravy = []
    if predchozi is not None and "pozastaven" in predchozi and "pozastaven" not in stav:
        notify("🚨 Hláška o pozastavení příjmu žádostí zmizela – pravděpodobně se znovu přijímají žádosti!\n"
               f"{stav[:600]}\n{URL}", title=TITLE + " – OTEVŘENO?")
    elif predchozi is not None and stav != predchozi:
        nove = [l for l in stav.splitlines() if l not in predchozi.splitlines()]
        zpravy.append("Změněný text o žádostech:\n" + "\n".join(nove)[:600])

    # 2) – 4) struktura stránky a webu
    odkazy = sorted(l for l in p.links if urlparse(l).netloc.endswith("nrb.cz") or l.lower().endswith(".pdf"))
    mapa = sitemap_urls()
    struktura = {
        "nadpisy": p.headings,
        "odkazy": odkazy,
        "mapa_webu": sorted(u for u in mapa if ZAJIMAVE_URL.search(u)) if mapa is not None else None,
    }
    stara = json.loads(STRUKTURA.read_text()) if STRUKTURA.exists() else None
    STRUKTURA.write_text(json.dumps(struktura, ensure_ascii=False, indent=2))
    print(f"Nadpisů: {len(p.headings)}, odkazů: {len(odkazy)}, "
          f"stránek v mapě webu: {'nenalezena' if mapa is None else len(struktura['mapa_webu'])}")

    if stara:
        popisky = {"nadpisy": "Nové sekce na stránce", "odkazy": "Nové odkazy na stránce",
                   "mapa_webu": "Nové stránky na webu NRB"}
        for klic, popis in popisky.items():
            if struktura[klic] is None or stara.get(klic) is None:
                continue
            pridane = [x for x in struktura[klic] if x not in stara[klic]]
            if pridane:
                zpravy.append(f"{popis}:\n" + "\n".join(pridane[:10]))

    if predchozi is None:
        notify(f"Hlídání spuštěno.\n{stav[:600]}", title=TITLE)
    elif zpravy:
        notify("Změna u NRB – zkontroluj, zda se znovu vypsaly výzvy.\n\n" + "\n\n".join(zpravy)[:1500]
               + f"\n\n{URL}", title=TITLE)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Chyba:", e, file=sys.stderr)
        sys.exit(1)
