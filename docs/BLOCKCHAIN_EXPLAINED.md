# Blockchain Explained (for this project)

## 1. SHA-256 in one minute
SHA-256 turns any input into 64 hexadecimal characters (256 bits).
* Same input -> always the same output.
* One changed bit -> a completely different output.
* You cannot practically work backwards from the output to the input.

```python
import hashlib
hashlib.sha256(b"abc").hexdigest()
# 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
```

## 2. Evidence hashing (Formula 1)
`H_evidence = SHA256(F)` where `F` is the complete byte content of the file.
Large files are read in 1 MiB chunks and fed to the hash object one chunk at a time
(`hasher.update(chunk)`); the final digest is identical to hashing the file in one piece.
See `evidence/hashing.py`.

## 3. A block
| Field | Meaning |
|---|---|
| index | position (0 = genesis) |
| timestamp | UTC ISO-8601 text |
| evidence_id, custody_event_id | what the block is about |
| event_type, actor, details | what happened and who did it |
| evidence_hash | SHA-256 of the evidence **file** (never the file) |
| previous_hash | hash of the block before |
| hash | this block's own hash (NOT part of its own input) |

## 4. Canonical JSON and the block hash (Formula 2)
`H_i = SHA256( CanonicalJSON(D_i) )`

`D_i` is every field except `hash`. "Canonical" means one exact text form:
sorted keys, no spaces (`separators=(",", ":")`), ASCII escapes. Without it, `{"a":1,"b":2}`
and `{"b":2,"a":1}` would be the same data but hash differently and validation would fail by accident.

## 5. Previous-hash linking (Formula 3)
`PreviousHash_i = Hash_(i-1)`. Because `previous_hash` is inside the data that is hashed, a block's
hash depends on the whole history before it.

## 6. Validation (Formula 4)
For every block the validator **recalculates** the hash and compares it with the stored one, then
checks the link. It never trusts the stored hash - a stored hash is only a claim.
It also checks that block 0 is the genuine genesis block and that indexes run 0,1,2,...
This project additionally cross-checks each block with its `CustodyEvent` row and with the
evidence's original hash, so editing database tables directly is detected too.

## 7. Worked example
```
Block 0 (genesis)  hash = 1d5f8276...
Block 1  previous_hash = 1d5f8276...   data: EV-0001 REGISTERED   hash = 276a10f4...
Block 2  previous_hash = 276a10f4...   data: EV-0001 TRANSFERRED hash = 20fbbd96...
```
Attack A - edit block 1's actor and leave its hash: recalculation gives a new value != stored -> **hash mismatch**.
Attack B - edit block 1 *and* recompute its hash to `9aa3...`: block 1 now looks fine, but block 2 still
holds `previous_hash = 276a10f4...` which no longer equals block 1's hash -> **broken link**.
Attack C - rewrite block 1 *and every later block* and the matching database rows: the chain validates again.
That is the fundamental limit of a single local copy (section 9).

## 8. Evidence integrity vs ledger integrity
| | Evidence integrity | Ledger integrity |
|---|---|---|
| Question | Is the file the same as when registered? | Is the custody history unmodified? |
| Method | re-hash file, compare with original hash | recalculate block hashes, check links |
| Page | Verify evidence | Blockchain ledger |
| Mismatch means | file content differs | a block/record was altered or is inconsistent |

Neither proves *who* created the file or that the registrant told the truth.

## 9. Why this is not a production blockchain
No peer-to-peer network, no consensus, no independent copies, no signatures, no proof-of-work.
It is a hash-linked log stored in one SQLite file: tamper-**evident**, not tamper-proof.
Real systems add many independent nodes, digital signatures and consensus so a single party
cannot quietly rewrite history. Anchoring the latest block hash somewhere outside the system
(printed in a report, emailed to a supervisor) would be a sensible future improvement.

## 10. Safe tamper demonstration
* Page **Tamper demo (safe)** or `python manage.py tamper_demo` - builds a synthetic chain in memory,
  tampers with a *copy*, and shows validation failing. No real data is touched.
* Automated tests (`tests/test_blockchain_core.py`) do the same for the in-memory chain, and
  `tests/test_ledger_database.py` edits rows in a temporary test database.
