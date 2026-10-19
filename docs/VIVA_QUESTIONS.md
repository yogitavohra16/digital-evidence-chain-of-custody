# Viva Questions and Answers

**Q1. What problem does your project solve?**
It keeps a tamper-evident chain-of-custody record for digital evidence and lets you check that an evidence file is unchanged since registration, using SHA-256 hashes and a hash-linked ledger.

**Q2. What is SHA-256?**
A cryptographic hash function that maps any input to a fixed 256-bit (64 hex character) fingerprint. The same input always gives the same output; a tiny change gives a completely different output; it cannot practically be reversed.

**Q3. How do you hash a large file without running out of memory?**
`evidence/hashing.py` reads 1 MiB chunks and calls `hasher.update(chunk)` for each one. The final digest equals hashing the whole file at once (a test proves it).

**Q4. Does a matching hash prove the file is authentic?**
No. It proves the content is the same as when it was registered. It does not prove who created it, where it came from, or that the registered file was genuine in the first place.

**Q5. Does a hash mismatch prove tampering?**
No. It proves the content differs from the registered version. The cause could be corruption, an accidental edit or malicious change, so it needs investigation.

**Q6. What is a block in your system?**
One ledger record for one custody event: index, timestamp, evidence ID, event ID, event type, actor, details, evidence hash, previous hash and its own hash.

**Q7. What is the genesis block and why is it fixed?**
Block 0, the starting point. All its values (including the timestamp) are constants, so it is identical everywhere and the validator can check it is genuine. It is created once after `migrate` and never duplicated.

**Q8. Why does each block store the previous block's hash?**
It chains the blocks. Because the previous hash is part of the data being hashed, changing an old block changes its hash and breaks the link stored in the next block.

**Q9. What is canonical JSON and why do you need it?**
A single, exact way of writing JSON (sorted keys, no extra spaces, ASCII escapes). Hashing works on bytes, so identical data must always serialize to identical text or validation would fail by accident.

**Q10. Why doesn't a block include its own hash in the data that is hashed?**
A value cannot be an input to its own calculation. The hash is computed from the other fields and stored next to them.

**Q11. How does validation work, and why recalculate instead of trusting the stored hash?**
For every block it recomputes `SHA256(CanonicalJSON(data))` and compares it with the stored hash, then checks `previous_hash == previous block's hash`, the genesis block and index order. A stored hash is just a claim; only recalculation reveals edited data.

**Q12. What if an attacker edits a block and recalculates its hash?**
That block then looks fine, but the next block's `previous_hash` no longer matches, so the link breaks. My app also cross-checks blocks with the custody-event rows and the evidence's original hash.

**Q13. Can the attacker still win?**
Yes, if they can rewrite every later block and the database rows consistently. A single local chain is tamper-evident, not tamper-proof; real blockchains use many independent copies and consensus.

**Q14. Why is this not a "real" blockchain?**
No network, no consensus, no mining, no digital signatures, no distributed copies. It is an educational, application-level hash-linked ledger stored in SQLite.

**Q15. Why not use proof-of-work or Ethereum?**
They solve problems (trustless money, distributed agreement) that this project does not have, and would add complexity unrelated to evidence integrity.

**Q16. What does Django's ORM do?**
It lets you work with database tables as Python classes (models), e.g. `Evidence.objects.filter(...)`, instead of writing SQL.

**Q17. What are migrations?**
Generated Python files describing database changes. `makemigrations` writes them, `migrate` applies them to SQLite.

**Q18. How are model, view, template and URL connected?**
A URL pattern maps an address to a view; the view reads or writes models and passes data to a template, which renders HTML.

**Q19. How does a Django form protect the application?**
It validates input on the server (required fields, file type, size, custody rules) and returns error messages. CSRF tokens protect every POST form.

**Q20. How do you keep the evidence and ledger consistent?**
Saving the custody event, updating status and creating the block happen inside one `transaction.atomic()`. If the block fails, everything rolls back. A damaged ledger blocks new entries and is never auto-repaired.

**Q21. How are uploaded files handled safely?**
Extension allow-list and size limit; stored under a random UUID name in a private folder; no URL serves that folder; the user's filename is only stored as text; files are never executed; the stored copy is re-hashed after saving.

**Q22. Why store the evidence file separately from the blockchain?**
Blocks hold only the file's hash and metadata. Putting files in blocks would bloat the ledger and leak content; the hash is enough to detect change.

**Q23. How do you prevent duplicate evidence IDs?**
The next number is generated inside a transaction and the `evidence_id` column is `unique`; a duplicate is rejected by the database and the code retries.

**Q24. Why can custody events not be edited or deleted?**
The chain of custody is an append-only history. There is no edit/delete page, the admin shows them read-only, and the blockchain would flag a direct database edit.

**Q25. How did you test the system?**
45 automated Django tests: known SHA-256 vector, same/different file hashes, genesis, linking, valid chain, modified block, broken link, DB tampering, registration, verification (match / mismatch / missing), authentication, custody events and PDF generation. Run with `python manage.py test`.

**Q26. How do you demonstrate tampering safely?**
The *Tamper demo* page or `python manage.py tamper_demo` tampers with a copy of a synthetic in-memory chain; the unit tests do likewise. Real evidence and the real ledger are never modified.

**Q27. What are the main security limitations?**
SQLite and a local folder are not a forensic vault (no encryption, no write-once media); usernames and typed names do not prove identity; no per-role permissions; the secret key is a development key; no legal-admissibility claim.

**Q28. How are timestamps handled?**
Stored in UTC (`USE_TZ=True`), displayed in the configured `TIME_ZONE`. Blocks use the UTC ISO-8601 text. The server sets the time, so users cannot back-date events.
