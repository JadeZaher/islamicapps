"""Offline contract tests for the Thaqalayn live REST snapshot refresher."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "shia-hadith"
    / "download_thaqalayn.py"
)
MODULE_NAME = "download_thaqalayn_test"
SPEC = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
download = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[MODULE_NAME] = download
SPEC.loader.exec_module(download)


KNOWN_BOOK = "Al-Kafi-Volume-1-Kulayni"
NUMANI_BOOK = "Kitab-al-Ghayba-Numani"
KNOWN_MAPPING = {KNOWN_BOOK: "1"}
NUMANI_MAPPING = {NUMANI_BOOK: "22"}


def api_url(fragment):
    return f"{download.API_BASE_URL.rstrip('/')}/{fragment.lstrip('/')}"


def book_metadata(book_id, minimum=1, maximum=1):
    return {
        "bookId": book_id,
        "BookName": "Test work",
        "idRangeMin": minimum,
        "idRangeMax": maximum,
        "volume": 1,
    }


def hadith(book_id, hadith_id, **updates):
    row = {
        "id": hadith_id,
        "bookId": book_id,
        "book": "Test work",
        "volume": 1,
        "arabicText": f"Arabic source {hadith_id}",
        "englishText": f"English translation {hadith_id}",
    }
    row.update(updates)
    return row


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def seed_snapshot(books_dir, provider_file_id, metadata, rows):
    books_dir.mkdir(parents=True, exist_ok=True)
    write_json(books_dir / "BookNames.json", [metadata])
    write_json(books_dir / f"{provider_file_id}.json", rows)
    write_json(
        books_dir / "snapshot_manifest.json",
        {"fetched_at": "old", "record_count": len(rows)},
    )


class FakeResponse:
    def __init__(self, payload, *, status_code=200, headers=None):
        self.content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.status_code = status_code
        self.headers = headers or {"ETag": '"offline-fixture"'}

    @property
    def text(self):
        return self.content.decode("utf-8")

    def json(self):
        return json.loads(self.content.decode("utf-8"))

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"fixture HTTP status {self.status_code}")


class FakeHttpGet:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "headers": dict(headers or {}), "timeout": timeout}
        )
        if url not in self.routes:
            raise AssertionError(f"unexpected HTTP request: {url}")
        return FakeResponse(self.routes[url])


class SnapshotRefreshTests(unittest.TestCase):
    def test_success_stages_complete_snapshot_and_commits_manifest_last(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books_dir = root / "v2_books"
            seed_snapshot(
                books_dir,
                "1",
                {**book_metadata(KNOWN_BOOK), "translator": ""},
                [hadith(KNOWN_BOOK, 1, englishText="stale translation")],
            )
            live_metadata = {
                **book_metadata(KNOWN_BOOK, maximum=2),
                "translator": "Named source translator",
            }
            live_rows = [hadith(KNOWN_BOOK, 1), hadith(KNOWN_BOOK, 2)]
            http_get = FakeHttpGet(
                {
                    api_url("allbooks"): [live_metadata],
                    api_url(KNOWN_BOOK): live_rows,
                }
            )
            real_replace = download.os.replace
            replaced_targets = []

            def tracking_replace(source, target):
                replaced_targets.append(Path(target))
                return real_replace(source, target)

            with mock.patch.object(
                download.os, "replace", side_effect=tracking_replace
            ):
                returned_manifest = download.refresh_snapshot(
                    books_dir=books_dir,
                    max_workers=2,
                    timeout=1.0,
                    retries=1,
                    backoff_seconds=0.0,
                    http_get=http_get,
                    fetched_at="2026-07-21T12:00:00Z",
                    curated_provider_files=KNOWN_MAPPING,
                )

            self.assertEqual(
                json.loads((books_dir / "BookNames.json").read_text("utf-8")),
                [live_metadata],
            )
            self.assertEqual(
                json.loads((books_dir / "1.json").read_text("utf-8")),
                live_rows,
            )
            rendered_book = (books_dir / "1.json").read_text("utf-8")
            self.assertTrue(rendered_book.startswith("[\n\t{"))
            self.assertFalse(rendered_book.endswith("\n"))
            disk_manifest = json.loads(
                (books_dir / "snapshot_manifest.json").read_text("utf-8")
            )
            self.assertEqual(returned_manifest, disk_manifest)
            self.assertEqual(disk_manifest["actual_record_count"], 2)
            self.assertEqual(disk_manifest["manifest"]["book_count"], 1)

            canonical_targets = [
                path.name
                for path in replaced_targets
                if path.parent.resolve() == books_dir.resolve()
            ]
            self.assertEqual(canonical_targets[-1], "snapshot_manifest.json")
            self.assertEqual(
                set(canonical_targets),
                {"BookNames.json", "1.json", "snapshot_manifest.json"},
            )
            self.assertEqual(
                {call["url"] for call in http_get.calls},
                {api_url("allbooks"), api_url(KNOWN_BOOK)},
            )
            self.assertEqual([path.name for path in root.iterdir()], ["v2_books"])

    def test_unknown_provider_book_fails_closed_without_replacing_snapshot(self):
        unknown_book = "Previously-Unmapped-Provider-Book"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books_dir = root / "v2_books"
            seed_snapshot(
                books_dir,
                "1",
                book_metadata(KNOWN_BOOK),
                [hadith(KNOWN_BOOK, 1)],
            )
            before = {
                path.name: path.read_bytes()
                for path in books_dir.iterdir()
                if path.is_file()
            }
            http_get = FakeHttpGet(
                {
                    api_url("allbooks"): [
                        book_metadata(KNOWN_BOOK),
                        book_metadata(unknown_book),
                    ],
                    api_url(KNOWN_BOOK): [hadith(KNOWN_BOOK, 1)],
                    api_url(unknown_book): [hadith(unknown_book, 1)],
                }
            )

            with self.assertRaisesRegex(
                download.SourceValidationError, "(?i)unknown|unmapped"
            ):
                download.refresh_snapshot(
                    books_dir=books_dir,
                    max_workers=2,
                    timeout=1.0,
                    retries=1,
                    backoff_seconds=0.0,
                    http_get=http_get,
                    fetched_at="2026-07-21T12:00:00Z",
                    curated_provider_files=KNOWN_MAPPING,
                )

            after = {
                path.name: path.read_bytes()
                for path in books_dir.iterdir()
                if path.is_file()
            }
            self.assertEqual(after, before)
            self.assertEqual([path.name for path in root.iterdir()], ["v2_books"])

    def test_publication_failure_rolls_back_every_canonical_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books_dir = root / "v2_books"
            seed_snapshot(
                books_dir,
                "1",
                book_metadata(KNOWN_BOOK),
                [hadith(KNOWN_BOOK, 1, englishText="old")],
            )
            before = {
                path.name: path.read_bytes()
                for path in books_dir.iterdir()
                if path.is_file()
            }
            live_metadata = book_metadata(KNOWN_BOOK, maximum=2)
            http_get = FakeHttpGet(
                {
                    api_url("allbooks"): [live_metadata],
                    api_url(KNOWN_BOOK): [
                        hadith(KNOWN_BOOK, 1),
                        hadith(KNOWN_BOOK, 2),
                    ],
                }
            )
            real_replace = download.os.replace
            failed = False

            def fail_once_during_publication(source, target):
                nonlocal failed
                source_path = Path(source)
                target_path = Path(target)
                if (
                    not failed
                    and source_path.parent.name.startswith(".thaqalayn-refresh-")
                    and target_path == books_dir / "BookNames.json"
                ):
                    failed = True
                    raise OSError("injected canonical replacement failure")
                return real_replace(source, target)

            with mock.patch.object(
                download.os, "replace", side_effect=fail_once_during_publication
            ):
                with self.assertRaisesRegex(OSError, "injected"):
                    download.refresh_snapshot(
                        books_dir=books_dir,
                        max_workers=2,
                        timeout=1.0,
                        retries=1,
                        backoff_seconds=0.0,
                        http_get=http_get,
                        fetched_at="2026-07-21T12:00:00Z",
                        curated_provider_files=KNOWN_MAPPING,
                    )

            after = {
                path.name: path.read_bytes()
                for path in books_dir.iterdir()
                if path.is_file()
            }
            self.assertTrue(failed)
            self.assertEqual(after, before)
            self.assertEqual([path.name for path in root.iterdir()], ["v2_books"])


class PayloadValidationTests(unittest.TestCase):
    def test_curated_file_identity_rejects_a_reassigned_numeric_file(self):
        with tempfile.TemporaryDirectory() as directory:
            books_dir = Path(directory) / "v2_books"
            seed_snapshot(
                books_dir,
                "1",
                book_metadata(NUMANI_BOOK),
                [hadith(NUMANI_BOOK, 1)],
            )

            with self.assertRaisesRegex(
                download.SourceValidationError, "(?i)reassigned"
            ):
                download.load_provider_file_map(books_dir, KNOWN_MAPPING)

    def test_duplicate_upstream_ids_are_rejected(self):
        payload = [hadith(KNOWN_BOOK, 1), hadith(KNOWN_BOOK, 1)]

        with self.assertRaisesRegex(
            download.SourceValidationError, "(?i)duplicate.*1"
        ):
            download.validate_book_payload(KNOWN_BOOK, payload)

    def test_mismatched_provider_book_id_is_rejected(self):
        payload = [hadith("Different-Book", 1)]

        with self.assertRaisesRegex(
            download.SourceValidationError,
            "(?i)(mismatch.*book.?id|book.?id.*mismatch)",
        ):
            download.validate_book_payload(KNOWN_BOOK, payload)


class ManifestDiscrepancyTests(unittest.TestCase):
    def test_advertised_ghost_id_is_reported_without_synthesizing_a_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            books_dir = root / "v2_books"
            seed_snapshot(
                books_dir,
                "22",
                book_metadata(NUMANI_BOOK, minimum=468, maximum=468),
                [hadith(NUMANI_BOOK, 468)],
            )
            advertised = book_metadata(NUMANI_BOOK, minimum=468, maximum=469)
            live_rows = [hadith(NUMANI_BOOK, 468)]
            http_get = FakeHttpGet(
                {
                    api_url("allbooks"): [advertised],
                    api_url(NUMANI_BOOK): live_rows,
                }
            )

            returned_manifest = download.refresh_snapshot(
                books_dir=books_dir,
                max_workers=2,
                timeout=1.0,
                retries=1,
                backoff_seconds=0.0,
                http_get=http_get,
                fetched_at="2026-07-21T12:00:00Z",
                curated_provider_files=NUMANI_MAPPING,
            )

            published_rows = json.loads(
                (books_dir / "22.json").read_text(encoding="utf-8")
            )
            self.assertEqual(published_rows, live_rows)
            self.assertEqual([row["id"] for row in published_rows], [468])

            disk_manifest = json.loads(
                (books_dir / "snapshot_manifest.json").read_text("utf-8")
            )
            self.assertEqual(returned_manifest, disk_manifest)
            self.assertEqual(disk_manifest["actual_record_count"], 1)
            self.assertEqual(
                disk_manifest["books"][0]["provider_book_id"], NUMANI_BOOK
            )
            self.assertEqual(disk_manifest["books"][0]["provider_file_id"], "22")
            self.assertEqual(disk_manifest["books"][0]["actual_count"], 1)
            inconsistencies = disk_manifest["upstream_inconsistencies"]
            self.assertEqual(len(inconsistencies), 1)
            inconsistency = inconsistencies[0]
            self.assertEqual(inconsistency["provider_book_id"], NUMANI_BOOK)
            self.assertEqual(inconsistency["provider_file_id"], "22")
            self.assertEqual(
                inconsistency["advertised_id_range"], {"min": 468, "max": 469}
            )
            self.assertEqual(
                inconsistency["actual_id_range"], {"min": 468, "max": 468}
            )
            self.assertEqual(inconsistency["missing_ids"], [469])


if __name__ == "__main__":
    unittest.main()
