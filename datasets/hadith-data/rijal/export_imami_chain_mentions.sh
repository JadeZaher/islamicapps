#!/usr/bin/env bash
# Snapshot of live Imami chain mentions from the production database (SELECT only, read-only session).
# Writes datasets/hadith-data/rijal/inputs/imami_chain_mentions.tsv.gz (gzip -n: no name or time, so the bytes depend
# only on the data). The connection string is read from .env.local and never printed. Usage (repo root):
#   bash datasets/hadith-data/rijal/export_imami_chain_mentions.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
PSQL="${PSQL:-C:/Program Files/PostgreSQL/16/bin/psql.exe}"
OUT_DIR="datasets/hadith-data/rijal/inputs"
mkdir -p "$OUT_DIR"
TMP="$(mktemp)"
TMP_NATIVE="$(cygpath -m "$TMP" 2>/dev/null || echo "$TMP")"
trap 'rm -f "$TMP"' EXIT
PGURL="$(grep '^DATABASE_URL_PRODUCTION=' .env.local | head -1 | cut -d= -f2- | sed 's/^"//; s/"$//')"
export PGOPTIONS="-c default_transaction_read_only=on"
"$PSQL" -X -q -c "\copy (select m.hadith_id, h.collection_id, m.chain_id, m.position, m.surface_ar,
  m.surface_normalized from chain_mentions m join hadiths h on h.id = m.hadith_id
  where h.tradition_id = 'tradition:imami' and m.retired_at is null and h.retired_at is null
  order by m.chain_id, m.position) to '$TMP_NATIVE' with (format csv, header true, delimiter E'\t')" "$PGURL"
"$PSQL" -X -q -A -t -c "select 'dataset_version=' || id from dataset_versions where is_current" "$PGURL" \
  > "$OUT_DIR/imami_chain_mentions.version.txt"
gzip -n -9 -c "$TMP" > "$OUT_DIR/imami_chain_mentions.tsv.gz"
sha256sum "$OUT_DIR/imami_chain_mentions.tsv.gz"
