"""demo.py - a SAFE tamper-detection demonstration.

This builds a small SYNTHETIC chain entirely in memory (it uses no database rows and
no real evidence), tampers with a COPY, and validates both. Nothing is ever written
to the database or to disk, so it cannot corrupt the real ledger.

Used by the 'Tamper demo' page and by:  python manage.py tamper_demo
"""
from .block import sha256_text
from .chain import Blockchain

SCENARIOS = {
    "edit_data": "Edit a block's data and leave its stored hash unchanged",
    "edit_and_rehash": "Edit a block's data AND recalculate that block's hash",
    "break_link": "Change a block's previous_hash (and recalculate its own hash)",
}


def build_demo_chain():
    """Build a valid 4-event synthetic chain (genesis + 4 blocks) in memory.

    All names, hashes and remarks are made up for the demonstration.
    """
    chain = Blockchain()
    demo_file_hash = sha256_text("synthetic demonstration file - not real evidence")
    events = [
        ("REGISTERED", "Investigator A", {"from": "", "to": "", "remarks": "Demo registration"}),
        ("TRANSFERRED", "Investigator A", {"from": "Investigator A", "to": "Analyst B", "remarks": "Demo transfer"}),
        ("ANALYSIS_STARTED", "Analyst B", {"from": "", "to": "", "remarks": "Demo analysis started"}),
        ("ARCHIVED", "Analyst B", {"from": "", "to": "", "remarks": "Demo archive"}),
    ]
    for number, (event_type, actor, details) in enumerate(events, start=1):
        chain.add_block(
            timestamp=f"2026-01-0{number}T10:00:00.000000+00:00",
            evidence_id="EV-DEMO",
            custody_event_id=number,
            event_type=event_type,
            actor=actor,
            details=dict(details, recorded_by="demo_user"),
            evidence_hash=demo_file_hash,
        )
    return chain


def run_tamper_demo(scenario="edit_data", block_index=2):
    """Tamper with a COPY of the demo chain and validate before and after.

    Inputs:  scenario - one of SCENARIOS; block_index - which block (1-4) to attack.
    Returns: dict with the original chain, tampered chain, both validation results
             and a plain-English explanation.
    """
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario.")
    if not 1 <= block_index <= 4:
        raise ValueError("Block number must be between 1 and 4.")

    original = build_demo_chain()
    tampered = original.copy()          # <- we only ever change this copy
    victim = tampered.blocks[block_index]

    if scenario == "edit_data":
        victim.actor = "Someone Else"
        explanation = (
            f"The actor in block #{block_index} was changed but its stored hash was left alone. "
            "Validation recalculates the hash from the data, gets a different value, and reports a hash mismatch."
        )
    elif scenario == "edit_and_rehash":
        victim.actor = "Someone Else"
        victim.hash = victim.calculate_hash()   # attacker recalculates this block's hash
        explanation = (
            f"The attacker also recalculated block #{block_index}'s hash, so that block looks fine on its own. "
            "But the NEXT block still stores the old hash as its previous_hash, so the link is broken."
            if block_index < 4 else
            f"Block #{block_index} is the last block, so no later block points to it: this "
            "tampering is NOT detectable by hash-linking alone. This is why the real application "
            "also cross-checks every block against the database record and the evidence's original hash."
        )
    else:  # break_link
        victim.previous_hash = sha256_text("some other block")
        victim.hash = victim.calculate_hash()
        explanation = (
            f"Block #{block_index}'s previous_hash was changed to a different value, so it no longer "
            "equals the hash of the block before it. Validation reports a broken link."
        )

    return {
        "scenario": scenario,
        "scenario_label": SCENARIOS[scenario],
        "block_index": block_index,
        "original_blocks": original.blocks,
        "tampered_blocks": tampered.blocks,
        "original_result": original.validate(),
        "tampered_result": tampered.validate(),
        "explanation": explanation,
    }
