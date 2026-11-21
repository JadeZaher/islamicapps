# Backups

Off-machine copies in a private Railway Storage Bucket: the datasets, the production Postgres dump, the build inputs of the live database and the final Neo4j export. Sections: [datasets](#dataset-backups) (below), [database](#database-backups), [build inputs](#build-inputs-of-the-live-database), [Neo4j](neo4j-final-dump.md).

## Dataset backups

The datasets exist nowhere else.

| | |
|---|---|
| Railway project / environment | `hadith-ontology` (`43973172-fd19-4c41-8097-369cf805cbe6`) / `production` (`e967d839-d678-4d56-9984-b60e7fc2029d`) |
| Bucket (display name) | `dataset-backups` (id `86f65c11-980e-49cb-8b36-e096dcb09c16`), region `iad` (US East), private |
| Actual S3 bucket name | shown by `railway bucket credentials --bucket dataset-backups` (`BUCKET`; display name + hash) |
| Endpoint | `https://t3.storageapi.dev`, virtual-host style, region `auto` |
| Backup `2026-11-21` | 482 files, 2,878 MB under key prefix `2026-11-21/` (paths mirror `datasets/`) |
| Manifest | [`dataset-backup-2026-11-21.manifest.jsonl`](dataset-backup-2026-11-21.manifest.jsonl): `{path, bytes, sha256}` per file |

Each object also carries `x-amz-meta-sha256`, which is what makes re-runs skip files that are already uploaded.

## What is backed up

Everything under `datasets/` except the exclusions below: canonical `all_hadiths_*.csv[.gz]` and the dated `all_hadiths_unified.csv.bak-*` snapshots, `archive/`, `narrator-data/`, `sources/` (docs, `sources/` minus `external/`), per-tradition folders (`shia-hadith`, `zaydi-hadith`, `ibadi-hadith`, `rida-hadith`, `sheikahmad`, `openiti-sources`), `reconciled/`, `diagnostics/`, registries, manifests, curation files, `neo4j_export/`, `pg_export/`, `algo_candidates/`, tests, scripts, and `machine_translation_candidates/*.jsonl` (the translation OUTPUT files).

## What is NOT backed up

| Excluded | Size | Why |
|---|---|---|
| `datasets/hadith-data/development/` | 9.04 GB | regenerable build outputs; the inputs of the live database are backed up separately ([build inputs](#build-inputs-of-the-live-database)) |
| `datasets/sources/external/` | 1.72 GB | being downloaded by another process; re-download from upstream |
| `*.sqlite3`, `*.sqlite3-wal`, `*.sqlite3-shm` (all under `machine_translation_candidates/`) | 2.03 GB + 0.16 GB + 0.2 MB | regenerable resumable-run journals; the `.jsonl` outputs are backed up |
| `*.lock`, `__pycache__/`, `*.pyc` | ~1.7 MB | transient |
| `datasets/hadith-data/curation_backlog.csv` (16.4 MB), `curation_manifest.json` (16.5 KB), `curation_candidate_manifest.json` (16.5 KB) | 16.4 MB | access-denied at the OS level when the backup ran; **not backed up** |

The exclusion rules live in `src/scripts/ops/backup-datasets.py` (`EXCLUDED_*`). Run `python src/scripts/ops/backup-datasets.py plan` to see the current include/exclude/unreadable summary.

## Restore a file

Credentials: `railway bucket credentials --bucket dataset-backups --json` (never commit them). Export them as env vars, then use any S3 client:

```bash
export BACKUP_S3_ENDPOINT=https://t3.storageapi.dev
export BACKUP_S3_BUCKET=<BUCKET from credentials>
export BACKUP_S3_ACCESS_KEY_ID=<accessKeyId>
export BACKUP_S3_SECRET_ACCESS_KEY=<secretAccessKey>

# restore one file into a NEW directory (do not overwrite live data blindly)
python - <<'PY'
import os, boto3
from botocore.config import Config
s3 = boto3.client("s3", endpoint_url=os.environ["BACKUP_S3_ENDPOINT"], region_name="auto",
    aws_access_key_id=os.environ["BACKUP_S3_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["BACKUP_S3_SECRET_ACCESS_KEY"],
    config=Config(s3={"addressing_style": "virtual"}, request_checksum_calculation="when_required", response_checksum_validation="when_required"))
s3.download_file(os.environ["BACKUP_S3_BUCKET"], "2026-11-21/<relative/path/under/datasets>", "<local destination>")
PY
```

With the AWS CLI: `aws s3 cp s3://$BACKUP_S3_BUCKET/2026-11-21/<path> <dest> --endpoint-url $BACKUP_S3_ENDPOINT` (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY set from the two credential values, `AWS_REQUEST_CHECKSUM_CALCULATION=when_required`). Check the result against `sha256` in the manifest (`sha256sum <file>`).

## Run the backup again

Requires `boto3` (`pip install --user boto3`). Set the four `BACKUP_S3_*` variables as above, then:

```bash
python src/scripts/ops/backup-datasets.py plan                       # what would be included / excluded
python src/scripts/ops/backup-datasets.py upload --prefix YYYY-MM-DD --manifest docs/backups/dataset-backup-YYYY-MM-DD.manifest.jsonl
python src/scripts/ops/backup-datasets.py verify --prefix YYYY-MM-DD --manifest docs/backups/dataset-backup-YYYY-MM-DD.manifest.jsonl
```

`upload` hashes every file, writes the manifest, then uploads with 4 workers (multipart for files over 64 MB). Re-running with the same prefix and manifest is a resume: objects whose size and `sha256` metadata already match are skipped (pass `--rehash` to recompute the manifest). It never deletes local or remote data. A new date prefix makes a new full copy; delete old prefixes manually only when you decide to.

## Cost

Railway Storage Buckets cost **$0.015 per GB-month**; S3 operations and bucket egress are free; usage is averaged daily and rounded up to a whole GB-month (source: <https://docs.railway.com/storage-buckets/billing>). Uploading from this machine is not Railway service egress.

2.878 GB is billed as 3 GB-month: **about $0.045 per month** (about $0.043 unrounded). Each additional full dated copy adds the same amount. Plan limits (Hobby 1 TB, Pro unlimited, Free/Trial caps) are on the same page. Railway buckets currently lack versioning, object lock and server-side encryption (<https://docs.railway.com/storage-buckets>), so the manifest hashes are the integrity record.

## Database backups

Script: `src/scripts/ops/backup-database.py` (credentials from environment only; nothing is printed or written to disk). Subcommands: `run` (preflight, dump, SHA-256, upload, verify), `verify`, `retention` (reports only), `put` (upload files with hashes).

| Backup | Key prefix | Dataset version | Dump |
|---|---|---|---|
| 2026-11-21, migrations 0000 to 0009 | `db/2026-11-21/` | `e2430eae674e...` (complete) | 136,980,800 bytes, 88 s, SHA-256 `30c996ad6788a88dfd3a67aa48aad7523d546c70743fc2fb33a12233fb24bc8d` |
| 2026-11-21, migrations 0000 to 0011 (taken after another lane migrated production) | `db/2026-11-21-schema0011/` | `e2430eae674e...` (complete) | 137,057,209 bytes, 166 s, SHA-256 `e812694680b0a93779ede2cf9ef8501a73752efc700bd532b4757d199acca51c` |

Each prefix holds `railway-<date>.dump` (custom format, gzip level 6, `--no-owner --no-acl`), `.sha256` and `.meta.json` (server version, dataset versions, whether a load was running, timings). No load was in progress for either dump. The production database is 1.8 GB on disk and dumps to about 137 MB.

`pg_dump` must be at least the server's major version (18). The machine has only 16 and 17, so the script runs `pg_dump` and `psql` in a `postgres:18` podman container (override with `BACKUP_PG_IMAGE`, or `BACKUP_PG_DUMP=<dir with pg_dump>` for a local binary). Start the podman machine first (`podman machine start`) and stop it afterwards (`podman machine stop`).

### Run it

```bash
export BACKUP_DATABASE_URL=<production URL>            # the value of DATABASE_URL_PRODUCTION
# plus the four BACKUP_S3_* variables from "Restore a file" above
python src/scripts/ops/backup-database.py run --workdir <scratch dir> --delete-local
python src/scripts/ops/backup-database.py verify --prefix db/YYYY-MM-DD
python src/scripts/ops/backup-database.py retention --keep 8
```

`run` deletes nothing remote; `--delete-local` removes only the local dump, and only after the uploaded copy has been listed and re-hashed. The prefix is `db/<date>` (`--date` to override); re-running the same date overwrites that date's objects, so use a distinct `--date` for a second dump on one day.

### Retention (described, not automatic)

Proposed: keep the newest 8 dumps plus the first dump of each month. `retention --keep N` marks older prefixes `REVIEW`; delete them by hand only after deciding. Nothing in the tooling deletes remote data.

### Restore

1. Fetch the dump and its `.sha256` (S3 client as in "Restore a file"; key `db/<date>/railway-<date>.dump`) and check `sha256sum -c`.
2. Create an empty database on a PostgreSQL 18 server that has `vector`, `pg_trgm` and `unaccent` available (Railway's Postgres service does): `create database <name>;`.
3. `pg_restore --dbname=<url> --no-owner --no-acl --exit-on-error -j 2 railway-<date>.dump` (use the `postgres:18` image if no local client is 17 or newer).
4. If the dump predates the current migrations, `npm run db:migrate` (expand-only), then `npm run db:verify` and `npm run db:verify-data`, both with `DATABASE_URL` pointing at the restored database (an exported variable wins over `.env.local`).
5. To make the restored database production, point the app's `DATABASE_URL` at it; do not restore over the live `railway` database without deciding to.

### Restore drill (2026-11-21)

Restored `db/2026-11-21/` into scratch database `restore_drill_20261121` on the production server, then dropped it.

| Step | Result |
|---|---|
| `pg_restore -j 2` of the 137 MB dump | 524 s, exit 0, no errors |
| Catalog after restore | 55 tables, 10 views, 1 materialized view, 136 indexes, 4 extensions: identical to production's catalog at the dump's migration level (production has since gained 0010 and 0011) |
| Row counts and checksum | `hadiths` 99,283 with identical md5 over `id \|\| arabic_sha256`; `chains` 114,597; `chain_mentions` 538,513; `narrators` 24,326; `translations` 66,776; `hadith_assessments` 44,937; dataset version `e2430eae674e...` complete: all equal to production |
| `npm run db:migrate` on the restored copy | 8 s; migrations 0010 and 0011 applied |
| `npm run db:verify` | OK: catalog matches `src/db/schema` (48 tables, 11 views, 154 foreign keys, 12 of 12 migrations) |
| `npm run db:verify-data` | OK: every data invariant passes (0 violations; 154 foreign keys, 0 orphans) |
| Size | restored 1,196 MB against 1,811 MB for the live database (live carries dead space from repeated loads and index builds) |

The second dump (`db/2026-11-21-schema0011/`) was checked with `pg_restore --list` (49 table-data entries) but not fully restored.

## Build inputs of the live database

Prefix `development-inputs/2026-11-21/` (114 files, 1,349,687,039 bytes; paths mirror `datasets/`), manifest [`development-inputs-2026-11-21.manifest.jsonl`](development-inputs-2026-11-21.manifest.jsonl):

- `hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: the schema v2 input (`input_dataset_sha256 feeeb38d...`) the bundle was built from.
- `hadith-data/development/pg-load-2026-11-21/bundle/`: the source bundle (content hash `c4e5e12e...`).
- `hadith-data/development/pg-load-2026-11-21/projection-v3/`: the projection production was loaded from (content hash `e2430eae...`, version 2026.11.21.3).
- the top-level load logs, reports and catalogs of `pg-load-2026-11-21/` (production load log `prod-load-2.log`).

Skipped as superseded: `projection/`, `projection-repeat/`, `projection-v2/`, `projection-candidates/`, `superseded/`. Other inputs (`datasets/narrator-data/all_rawis.csv`, `all_hadiths_unified.csv.gz`, the reconciled sidecars, the report-correspondence output) are already in the `2026-11-21/` dataset backup. A sample of 9 objects (the 3 largest and 6 random) was re-downloaded and re-hashed: all match.

Still access-denied and therefore **not backed up**: `datasets/hadith-data/curation_backlog.csv` (16,357,722 bytes), `curation_manifest.json` and `curation_candidate_manifest.json` (16,459 bytes each). Once the owner unlocks them from an elevated shell, `python src/scripts/ops/backup-datasets.py upload --rehash` picks them up (existing objects are skipped).

## Bucket contents and monthly cost (2026-11-21)

| Prefix | Objects | Bytes |
|---|---|---|
| `2026-11-21/` (datasets) | 482 | 2,878,145,482 |
| `db/2026-11-21/` | 3 | 136,981,352 |
| `db/2026-11-21-schema0011/` | 3 | 137,057,784 |
| `development-inputs/2026-11-21/` | 114 | 1,349,687,039 |
| `neo4j-final/2026-11-21/` | 3 | 70,620,023 |
| Total | 605 | 4,572,491,680 (4.57 GB) |

At $0.015 per GB-month, rounded up to 5 GB-month: about **$0.075 per month** (unrounded $0.069). Source: <https://docs.railway.com/storage-buckets/billing> (see Cost above). Each further 137 MB database dump kept adds about $0.002 per month.

## Proposed schedule (not created)

Railway cron service, weekly:

1. New service in the project from this repository with a small Dockerfile based on `postgres:18` plus `python3 python3-boto3`, copying `src/scripts/ops/backup-database.py`; start command `python3 src/scripts/ops/backup-database.py run --workdir /tmp/dump --delete-local`. `pg_dump` is then local: set `BACKUP_PG_DUMP=/usr/lib/postgresql/18/bin`.
2. Variables on that service: `BACKUP_DATABASE_URL` as a reference to the Postgres private URL (no public egress), and the four `BACKUP_S3_*` variables from the bucket's credentials.
3. Settings, Cron Schedule: `0 3 * * 0` (Sundays 03:00 UTC). Railway schedules are UTC, runs must be at least 5 minutes apart, and the process must exit when done or later runs are skipped (<https://docs.railway.com/cron-jobs>). The service needs about 140 MB of scratch space in `/tmp`.
4. Locally instead: a Windows Task Scheduler weekly task running the `run` command with the environment set from `railway bucket credentials` and `.env.local`, after `podman machine start` (and `podman machine stop` afterwards).

Railway's own volume backups (data architecture section 2.5) are separate and expire; this off-platform dump is the durable copy.

## Operations notes (2026-11-21)

- `railway.json` migration, not applied. `railway config migrate` (dry run) emits `.railway/railway.ts` with only the health check (`/api/health`, 120 s) and a comment for builder and Dockerfile path: it drops `restartPolicyType ON_FAILURE` and `restartPolicyMaxRetries 5`, and `--apply` clears the service's config-file settings and then needs `railway config apply` for the whole project. Steps before 2026-12-01: run `railway config migrate --apply`, add the restart policy to the generated service by hand (check the field names in the generated types), run `railway config plan` and require that it shows no change to services other than `islamicapps` and nothing destructive, then `railway config apply`, then confirm the deployed service settings (health check, restart policy, Dockerfile builder) in the dashboard.
- Public access to Postgres is the TCP proxy `shortline.proxy.rlwy.net:42750`. This machine uses it for operator loads and backups, so removing it breaks them. Remove it only after moving loads and backups into Railway (the cron service above reaches Postgres over the private network).
