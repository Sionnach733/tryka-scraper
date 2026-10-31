#!/usr/bin/env bash
# One-off fix: Lisbon Race 6 relay (TR_5GGDDHUF8D) was published with the wrong
# age-group labels. Every other relay uses U40 / 40+, so rename:
#   "40 - 49"     -> "U40"
#   "M40+", "W40+" -> "40+"
# Age-group ranks were already numbered within each of these groups, so only
# the labels change. Idempotent: re-running it is a no-op.
# Note: `scraper.py --force` on this event would bring the old labels back.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

DB=${1:-tryka.db}
EVENT=TR_5GGDDHUF8D

show() {
    sqlite3 -column -header "$DB" "
        SELECT r.gender, r.age_group, COUNT(*) AS teams
        FROM results r JOIN events e ON e.id = r.event_id
        WHERE e.event_id = '$EVENT'
        GROUP BY 1, 2 ORDER BY 1, 2;"
}

echo "== before =="
show

backup="$DB.bak-$(date +%Y%m%d-%H%M%S)-preLisbon6RelayAG"
echo "== backing up $DB to $backup =="
cp "$DB" "$backup"

sqlite3 "$DB" "
BEGIN;
UPDATE results SET age_group = CASE age_group
        WHEN '40 - 49' THEN 'U40'
        ELSE '40+'
    END
WHERE event_id = (SELECT id FROM events WHERE event_id = '$EVENT')
  AND age_group IN ('40 - 49', 'M40+', 'W40+');
SELECT changes() || ' rows updated';
COMMIT;"

echo "== after =="
show
