"""services.py - evidence integrity verification.

FORMULA 5 - EVIDENCE INTEGRITY VERIFICATION
    VerificationResult =
        MATCH      if OriginalHash == CurrentHash
        MISMATCH   if OriginalHash != CurrentHash
    plus explicit states FILE_MISSING and ERROR when the hash cannot be calculated.

RULES
    * The ORIGINAL hash stored on the Evidence row is never changed here.
    * A MISMATCH means the file content differs from the registered version. It does
      not by itself prove malicious tampering (it could be corruption, an accidental
      edit, a restore from the wrong backup ...). It means: investigate.
"""
from evidence.hashing import calculate_sha256_of_path

from .models import VerificationRecord


def verify_evidence(evidence, user):
    """Re-hash the stored file, compare with the original hash, save a history row.

    Inputs:  evidence - the Evidence to verify; user - who is running the check.
    Returns: the saved VerificationRecord.
    """
    current_hash = ""
    error_details = ""

    try:
        # Step 1: locate the stored file. `.path` is built by Django from the stored
        # relative name inside the private folder; we never use user-typed paths.
        file_path = evidence.stored_file.path

        # Step 2: calculate the CURRENT hash from the file's bytes, in chunks.
        current_hash = calculate_sha256_of_path(file_path)

        # Step 3: compare with the ORIGINAL hash (which we never modify).
        if current_hash == evidence.sha256_hash:
            result = VerificationRecord.Result.MATCH
        else:
            result = VerificationRecord.Result.MISMATCH
            error_details = (
                "The current file content differs from the registered version. "
                "This does not by itself prove malicious tampering."
            )
    except FileNotFoundError:
        result = VerificationRecord.Result.FILE_MISSING
        error_details = "The registered evidence file could not be found in storage."
    except (OSError, ValueError) as error:
        result = VerificationRecord.Result.ERROR
        error_details = f"The file could not be read: {error}"

    return VerificationRecord.objects.create(
        evidence=evidence,
        verified_by=user,
        original_hash=evidence.sha256_hash,
        current_hash=current_hash,
        result=result,
        error_details=error_details,
    )
