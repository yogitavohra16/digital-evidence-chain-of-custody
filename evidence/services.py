"""services.py - the business logic for cases, evidence and custody events.

Views stay short because the real work is here. Everything that must succeed or fail
TOGETHER (saving the evidence row, the first custody event and its block) runs inside
`transaction.atomic()`: if any step raises an error, the database rolls back to the
state before the transaction began.
"""
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from blockchain.services import append_custody_event_block, require_valid_ledger

from .hashing import calculate_sha256_from_chunks, calculate_sha256_of_path
from .models import Case, CustodyEvent, Evidence

# Which evidence status each action produces. ACCESSED is missing on purpose:
# viewing evidence does not change where it is in the workflow.
STATUS_AFTER_ACTION = {
    CustodyEvent.ActionType.REGISTERED: Evidence.Status.REGISTERED,
    CustodyEvent.ActionType.TRANSFERRED: Evidence.Status.TRANSFERRED,
    CustodyEvent.ActionType.ANALYSIS_STARTED: Evidence.Status.IN_ANALYSIS,
    CustodyEvent.ActionType.ANALYSIS_COMPLETED: Evidence.Status.ANALYSIS_COMPLETED,
    CustodyEvent.ActionType.RETURNED: Evidence.Status.RETURNED,
    CustodyEvent.ActionType.ARCHIVED: Evidence.Status.ARCHIVED,
}


def _next_code(model, field_name, prefix):
    """Work out the next code like 'EV-0007' from the highest existing one.

    Inputs: the model, the unique code field, and the prefix ('EV' or 'CASE').
    Returns: the next unused code as text.
    The unique constraint in the database is the real protection against duplicates;
    callers retry if two requests ever pick the same number at once.
    """
    highest = 0
    for code in model.objects.values_list(field_name, flat=True):
        try:
            highest = max(highest, int(code.split("-")[-1]))
        except ValueError:
            continue
    return f"{prefix}-{highest + 1:04d}"


def create_case(*, title, description, status, user):
    """Create a case with an auto-generated unique Case ID (CASE-0001, CASE-0002 ...)."""
    for _attempt in range(5):
        try:
            with transaction.atomic():
                return Case.objects.create(
                    case_id=_next_code(Case, "case_id", "CASE"),
                    title=title,
                    description=description,
                    status=status,
                    created_by=user,
                )
        except IntegrityError:
            continue  # someone else took that number; pick the next one
    raise ValidationError("Could not generate a unique Case ID. Please try again.")


def register_evidence(*, case, uploaded_file, notes, user, handler_name):
    """Register an uploaded evidence file.

    Inputs:
        case          - the Case the evidence belongs to
        uploaded_file - Django UploadedFile (already validated by the form)
        notes         - free-text description
        user          - the logged-in user
        handler_name  - name of the person registering/collecting the evidence
    Returns: the new Evidence object.

    Steps (all inside one transaction):
      1. Check the ledger is healthy (we never extend a damaged chain).
      2. Hash the uploaded bytes in chunks.
      3. Save the evidence row (Django stores the file under a random safe name).
      4. Re-hash the SAVED copy to prove it was stored without change.
      5. Create the first custody event and its blockchain block.
    If anything fails, the database is rolled back and the stored file is deleted.
    """
    require_valid_ledger()

    # Step 2: hash the actual file bytes, chunk by chunk.
    sha256_hash = calculate_sha256_from_chunks(uploaded_file.chunks())
    original_name = Path(uploaded_file.name).name
    extension = Path(original_name).suffix.lower().lstrip(".")

    evidence = None
    try:
        for _attempt in range(5):
            try:
                with transaction.atomic():
                    evidence = Evidence(
                        evidence_id=_next_code(Evidence, "evidence_id", "EV"),
                        case=case,
                        original_filename=original_name[:255],
                        file_extension=extension,
                        file_size=uploaded_file.size,
                        sha256_hash=sha256_hash,
                        registered_by=user,
                        notes=notes,
                        status=Evidence.Status.REGISTERED,
                    )
                    # Step 3: saving the model also saves the file to private storage.
                    uploaded_file.seek(0)
                    evidence.stored_file.save(uploaded_file.name, uploaded_file, save=False)
                    evidence.save()

                    # Step 4: confirm the stored copy hashes to the same value.
                    stored_hash = calculate_sha256_of_path(evidence.stored_file.path)
                    if stored_hash != sha256_hash:
                        raise ValidationError("The stored copy does not match the uploaded file.")

                    # Step 5: first custody event + block.
                    _create_event_and_block(
                        evidence=evidence,
                        action_type=CustodyEvent.ActionType.REGISTERED,
                        user=user,
                        handler_name=handler_name,
                        remarks=notes or "Evidence registered in the system.",
                    )
                    return evidence
            except IntegrityError:
                _delete_stored_file(evidence)
                continue
        raise ValidationError("Could not generate a unique Evidence ID. Please try again.")
    except Exception:
        _delete_stored_file(evidence)
        raise


def _delete_stored_file(evidence):
    """Remove a stored file after a failed registration (database was rolled back)."""
    if evidence is not None and evidence.stored_file:
        try:
            evidence.stored_file.storage.delete(evidence.stored_file.name)
        except OSError:
            pass


def validate_custody_event(*, evidence, action_type, handler_name, from_party, to_party, remarks):
    """Check the rules for a new custody event. Raises ValidationError if broken.

    Why: bad events (a transfer with no receiver, work on archived evidence) would
    make the chain of custody meaningless. The same rules are enforced in the form
    AND here, so no code path can skip them.
    """
    problems = []
    A = CustodyEvent.ActionType

    if action_type == A.REGISTERED:
        problems.append("The registration event is created automatically; choose another action.")
    if not handler_name.strip():
        problems.append("Handler name is required.")
    if not remarks.strip():
        problems.append("Purpose / remarks are required.")
    if evidence.status == Evidence.Status.ARCHIVED:
        problems.append("This evidence is archived; no further custody events can be recorded.")
    if action_type == A.TRANSFERRED:
        if not from_party.strip() or not to_party.strip():
            problems.append("A transfer needs both 'From' and 'To'.")
        elif from_party.strip().lower() == to_party.strip().lower():
            problems.append("'From' and 'To' must be different people for a transfer.")
    if action_type == A.RETURNED and not to_party.strip():
        problems.append("A return needs the 'To' field (who receives the evidence).")
    if action_type == A.ANALYSIS_STARTED and evidence.status == Evidence.Status.IN_ANALYSIS:
        problems.append("Analysis has already started for this evidence.")
    if action_type == A.ANALYSIS_COMPLETED and evidence.status != Evidence.Status.IN_ANALYSIS:
        problems.append("Analysis can only be completed after it has been started.")

    if problems:
        raise ValidationError(problems)


def _create_event_and_block(*, evidence, action_type, user, handler_name,
                            from_party="", to_party="", remarks=""):
    """Save a CustodyEvent, update the evidence status and append the block.

    MUST be called inside transaction.atomic(). If appending the block fails, the
    exception propagates and the event is rolled back with it.
    """
    event = CustodyEvent.objects.create(
        evidence=evidence,
        action_type=action_type,
        recorded_by=user,
        handler_name=handler_name.strip(),
        from_party=from_party.strip(),
        to_party=to_party.strip(),
        remarks=remarks.strip(),
        evidence_hash=evidence.sha256_hash,  # copy of the ORIGINAL hash
    )
    new_status = STATUS_AFTER_ACTION.get(action_type)
    if new_status and evidence.status != new_status:
        evidence.status = new_status
        evidence.save(update_fields=["status"])
    append_custody_event_block(event)
    return event


def add_custody_event(*, evidence, action_type, user, handler_name,
                      from_party="", to_party="", remarks=""):
    """Validate and record a custody event, creating its blockchain block.

    Returns: the saved CustodyEvent.
    Raises:  ValidationError for rule violations; LedgerInvalidError if the existing
             ledger fails validation (nothing is saved in that case).
    """
    require_valid_ledger()
    with transaction.atomic():
        # Re-read the evidence inside the transaction so the rules below are checked
        # against its CURRENT status (not a stale copy from the web form).
        evidence = Evidence.objects.get(pk=evidence.pk)
        validate_custody_event(
            evidence=evidence, action_type=action_type, handler_name=handler_name,
            from_party=from_party, to_party=to_party, remarks=remarks,
        )
        return _create_event_and_block(
            evidence=evidence, action_type=action_type, user=user,
            handler_name=handler_name, from_party=from_party,
            to_party=to_party, remarks=remarks,
        )
