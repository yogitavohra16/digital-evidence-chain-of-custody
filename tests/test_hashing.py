"""Tests for SHA-256 evidence hashing (Formula 1)."""
import hashlib
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from evidence.hashing import calculate_sha256_from_chunks, calculate_sha256_of_bytes, calculate_sha256_of_path


class HashingTests(SimpleTestCase):
    """SHA-256 must be correct, repeatable and sensitive to change."""

    def test_known_sha256_value(self):
        """The SHA-256 of b'abc' is a well-known published test vector."""
        expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        self.assertEqual(calculate_sha256_of_bytes(b"abc"), expected)

    def test_identical_files_have_same_hash(self):
        """Two files with identical bytes produce identical hashes."""
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder, "a.txt"), Path(folder, "b.txt")
            first.write_bytes(b"same content"); second.write_bytes(b"same content")
            self.assertEqual(calculate_sha256_of_path(first), calculate_sha256_of_path(second))

    def test_modified_file_has_different_hash(self):
        """Changing one byte changes the hash completely."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "a.txt")
            path.write_bytes(b"original content")
            original = calculate_sha256_of_path(path)
            path.write_bytes(b"original contenT")
            self.assertNotEqual(original, calculate_sha256_of_path(path))

    def test_chunked_hash_equals_whole_file_hash(self):
        """Reading in small chunks gives the same result as hashing everything at once."""
        data = b"0123456789" * 1000
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "big.bin")
            path.write_bytes(data)
            self.assertEqual(calculate_sha256_of_path(path, chunk_size=7), hashlib.sha256(data).hexdigest())
        chunks = [data[index:index + 13] for index in range(0, len(data), 13)]
        self.assertEqual(calculate_sha256_from_chunks(chunks), hashlib.sha256(data).hexdigest())
