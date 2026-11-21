# Dataset backups

Off-machine copy of `datasets/` in a private Railway Storage Bucket. The datasets exist nowhere else.

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
| `datasets/hadith-data/development/` | 9.04 GB | regenerable build outputs |
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
