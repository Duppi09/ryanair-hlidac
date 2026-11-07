#!/usr/bin/env python3
"""Převede textové soubory z banka/*.txt na otazky.json pro cvičnou aplikaci.

Formát souborů:
  # tema: id | Název tématu
  Q: otázka s výběrem      (+ správná možnost, - špatná možnost)
  N: číselná otázka        (= hodnota | tolerance | jednotka)
  E: vysvětlení
  Z: zdroj (školní materiál)
Prázdný řádek odděluje otázky.

ID otázky = téma + krátký hash textu, takže zůstává stejné, i když se
otázky přeskládají nebo přidají nové (statistiky v aplikaci se neztratí).
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def qid(topic, text):
    return topic + "-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def parse(path):
    topics, questions = [], []
    topic = None
    cur = None

    def flush():
        nonlocal cur
        if cur is None:
            return
        problems = []
        if cur["typ"] == "vyber":
            right = [o for o in cur["moznosti"] if o["ok"]]
            if len(right) != 1:
                problems.append("musí mít právě jednu správnou možnost (+)")
            if len(cur["moznosti"]) < 2:
                problems.append("málo možností")
        elif "odpoved" not in cur:
            problems.append("chybí řádek '= hodnota | tolerance | jednotka'")
        if not cur.get("vysvetleni"):
            problems.append("chybí vysvětlení (E:)")
        if problems:
            sys.exit(f"{path}: otázka „{cur['otazka']}“: " + "; ".join(problems))
        questions.append(cur)
        cur = None

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s:
                flush()
                continue
            if s.startswith("# tema:"):
                flush()
                tid, name = [p.strip() for p in s[len("# tema:"):].split("|", 1)]
                topic = tid
                topics.append({"id": tid, "nazev": name})
                continue
            if s.startswith("#"):
                continue
            tag, _, rest = s.partition(":") if s[:2] in ("Q:", "N:", "E:", "Z:") else (s[0], "", s[1:])
            rest = rest.strip()
            if s.startswith("Q:") or s.startswith("N:"):
                flush()
                if topic is None:
                    sys.exit(f"{path}: otázka před prvním '# tema:'")
                cur = {
                    "id": qid(topic, rest),
                    "tema": topic,
                    "typ": "vyber" if s.startswith("Q:") else "cislo",
                    "otazka": rest,
                }
                if cur["typ"] == "vyber":
                    cur["moznosti"] = []
            elif s[0] in "+-" and cur and cur["typ"] == "vyber":
                cur["moznosti"].append({"t": s[1:].strip(), "ok": s[0] == "+"})
            elif s.startswith("=") and cur and cur["typ"] == "cislo":
                parts = [p.strip() for p in s[1:].split("|")]
                cur["odpoved"] = float(parts[0].replace(",", "."))
                cur["tolerance"] = float(parts[1].replace(",", ".")) if len(parts) > 1 and parts[1] else 0
                cur["jednotka"] = parts[2] if len(parts) > 2 else ""
            elif s.startswith("E:") and cur:
                cur["vysvetleni"] = rest
            elif s.startswith("Z:") and cur:
                cur["zdroj"] = rest
            else:
                sys.exit(f"{path}: nerozumím řádku: {line}")
    flush()
    return topics, questions


def main():
    all_topics, all_q = [], []
    for path in sorted(glob.glob(os.path.join(HERE, "banka", "*.txt"))):
        t, q = parse(path)
        all_topics += t
        all_q += q
    ids = [q["id"] for q in all_q]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f"Duplicitní otázky: {dup}")
    known = {t["id"] for t in all_topics}
    # sloučit opakované hlavičky stejného tématu
    seen, topics = set(), []
    for t in all_topics:
        if t["id"] not in seen:
            seen.add(t["id"])
            topics.append(t)
    for t in topics:
        t["pocet"] = sum(1 for q in all_q if q["tema"] == t["id"])
    out = {"verze": hashlib.sha1("".join(ids).encode()).hexdigest()[:10], "temata": topics, "otazky": all_q}
    with open(os.path.join(HERE, "otazky.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(all_q)} otázek v {len(topics)} tématech")
    for t in topics:
        print(f"  {t['id']:14} {t['pocet']:3}  {t['nazev']}")
    assert known


if __name__ == "__main__":
    main()
