# Project Overview

## Problem statement
Digital evidence (files, images, logs) is easy to copy and alter, and a paper or spreadsheet
chain-of-custody log is easy to edit afterwards without anyone noticing. Investigators need a
way to show (a) that an evidence file is still byte-for-byte the same as when it was collected
and (b) who handled it and when, in a record where later edits are noticeable.

## Need for the project
* A cryptographic hash (SHA-256) gives every file a fingerprint that changes if the file changes.
* A hash-linked ledger makes edits to the custody history **detectable**.
* A web application makes this usable by a non-programmer investigator and produces a printable PDF.

## Objectives
1. Register evidence and compute its SHA-256 hash automatically.
2. Record every custody event and write it to a custom Python blockchain.
3. Verify evidence files against their registered hash at any time.
4. Validate the ledger and report any modified or mis-linked block.
5. Generate a PDF report from real data.
6. Keep the code small enough to be understood and explained in a viva.

## Scope
**In scope:** login, dashboard, cases, evidence registration, custody events, blockchain ledger,
evidence verification, PDF report, safe tamper demonstration, automated tests.

**Out of scope (deliberately):** AI/ML, cryptocurrency, mining/proof-of-work, Ethereum or any
public blockchain, networking/consensus, Docker, cloud, microservices.

## Architecture
```
Browser --> Django views (login required) --> services (business rules)
                                              |-- evidence/hashing.py     SHA-256 of files
                                              |-- blockchain/block.py     Block + canonical JSON + hash
                                              |-- blockchain/chain.py     in-memory chain
                                              |-- blockchain/validation.py  tamper detector (pure Python)
                                              |-- blockchain/services.py  chain <-> SQLite bridge
                                              |-- verification/services.py  re-hash + compare
                                              `-- reports/pdf_generator.py  ReportLab PDF
SQLite (db.sqlite3): cases, evidence, custody events, blocks, verification records
Private folder (private_evidence/): the uploaded evidence files themselves
```

## Modules (Django apps)
| App | Purpose |
|---|---|
| `config` | settings, main URL table |
| `evidence` | Case, Evidence, CustodyEvent models; forms; views; hashing; services |
| `blockchain` | BlockRecord model; block/chain/validation code; ledger page; tamper demo |
| `verification` | VerificationRecord model; integrity verification page |
| `reports` | PDF generation and report page |

## Database design
* `Case` 1---* `Evidence` 1---* `CustodyEvent` 1---1 `BlockRecord`
* `Evidence` 1---* `VerificationRecord`
* Unique constraints: `case_id`, `evidence_id`, `block_index`, `current_hash`.
* `PROTECT` foreign keys stop deleting a case/evidence/user that other records depend on.
* A check constraint requires the hash to be 64 hex characters, and only block 0 may have no custody event.
* Timestamps are stored in UTC by Django and shown in `TIME_ZONE` (default `Asia/Kolkata`, set in `config/settings.py`).

## Consistency between events and blocks
Registering evidence or recording an event runs inside one `transaction.atomic()` block:
event row -> status update -> block row. If any step fails everything is rolled back, so an event
is never reported as recorded without its block. Before adding anything, the whole ledger is
validated; a damaged ledger blocks new entries instead of being "repaired".

## Limitations
* Local, application-level blockchain: **not distributed**, no consensus, one copy.
* Tamper-**evident**, not tamper-proof: someone able to rewrite the entire database could rebuild a valid chain.
* SQLite and a local folder are fine for a demo but are not a secure forensic evidence vault
  (no encryption at rest, no write-once storage, no off-site copy).
* A hash match shows content is unchanged since registration; it does not prove origin or authenticity.
* A typed handler name plus a username does not independently prove a person's identity.
* Users are not split into roles: every logged-in user can use every feature (kept simple on purpose).
* The software makes **no claim of legal admissibility**.
