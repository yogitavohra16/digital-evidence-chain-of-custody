"""block.py - what a single block is, and how its hash is calculated.

WHAT IS A BLOCK?
    A block is one record in the ledger. In this project every block describes ONE
    custody event (for example "EV-0001 was transferred from Alice to Bob"), plus
    the SHA-256 hash of the evidence file and the hash of the PREVIOUS block.

WHAT IS A HASH?
    A hash function turns any input into a fixed-length "fingerprint". With SHA-256
    the fingerprint is 64 hexadecimal characters. Change even one character of the
    input and you get a completely different fingerprint.

BLOCK HASH FORMULA (Formula 2 in the documentation):
    H_i = SHA256( CanonicalJSON( D_i ) )
    where D_i is the block's data WITHOUT its own hash.

IMPORTANT SECURITY NOTE (read this!):
    A hash-linked chain is TAMPER-EVIDENT, not absolutely immutable. If someone can
    rewrite the whole chain (every block, every hash) AND the database, they can
    build a new chain that still validates. This prototype is a local,
    application-level blockchain, not a distributed production blockchain.
"""
import hashlib
import json
from dataclasses import dataclass, field

# The genesis block (block number 0) must be IDENTICAL every time it is created, so
# its timestamp is a fixed constant instead of "now". Otherwise every new database
# would get a different genesis hash.
GENESIS_TIMESTAMP = "2026-01-01T00:00:00+00:00"

# 64 zeros: used as the "previous hash" of the genesis block (there is no block
# before it) and as the evidence hash of the genesis block (it has no evidence).
ZERO_HASH = "0" * 64


def canonical_json(data):
    """Turn a dictionary into one exact, repeatable JSON string.

    Why it is needed (deterministic serialization):
        SHA-256 hashes BYTES. If the same data could be written as text in two
        different ways (keys in a different order, extra spaces, ...), we would get
        two different hashes for the same block and validation would fail by
        accident. "Canonical" means there is only ONE correct way to write the data:
          - sort_keys=True        -> keys are always in alphabetical order
          - separators=(",", ":") -> no extra spaces
          - ensure_ascii=True     -> non-English characters become \\uXXXX escapes,
                                     so the encoding is the same on every computer

    Input:  data - a dictionary containing only JSON-friendly values.
    Returns: the canonical JSON text (str).
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text):
    """Return the SHA-256 hash (64 hex characters) of a piece of text.

    The text is first converted to bytes using UTF-8, because hash functions work
    on bytes, not on Python strings.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Block:
    """One block of the custody ledger.

    Fields that are part of the hash (the "block data" D_i):
        index           - position in the chain (genesis = 0, then 1, 2, 3 ...)
        timestamp       - when the event happened, as a UTC ISO-8601 text string
        evidence_id     - e.g. "EV-0001" (or "GENESIS" for the first block)
        custody_event_id- primary key of the CustodyEvent row (None for genesis)
        event_type      - e.g. "TRANSFERRED"
        actor           - name of the person who handled the evidence
        details         - small dictionary: from/to, remarks, recorded-by username
        evidence_hash   - SHA-256 of the evidence FILE (never the file itself!)
        previous_hash   - hash of the block before this one

    Field that is NOT part of the hash:
        hash            - the result of the calculation. A value cannot be an
                          input to its own calculation, so it is excluded.
    """

    index: int
    timestamp: str
    evidence_id: str
    custody_event_id: int | None
    event_type: str
    actor: str
    details: dict
    evidence_hash: str
    previous_hash: str
    hash: str = field(default="")

    def data_for_hashing(self):
        """Return the block data D_i (everything except the block's own hash)."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "evidence_id": self.evidence_id,
            "custody_event_id": self.custody_event_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "details": self.details,
            "evidence_hash": self.evidence_hash,
            "previous_hash": self.previous_hash,
        }

    def serialize(self):
        """Return the canonical JSON text of the block data (what we hash and store)."""
        return canonical_json(self.data_for_hashing())

    def calculate_hash(self):
        """Calculate H_i = SHA256(CanonicalJSON(D_i)) from the CURRENT block data.

        Why validation calls this instead of trusting `self.hash`:
            The stored hash is only a claim. If someone edited the data and left
            the old hash in place, the stored hash would still look fine. Only by
            RECALCULATING from the data can we notice that the two no longer agree.
        """
        return sha256_text(self.serialize())

    def seal(self):
        """Calculate the hash and store it in `self.hash`. Returns the block."""
        self.hash = self.calculate_hash()
        return self

    def to_dict(self):
        """Return all fields (including the hash) as a dictionary."""
        data = self.data_for_hashing()
        data["hash"] = self.hash
        return data

    @classmethod
    def from_stored_data(cls, serialized_data, stored_hash):
        """Rebuild a Block from the JSON text and hash saved in the database.

        Inputs: serialized_data - the canonical JSON text of the block data.
                stored_hash     - the hash value that was saved with it.
        Returns: a Block. Its `hash` is the STORED value (not recalculated), so a
                 validator can compare it with `calculate_hash()`.
        """
        data = json.loads(serialized_data)
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            evidence_id=data["evidence_id"],
            custody_event_id=data["custody_event_id"],
            event_type=data["event_type"],
            actor=data["actor"],
            details=data["details"],
            evidence_hash=data["evidence_hash"],
            previous_hash=data["previous_hash"],
            hash=stored_hash,
        )


def create_genesis_block():
    """Create the genesis block (block 0), the fixed starting point of the chain.

    Because every value is a constant, this function returns an identical block
    (with an identical hash) every single time, on every computer. That is what
    "deterministic" means. The validator also uses it to confirm that block 0 in the
    database really is the genuine genesis block.
    """
    genesis = Block(
        index=0,
        timestamp=GENESIS_TIMESTAMP,
        evidence_id="GENESIS",
        custody_event_id=None,
        event_type="GENESIS",
        actor="SYSTEM",
        details={"message": "Genesis block - start of the custody ledger"},
        evidence_hash=ZERO_HASH,
        previous_hash=ZERO_HASH,
    )
    return genesis.seal()
