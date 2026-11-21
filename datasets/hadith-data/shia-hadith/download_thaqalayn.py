"""Refresh the checked-in Thaqalayn V2 snapshot from the public live REST API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable


API_BASE_URL = "https://www.thaqalayn-api.net/api/v2"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(OUTPUT_DIR, "v2_books")
SNAPSHOT_MANIFEST_NAME = "snapshot_manifest.json"
USER_AGENT = (
    "islamicapps-thaqalayn-refresh/1.0 "
    "(+https://github.com/atooz/islamicapps; scholarly data refresh)"
)
DEFAULT_MAX_WORKERS = 3
DEFAULT_TIMEOUT = 45.0
DEFAULT_RETRIES = 4
DEFAULT_BACKOFF_SECONDS = 1.0
MAX_MANIFEST_ID_SPAN = 100_000

# Curated from the checked-in numbered files; see AGENTS.md, "Freshness and source of truth."
PROVIDER_FILE_ID_BY_BOOK_ID = {
    "Al-Kafi-Volume-1-Kulayni": "1",
    "Al-Kafi-Volume-2-Kulayni": "2",
    "Al-Kafi-Volume-3-Kulayni": "3",
    "Al-Kafi-Volume-4-Kulayni": "4",
    "Al-Kafi-Volume-5-Kulayni": "5",
    "Al-Kafi-Volume-6-Kulayni": "6",
    "Al-Kafi-Volume-7-Kulayni": "7",
    "Al-Kafi-Volume-8-Kulayni": "8",
    "Mujam-al-Ahadith-al-Mutabara-Muhsini": "9",
    "Al-Khisal-Saduq": "10",
    "Uyun-akhbar-al-Rida-Volume-1-Saduq": "11",
    "Uyun-akhbar-al-Rida-Volume-2-Saduq": "12",
    "Al-Amali-Mufid": "13",
    "Al-Tawhid-Saduq": "14",
    "Kitab-al-Duafa-Ghadairi": "17",
    "Kitab-al-Ghayba-Numani": "22",
    "Thawab-al-Amal-wa-iqab-al-Amal-Saduq": "23",
    "Kamil-al-Ziyarat-Qummi": "24",
    "Fadail-al-Shia-Saduq": "25",
    "Sifat-al-Shia-Saduq": "26",
    "Kitab-al-Ghayba-Tusi": "27",
    "Maani-al-Akhbar-Saduq": "28",
    "Al-Amali-Saduq": "29",
    "Kitab-al-Mumin-Ahwazi": "30",
    "Kitab-al-Zuhd-Ahwazi": "31",
    "Nahj-al-Balagha-Radi": "32",
    "Risalat-al-Huquq-Abidin": "33",
    "Man-La-Yahduruh-al-Faqih-Volume-1-Saduq": "34",
    "Man-La-Yahduruh-al-Faqih-Volume-2-Saduq": "35",
    "Man-La-Yahduruh-al-Faqih-Volume-3-Saduq": "36",
    "Man-La-Yahduruh-al-Faqih-Volume-4-Saduq": "37",
    "Man-La-Yahduruh-al-Faqih-Volume-5-Saduq": "38",
    "Kamal-al-Din-wa-Tamam-al-Nima-Saduq": "39",
}


class RefreshError(RuntimeError):
    """Base error for a refresh that must not publish staged files."""


class SourceValidationError(RefreshError):
    """The upstream response or local identity map violated the source contract."""


class _RetryableFetchError(Exception):
    """Internal marker for an HTTP response that is safe to retry."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SourceValidationError(f"{label} must be a positive integer; got {value!r}")
    return value


def _json_bytes(value: Any) -> bytes:
    """Match the checked-in Go encoder's tab indentation and HTML escaping."""
    rendered = json.dumps(value, ensure_ascii=False, indent="\t")
    rendered = (
        rendered.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return rendered.encode("utf-8")


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceValidationError(
            f"Could not read valid UTF-8 JSON from {path}: {error}"
        ) from error


def _write_staged(path: str, payload: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _stdlib_http_get(url: str, *, headers: dict[str, str], timeout: float) -> Any:
    """Open one GET request with only Python's standard library."""
    request = urllib.request.Request(url, headers=headers, method="GET")
    return urllib.request.urlopen(request, timeout=timeout)


def load_provider_file_map(
    books_dir: str = BOOKS_DIR,
    curated_mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Validate numbered payloads against the immutable curated identity map."""
    expected = dict(
        PROVIDER_FILE_ID_BY_BOOK_ID if curated_mapping is None else curated_mapping
    )
    if not expected or len(expected) != len(set(expected.values())):
        raise SourceValidationError(
            "The curated provider mapping must be non-empty and one-to-one"
        )
    for provider_book_id, provider_file_id in expected.items():
        if (
            not isinstance(provider_book_id, str)
            or not provider_book_id
            or provider_book_id != provider_book_id.strip()
            or not isinstance(provider_file_id, str)
            or not provider_file_id.isdigit()
            or str(int(provider_file_id)) != provider_file_id
            or int(provider_file_id) <= 0
        ):
            raise SourceValidationError(
                f"Invalid curated provider mapping entry: "
                f"{provider_book_id!r} -> {provider_file_id!r}"
            )
    try:
        names = os.listdir(books_dir)
    except OSError as error:
        raise SourceValidationError(
            f"Could not inspect existing Thaqalayn files: {error}"
        ) from error

    numeric_names = sorted(
        (name for name in names if name.endswith(".json") and name[:-5].isdigit()),
        key=lambda name: int(name[:-5]),
    )
    if not numeric_names:
        raise SourceValidationError(
            "No checked-in numeric Thaqalayn files are available to establish provider identity"
        )
    observed_filenames = {name[:-5] for name in numeric_names}
    if observed_filenames != set(expected.values()):
        raise SourceValidationError(
            "Numeric provider files do not match the curated provider mapping; "
            f"unexpected={sorted(observed_filenames - set(expected.values()))}, "
            f"missing={sorted(set(expected.values()) - observed_filenames)}"
        )

    expected_by_file = {
        provider_file_id: provider_book_id
        for provider_book_id, provider_file_id in expected.items()
    }
    for name in numeric_names:
        provider_file_id = name[:-5]
        rows = _read_json(os.path.join(books_dir, name))
        if not isinstance(rows, list) or not rows:
            raise SourceValidationError(
                f"Existing provider file {name!r} is not a non-empty array"
            )
        observed: set[str] = set()
        for index, row in enumerate(rows):
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("bookId"), str)
                or not row["bookId"].strip()
            ):
                raise SourceValidationError(
                    f"Existing provider file {name!r} row {index} has no bookId"
                )
            observed.add(row["bookId"])
        if len(observed) != 1:
            raise SourceValidationError(
                f"Existing provider file {name!r} does not contain exactly one nonblank bookId"
            )
        provider_book_id = next(iter(observed))
        if provider_book_id != provider_book_id.strip():
            raise SourceValidationError(
                f"Existing provider file {name!r} has whitespace around bookId"
            )
        expected_book_id = expected_by_file[provider_file_id]
        if provider_book_id != expected_book_id:
            raise SourceValidationError(
                f"Provider file {name!r} was reassigned: expected "
                f"{expected_book_id!r}, observed {provider_book_id!r}"
            )
    return expected


def _load_existing_booknames(
    books_dir: str, provider_file_ids: dict[str, str]
) -> list[dict[str, Any]]:
    path = os.path.join(books_dir, "BookNames.json")
    books = _read_json(path)
    if not isinstance(books, list) or not books:
        raise SourceValidationError("Existing BookNames.json must be a non-empty array")
    ids = []
    for index, book in enumerate(books):
        if not isinstance(book, dict) or not isinstance(book.get("bookId"), str):
            raise SourceValidationError(f"Existing BookNames.json entry {index} has no bookId")
        ids.append(book["bookId"])
    if len(ids) != len(set(ids)):
        raise SourceValidationError("Existing BookNames.json contains duplicate bookId values")
    if set(ids) != set(provider_file_ids):
        raise SourceValidationError(
            "Existing BookNames.json and numeric provider files have different bookId sets"
        )
    return books


def _fetch_json_payload(
    url: str,
    *,
    http_get: Callable[..., Any],
    timeout: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        response: Any | None = None
        try:
            response = http_get(
                url,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=timeout,
            )
            status_value = getattr(response, "status", None)
            if status_value is None:
                status_value = getattr(response, "status_code", 200)
            status = int(status_value)
            if status == 429 or status >= 500:
                raise _RetryableFetchError(f"HTTP {status} from {url}")
            if status >= 400:
                raise RefreshError(f"Non-retryable HTTP {status} from {url}")
            reader = getattr(response, "read", None)
            raw = reader() if callable(reader) else getattr(response, "content", None)
            if not isinstance(raw, bytes):
                raise SourceValidationError(f"Non-byte HTTP response from {url}")
            decoded = raw.decode("utf-8")
            data = json.loads(decoded)
            headers = getattr(response, "headers", {}) or {}
            return {
                "data": data,
                "raw_sha256": _sha256(raw),
                "etag": headers.get("ETag") or headers.get("etag") or "",
            }
        except SourceValidationError:
            raise
        except urllib.error.HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise RefreshError(
                    f"Non-retryable HTTP {error.code} from {url}"
                ) from error
            last_error = error
            if attempt + 1 < retries:
                time.sleep(backoff_seconds * (2**attempt))
        except (
            _RetryableFetchError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(backoff_seconds * (2**attempt))
        finally:
            closer = getattr(response, "close", None)
            if callable(closer):
                closer()
    raise RefreshError(
        f"Failed to fetch valid JSON from {url} after {retries} attempts: {last_error}"
    )


def _validate_live_manifest(
    payload: Any, provider_file_ids: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(payload, list) or not payload:
        raise SourceValidationError("The live allbooks response must be a non-empty array")
    by_id: dict[str, dict[str, Any]] = {}
    for index, book in enumerate(payload):
        if not isinstance(book, dict):
            raise SourceValidationError(f"Live allbooks entry {index} is not an object")
        provider_book_id = book.get("bookId")
        if not isinstance(provider_book_id, str) or not provider_book_id.strip():
            raise SourceValidationError(f"Live allbooks entry {index} has no nonblank bookId")
        if provider_book_id in by_id:
            raise SourceValidationError(f"Duplicate live manifest bookId: {provider_book_id!r}")
        minimum = _positive_int(book.get("idRangeMin"), f"{provider_book_id}.idRangeMin")
        maximum = _positive_int(book.get("idRangeMax"), f"{provider_book_id}.idRangeMax")
        if maximum < minimum:
            raise SourceValidationError(
                f"{provider_book_id} has an inverted manifest ID range {minimum}-{maximum}"
            )
        if maximum - minimum + 1 > MAX_MANIFEST_ID_SPAN:
            raise SourceValidationError(
                f"{provider_book_id} manifest ID range exceeds the safe "
                f"{MAX_MANIFEST_ID_SPAN:,}-record bound"
            )
        by_id[provider_book_id] = book

    unknown = sorted(set(by_id) - set(provider_file_ids))
    missing = sorted(set(provider_file_ids) - set(by_id))
    if unknown or missing:
        raise SourceValidationError(
            "Live manifest does not match the curated provider-file identity map; "
            f"unknown={unknown}, missing={missing}"
        )
    return payload, by_id


def validate_book_payload(requested_book_id: str, payload: Any) -> list[int]:
    """Validate one live book array without altering any source-owned fields."""
    if not isinstance(payload, list) or not payload:
        raise SourceValidationError(
            f"Live payload for {requested_book_id!r} must be a non-empty array"
        )
    if len(payload) > MAX_MANIFEST_ID_SPAN:
        raise SourceValidationError(
            f"Live payload for {requested_book_id!r} exceeds the safe "
            f"{MAX_MANIFEST_ID_SPAN:,}-record bound"
        )
    ids: list[int] = []
    observed: set[int] = set()
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise SourceValidationError(
                f"{requested_book_id} row {index} is not a JSON object"
            )
        if row.get("bookId") != requested_book_id:
            raise SourceValidationError(
                f"{requested_book_id} row {index} has mismatched bookId {row.get('bookId')!r}"
            )
        hadith_id = _positive_int(row.get("id"), f"{requested_book_id} row {index} id")
        if hadith_id in observed:
            raise SourceValidationError(
                f"Duplicate ({requested_book_id!r}, {hadith_id}) source identity"
            )
        observed.add(hadith_id)
        ids.append(hadith_id)
    return ids


def _merge_booknames(
    existing: list[dict[str, Any]], live_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Update values while retaining the checked-in list and field ordering."""
    merged_books: list[dict[str, Any]] = []
    for old in existing:
        live = live_by_id[old["bookId"]]
        merged = {key: live.get(key, value) for key, value in old.items()}
        for key, value in live.items():
            if key not in merged:
                merged[key] = value
        merged_books.append(merged)
    return merged_books


def _book_snapshot_entry(
    *,
    provider_book_id: str,
    provider_file_id: str,
    manifest_book: dict[str, Any],
    ids: list[int],
    url: str,
    source_payload_sha256: str,
    file_payload: bytes,
    etag: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    advertised_min = int(manifest_book["idRangeMin"])
    advertised_max = int(manifest_book["idRangeMax"])
    actual_min = min(ids)
    actual_max = max(ids)
    actual_ids = set(ids)
    missing_ids = [
        hadith_id
        for hadith_id in range(advertised_min, advertised_max + 1)
        if hadith_id not in actual_ids
    ]
    outside_ids = sorted(
        hadith_id
        for hadith_id in actual_ids
        if hadith_id < advertised_min or hadith_id > advertised_max
    )
    entry = {
        "provider_book_id": provider_book_id,
        "provider_file_id": provider_file_id,
        "url": url,
        "etag": etag,
        "source_payload_sha256": source_payload_sha256,
        "file_sha256": _sha256(file_payload),
        "actual_count": len(ids),
        "actual_id_range": {"min": actual_min, "max": actual_max},
        "advertised_id_range": {"min": advertised_min, "max": advertised_max},
        "advertised_count": advertised_max - advertised_min + 1,
        "missing_ids": missing_ids,
        "ids_outside_advertised_range": outside_ids,
    }
    if not missing_ids and not outside_ids:
        return entry, None
    inconsistency = {
        "kind": "manifest_payload_id_range_mismatch",
        "provider_book_id": provider_book_id,
        "provider_file_id": provider_file_id,
        "advertised_id_range": {"min": advertised_min, "max": advertised_max},
        "actual_id_range": {"min": actual_min, "max": actual_max},
        "missing_ids": missing_ids,
        "ids_outside_advertised_range": outside_ids,
    }
    return entry, inconsistency


def _transaction_key(books_dir: str) -> str:
    canonical = os.path.normcase(os.path.realpath(books_dir)).encode("utf-8")
    return _sha256(canonical)[:16]


@contextmanager
def _refresh_lock(books_dir: str):
    """Serialize refreshes for one destination using an OS advisory lock."""
    lock_path = os.path.join(
        tempfile.gettempdir(),
        f"islamicapps-thaqalayn-{_transaction_key(books_dir)}.lock",
    )
    try:
        handle = open(lock_path, "a+b")
    except OSError as error:
        raise RefreshError(f"Could not open refresh lock {lock_path}: {error}") from error

    locked = False
    unlock: Callable[[], None]
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

                def unlock() -> None:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                def unlock() -> None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

            locked = True
        except (ImportError, OSError) as error:
            raise RefreshError(
                f"Another refresh owns the lock for {books_dir}, or locking failed: {error}"
            ) from error
        yield
    finally:
        if locked:
            try:
                unlock()
            except OSError:
                pass
        handle.close()


def _durable_replace_json(path: str, value: Any) -> None:
    """Atomically replace one small transaction journal."""
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".transaction-", suffix=".tmp", dir=os.path.dirname(path)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def _read_transaction_journal(backup_dir: str, books_dir: str) -> dict[str, Any]:
    journal = _read_json(os.path.join(backup_dir, "transaction.json"))
    if not isinstance(journal, dict) or journal.get("schema_version") != 1:
        raise RefreshError(f"Invalid rollback journal in {backup_dir}")
    if journal.get("state") not in {"prepared", "committed"}:
        raise RefreshError(f"Unknown rollback state in {backup_dir}")
    if journal.get("books_dir") != os.path.normcase(os.path.realpath(books_dir)):
        raise RefreshError(f"Rollback journal destination mismatch in {backup_dir}")
    filenames = journal.get("filenames")
    existing = journal.get("existing")
    plain_filenames = (
        isinstance(filenames, list)
        and bool(filenames)
        and all(
            isinstance(name, str)
            and name
            and os.path.basename(name) == name
            and name not in {".", ".."}
            for name in filenames
        )
    )
    plain_existing = (
        isinstance(existing, list)
        and all(isinstance(name, str) for name in existing)
    )
    if (
        not plain_filenames
        or len(filenames) != len(set(filenames))
        or filenames[-1] != SNAPSHOT_MANIFEST_NAME
        or not plain_existing
        or len(existing) != len(set(existing))
        or not all(name in filenames for name in existing)
    ):
        raise RefreshError(f"Invalid rollback target list in {backup_dir}")
    return journal


def _restore_transaction(
    backup_dir: str, books_dir: str, journal: dict[str, Any]
) -> list[str]:
    """Restore an interrupted publication without consuming its backups."""
    existing = set(journal["existing"])
    errors: list[str] = []
    for filename in reversed(journal["filenames"]):
        target = os.path.join(books_dir, filename)
        try:
            if filename in existing:
                backup = os.path.join(backup_dir, "backups", filename)
                if not os.path.isfile(backup):
                    raise OSError(f"missing durable backup {backup}")
                descriptor, restore_path = tempfile.mkstemp(
                    prefix=".thaqalayn-restore-", dir=books_dir
                )
                os.close(descriptor)
                try:
                    shutil.copy2(backup, restore_path)
                    # Windows cannot flush a read-only descriptor with os.fsync.
                    with open(restore_path, "r+b") as handle:
                        os.fsync(handle.fileno())
                    os.replace(restore_path, target)
                finally:
                    if os.path.exists(restore_path):
                        os.remove(restore_path)
            elif os.path.exists(target):
                os.remove(target)
        except BaseException as error:
            errors.append(f"{filename}: {error}")
    return errors


def _recover_interrupted_publications(books_dir: str) -> None:
    """Recover or clean durable journals left by an interrupted process."""
    parent_dir = os.path.dirname(books_dir)
    key = _transaction_key(books_dir)
    preparing_prefix = f".thaqalayn-preparing-{key}-"
    rollback_prefix = f".thaqalayn-rollback-{key}-"
    try:
        names = os.listdir(parent_dir)
    except OSError as error:
        raise RefreshError(f"Could not inspect refresh transactions: {error}") from error

    for name in sorted(names):
        path = os.path.join(parent_dir, name)
        if name.startswith(preparing_prefix) and os.path.isdir(path):
            shutil.rmtree(path)
        elif name.startswith(rollback_prefix) and os.path.isdir(path):
            journal = _read_transaction_journal(path, books_dir)
            if journal["state"] == "prepared":
                errors = _restore_transaction(path, books_dir, journal)
                if errors:
                    raise RefreshError(
                        f"Interrupted refresh rollback remains in {path}: "
                        + "; ".join(errors)
                    )
            shutil.rmtree(path)


def _publish_staged_files(
    stage_dir: str, books_dir: str, filenames: list[str]
) -> None:
    """Replace staged files with a durable journal; publish the manifest last."""
    if not filenames or filenames[-1] != SNAPSHOT_MANIFEST_NAME:
        raise ValueError("snapshot_manifest.json must be the final publication target")
    if len(filenames) != len(set(filenames)) or any(
        os.path.basename(filename) != filename for filename in filenames
    ):
        raise ValueError("Publication targets must be unique plain filenames")
    for filename in filenames:
        if not os.path.isfile(os.path.join(stage_dir, filename)):
            raise RefreshError(f"Missing staged publication target: {filename}")

    parent_dir = os.path.dirname(books_dir)
    key = _transaction_key(books_dir)
    preparing_dir = tempfile.mkdtemp(
        prefix=f".thaqalayn-preparing-{key}-", dir=parent_dir
    )
    active_dir: str | None = None
    try:
        backups_dir = os.path.join(preparing_dir, "backups")
        os.makedirs(backups_dir)
        existing = [
            filename
            for filename in filenames
            if os.path.exists(os.path.join(books_dir, filename))
        ]
        for filename in existing:
            backup = os.path.join(backups_dir, filename)
            shutil.copy2(os.path.join(books_dir, filename), backup)
            # Windows cannot flush a read-only descriptor with os.fsync.
            with open(backup, "r+b") as handle:
                os.fsync(handle.fileno())

        journal = {
            "schema_version": 1,
            "state": "prepared",
            "books_dir": os.path.normcase(os.path.realpath(books_dir)),
            "filenames": filenames,
            "existing": existing,
        }
        _durable_replace_json(
            os.path.join(preparing_dir, "transaction.json"), journal
        )
        active_dir = os.path.join(
            parent_dir,
            f".thaqalayn-rollback-{key}-{os.getpid()}-{time.time_ns()}",
        )
        os.replace(preparing_dir, active_dir)
        preparing_dir = ""

        try:
            for filename in filenames:
                os.replace(
                    os.path.join(stage_dir, filename),
                    os.path.join(books_dir, filename),
                )
            journal["state"] = "committed"
            _durable_replace_json(
                os.path.join(active_dir, "transaction.json"), journal
            )
        except BaseException as original_error:
            errors = _restore_transaction(active_dir, books_dir, journal)
            if errors:
                raise RefreshError(
                    f"Publication failed and rollback is incomplete; durable "
                    f"backups remain in {active_dir}: " + "; ".join(errors)
                ) from original_error
            shutil.rmtree(active_dir)
            active_dir = None
            raise

        try:
            shutil.rmtree(active_dir)
            active_dir = None
        except OSError:
            # The committed journal is safe for the next refresh to clean.
            pass
    finally:
        if preparing_dir and os.path.isdir(preparing_dir):
            shutil.rmtree(preparing_dir, ignore_errors=True)


def _refresh_snapshot_locked(
    books_dir: str = BOOKS_DIR,
    *,
    api_base_url: str = API_BASE_URL,
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    http_get: Callable[..., Any] = _stdlib_http_get,
    fetched_at: str | None = None,
    curated_provider_files: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fetch, validate, stage, and publish a complete live V2 snapshot."""
    if max_workers < 2 or max_workers > 4:
        raise ValueError("max_workers must be between 2 and 4")
    if timeout <= 0 or retries <= 0 or backoff_seconds < 0:
        raise ValueError("timeout/retries must be positive and backoff_seconds non-negative")

    books_dir = os.path.abspath(books_dir)
    provider_file_ids = load_provider_file_map(books_dir, curated_provider_files)
    existing_booknames = _load_existing_booknames(books_dir, provider_file_ids)
    base_url = api_base_url.rstrip("/")
    manifest_url = f"{base_url}/allbooks"
    live_response = _fetch_json_payload(
        manifest_url,
        http_get=http_get,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    live_books, live_by_id = _validate_live_manifest(
        live_response["data"], provider_file_ids
    )
    merged_booknames = _merge_booknames(existing_booknames, live_by_id)

    parent_dir = os.path.dirname(books_dir)
    os.makedirs(books_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".thaqalayn-refresh-", dir=parent_dir) as stage_dir:
        booknames_payload = _json_bytes(merged_booknames)
        _write_staged(os.path.join(stage_dir, "BookNames.json"), booknames_payload)

        def fetch_and_stage(provider_book_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
            provider_file_id = provider_file_ids[provider_book_id]
            url = f"{base_url}/{provider_book_id}"
            response = _fetch_json_payload(
                url,
                http_get=http_get,
                timeout=timeout,
                retries=retries,
                backoff_seconds=backoff_seconds,
            )
            ids = validate_book_payload(provider_book_id, response["data"])
            file_payload = _json_bytes(response["data"])
            _write_staged(
                os.path.join(stage_dir, f"{provider_file_id}.json"), file_payload
            )
            return _book_snapshot_entry(
                provider_book_id=provider_book_id,
                provider_file_id=provider_file_id,
                manifest_book=live_by_id[provider_book_id],
                ids=ids,
                url=url,
                source_payload_sha256=response["raw_sha256"],
                file_payload=file_payload,
                etag=response["etag"],
            )

        entries: list[dict[str, Any]] = []
        inconsistencies: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_and_stage, provider_book_id): provider_book_id
                for provider_book_id in provider_file_ids
            }
            for future in as_completed(futures):
                entry, inconsistency = future.result()
                entries.append(entry)
                if inconsistency is not None:
                    inconsistencies.append(inconsistency)

        entries.sort(key=lambda entry: int(entry["provider_file_id"]))
        inconsistencies.sort(key=lambda item: int(item["provider_file_id"]))
        timestamp = fetched_at or datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        advertised_total = sum(entry["advertised_count"] for entry in entries)
        actual_total = sum(entry["actual_count"] for entry in entries)
        snapshot_manifest = {
            "schema_version": 1,
            "source": "Thaqalayn API V2 live REST",
            "fetched_at": timestamp,
            "api_base_url": base_url,
            "user_agent": USER_AGENT,
            "identity_mapping": (
                "Exact provider_book_id mapped to the existing checked-in numeric "
                "provider_file_id; URL, order, and title are never identity inputs."
            ),
            "manifest": {
                "url": manifest_url,
                "etag": live_response["etag"],
                "source_payload_sha256": live_response["raw_sha256"],
                "file_sha256": _sha256(booknames_payload),
                "book_count": len(live_books),
                "advertised_record_count": advertised_total,
            },
            "actual_record_count": actual_total,
            "books": entries,
            "upstream_inconsistencies": inconsistencies,
        }
        _write_staged(
            os.path.join(stage_dir, SNAPSHOT_MANIFEST_NAME),
            _json_bytes(snapshot_manifest),
        )

        filenames = [
            f"{entry['provider_file_id']}.json" for entry in entries
        ] + ["BookNames.json", SNAPSHOT_MANIFEST_NAME]
        _publish_staged_files(stage_dir, books_dir, filenames)

    return snapshot_manifest


def refresh_snapshot(
    books_dir: str = BOOKS_DIR,
    *,
    api_base_url: str = API_BASE_URL,
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    http_get: Callable[..., Any] = _stdlib_http_get,
    fetched_at: str | None = None,
    curated_provider_files: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Serialize, recover, then refresh one complete live V2 snapshot."""
    books_dir = os.path.abspath(books_dir)
    with _refresh_lock(books_dir):
        _recover_interrupted_publications(books_dir)
        return _refresh_snapshot_locked(
            books_dir,
            api_base_url=api_base_url,
            max_workers=max_workers,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
            http_get=http_get,
            fetched_at=fetched_at,
            curated_provider_files=curated_provider_files,
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books-dir", default=BOOKS_DIR)
    parser.add_argument("--api-base-url", default=API_BASE_URL)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = refresh_snapshot(
            args.books_dir,
            api_base_url=args.api_base_url,
            max_workers=args.max_workers,
            timeout=args.timeout,
            retries=args.retries,
            backoff_seconds=args.backoff_seconds,
        )
    except (RefreshError, ValueError, OSError) as error:
        print(f"Thaqalayn refresh failed without publishing: {error}", file=sys.stderr)
        return 1

    print(
        "Thaqalayn refresh published: "
        f"{len(manifest['books'])} provider books, "
        f"{manifest['actual_record_count']:,} actual rows, "
        f"{len(manifest['upstream_inconsistencies'])} upstream inconsistencies."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
