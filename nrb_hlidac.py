#!/usr/bin/env python3
"""Hlídač stránky NRB – Úvěr Expanze: dá vědět, když se změní stav příjmu žádostí / výzev.

Stáhne stránku, vytáhne z ní text a z něj řádky týkající se žádostí a výzev.
Když se tyto řádky změní oproti minulé kontrole, pošle notifikaci (ntfy / Telegram jako hlidac.py).
"""
import hashlib
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from hlidac import notify

URL = "https://www.nrb.cz/produkt/uver-expanze/"
DATA = Path(__file__).parent / "data"
SNAPSHOT = DATA / "nrb_stav.txt"
KLICOVA_SLOVA = re.compile(
    r"žádost|výzv|příjem|přijím|alokac|vyčerpán|ukončen|pozastaven|otevřen|uzavřen|spuštěn|termín|podat",
    re.IGNORECASE)


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "header", "footer", "nav"}
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "tr", "br", "section", "a", "button", "span"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def relevant_lines(html):
    p = TextExtractor()
    p.feed(html)
    lines = [re.sub(r"\s+", " ", l).strip() for l in "".join(p.parts).split("\n")]
    seen, out = set(), []
    for l in lines:
        if l and KLICOVA_SLOVA.search(l) and l not in seen:
            seen.add(l)
            out.append(l)
    return out


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    DATA.mkdir(exist_ok=True)

    stav = "\n".join(relevant_lines(html))
    predchozi = SNAPSHOT.read_text() if SNAPSHOT.exists() else None
    SNAPSHOT.write_text(stav)
    print(stav)

    if predchozi is None:
        notify(f"NRB Úvěr Expanze – hlídání spuštěno.\n{stav[:600]}", title="NRB Úvěr Expanze")
    elif "pozastaven" in predchozi and "pozastaven" not in stav:
        notify("🚨 NRB Úvěr Expanze: hláška o pozastavení příjmu žádostí zmizela – "
               f"pravděpodobně se znovu přijímají žádosti!\n{stav[:600]}\n{URL}", title="NRB Úvěr Expanze – OTEVŘENO?")
    elif stav != predchozi:
        nove = [l for l in stav.splitlines() if l not in predchozi.splitlines()]
        notify("NRB Úvěr Expanze – změna na stránce! Zkontroluj, zda se znovu vypsaly výzvy.\n"
               + "\n".join(nove)[:800] + f"\n{URL}", title="NRB Úvěr Expanze")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Chyba:", e, file=sys.stderr)
        sys.exit(1)
