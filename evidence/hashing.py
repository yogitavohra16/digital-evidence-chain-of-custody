"""hashing.py - calculating SHA-256 fingerprints of evidence files.

FORMULA 1 - SHA-256 EVIDENCE HASH
    Let F be the complete byte content of an evidence file.
        H_evidence = SHA256(F)
    In Python:  hashlib.sha256(file_bytes).hexdigest()

PURPOSE
    The hash is a fingerprint of the file's contents. If the file changes later, even
    by one byte, a new hash will differ from the original one, so we can detect it.

IMPORTANT
    A hash proves the file CONTENT is the same as when it was registered. It does not
    prove who created the file, where it came from, or that it is authentic.
"""
import hashlib

from django.conf import settings


def calculate_sha256_from_chunks(chunks):
    """Calculate SHA-256 from an iterable of byte chunks.

    Input:  chunks - any iterable that yields `bytes` objects (e.g. Django's
            UploadedFile.chunks()).
    Returns: the 64-character hexadecimal digest (str).
    """
    # Step 1: Create an empty SHA-256 object. Think of it as a calculator that has
    # not seen any data yet.
    hasher = hashlib.sha256()

    # Step 2: Feed it the file one chunk at a time.
    # SHA-256 produces ONE final digest for the complete sequence of bytes, whether we
    # give it in one piece or in many small pieces, so chunking never changes the result.
    for chunk in chunks:
        hasher.update(chunk)

    # Step 3: Return the hexadecimal digest.
    # We store this value so we can compare it with a future hash.
    return hasher.hexdigest()


def calculate_sha256_of_path(file_path, chunk_size=None):
    """Hash a file on disk by reading it in fixed-size chunks.

    Why chunks: a 5 GB disk image would not fit comfortably in memory. Reading 1 MiB
    at a time keeps memory use small no matter how large the file is.

    Inputs:  file_path - path of the file; chunk_size - bytes per read (optional).
    Returns: the hexadecimal SHA-256 digest.
    Raises:  FileNotFoundError / OSError if the file cannot be opened or read
             (callers decide how to report that).
    """
    chunk_size = chunk_size or settings.HASH_CHUNK_SIZE

    def read_chunks(file_object):
        # Keep reading until read() returns an empty bytes object (end of file).
        while True:
            chunk = file_object.read(chunk_size)
            if not chunk:
                return
            yield chunk

    with open(file_path, "rb") as file_object:
        return calculate_sha256_from_chunks(read_chunks(file_object))


def calculate_sha256_of_bytes(data):
    """Hash bytes that are already in memory (used for small samples and tests)."""
    return hashlib.sha256(data).hexdigest()
