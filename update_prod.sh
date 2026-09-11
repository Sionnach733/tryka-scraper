#!/usr/bin/env bash
# Pull the latest event IDs and fetch any new results into tryka.db.
# Safe to re-run any time: scraper.py skips athletes already stored,
# so a repeat run only fetches genuinely new results (e.g. as a
# still-in-progress race fills in).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "== git pull =="
git pull

if [ -f tryka.db ]; then
    backup="tryka.db.bak-$(date +%Y%m%d-%H%M%S)"
    echo "== backing up tryka.db to $backup =="
    cp tryka.db "$backup"
else
    echo "== no existing tryka.db, skipping backup =="
fi

mkdir -p logs
log="logs/fetch-$(date +%Y%m%d-%H%M%S).log"
echo "== running scraper.py (log: $log) =="

before=0
if [ -f tryka.db ]; then
    before=$(sqlite3 tryka.db "select count(*) from results;")
fi

python3 scraper.py 2>&1 | tee "$log"

after=$(sqlite3 tryka.db "select count(*) from results;")
echo "== done: $before -> $after results ($((after - before)) new) =="
