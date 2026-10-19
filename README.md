# Hlídač letenek Ryanair PRG ⇄ BCN (1. 2. – 5. 2. 2027)

## Lokální spuštění
```bash
python3 hlidac.py
CENOVY_LIMIT=3000 NTFY_TOPIC=moje-tajne-tema-123 python3 hlidac.py
```
Pravidelně třeba přes cron (`crontab -e`):
```
0 8,14,20 * * * cd /cesta/k/ryanair-hlidac && CENOVY_LIMIT=3000 NTFY_TOPIC=moje-tajne-tema-123 python3 hlidac.py >> log.txt 2>&1
```

## Na GitHub Actions (běží zdarma, i když máš vypnutý počítač)
1. Nahraj složku do nového (klidně privátního) repozitáře na GitHubu.
2. Settings → Secrets and variables → Actions:
   - Secret `NTFY_TOPIC` (nebo `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID`)
   - Variable `CENOVY_LIMIT` – např. `3000`
3. Záložka Actions → „Hlídač letenek Ryanair“ → Run workflow (první test).

## Notifikace do mobilu
Nainstaluj aplikaci **ntfy** a přihlas se k odběru tématu se stejným názvem jako `NTFY_TOPIC`.
Zvol si nějaký neuhodnutelný název, protože témata jsou veřejná.

Notifikace přijde při prvním měření, při každém zlevnění, při novém minimu a vždy, když je cena pod limitem.
Historie cen se ukládá do `data/historie.json`.
