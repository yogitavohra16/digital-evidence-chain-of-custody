# Blockchain-Based Digital Evidence Chain of Custody System (Python / Django)

A beginner-friendly web application that manages digital-evidence metadata, calculates **SHA-256**
hashes to verify evidence-file integrity, records every custody event in a **custom Python
blockchain**, detects changes to historical ledger records, and generates **PDF reports**.

> **Honest scope statement.** This is an academic minor-project *demonstration*. The blockchain is a
> local, application-level, hash-linked ledger - **not** a distributed production blockchain - and the
> system is **not a secure forensic evidence vault**. It makes no claim of legal admissibility.

Tested with **Python 3.13.13**, **Django 5.2.18 (LTS)**, **ReportLab 5.0.1**, SQLite. Target: Windows 11 + VS Code.

---

## 1. What the project is
A Django web app where investigators register evidence files, record who handled them, verify they are
unchanged, inspect a hash-linked ledger, and download a PDF chain-of-custody report.

## 2. Why it is needed
Custody logs in paper or spreadsheets can be altered silently, and files can change without notice.
Hashes make file changes detectable; a hash-linked ledger makes history edits detectable.

## 3. How SHA-256 and the blockchain work here
* **Evidence hash:** `H_evidence = SHA256(file bytes)`, computed in 1 MiB chunks at registration and kept forever.
* **Block hash:** `H_i = SHA256(CanonicalJSON(D_i))` (block data without its own hash).
* **Link:** each block stores the previous block's hash. **Validation** recalculates every hash and checks every link.
* **Verification:** re-hash the stored file, compare with the original hash (`MATCH` / `MISMATCH` / missing / error).

Full explanation with a worked example: [`docs/BLOCKCHAIN_EXPLAINED.md`](docs/BLOCKCHAIN_EXPLAINED.md).

## 4. Main features
Login/logout (Django auth) - dashboard with live statistics - cases (create/list/detail/search) -
evidence registration (auto SHA-256, size/type limits, private storage) - custody events with validation
rules - blockchain ledger with per-block status - evidence verification with history - PDF reports (ReportLab) -
safe tamper demo - search and filters - 45 automated tests.

## 5. Technology stack
Python 3.13 - Django 5.2 (templates, ORM, auth, forms) - SQLite - `hashlib` SHA-256 - custom blockchain -
ReportLab - HTML5/CSS3 - Bootstrap 5.3.3 and Bootstrap Icons (bundled locally, works offline) - vanilla JS.

## 6. Software prerequisites
Windows 11, **Python 3.13.x** (python.org, tick "Add to PATH"), Visual Studio Code (+ Python extension).


## 7-9. Virtual environment and dependencies
```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.
The prompt should start with `(venv)`.

## 10. Migrations (create the database; also creates the genesis block)
```powershell
python manage.py migrate
```
## 11. Create a login account
```powershell
python manage.py createsuperuser
```
Choose a username and password. This account works for the app and for `/admin/`.

## 12-13. Start the server and open the app
```powershell
python manage.py runserver
```
Open **http://127.0.0.1:8000/**

## 14. Log in
Use the username/password from step 13.

## 15. Create a case
**Cases -> New case**, enter a title (use a title starting with `DEMO` for the demo below) -> **Create case**.
The Case ID `CASE-0001` is generated automatically.

## 16. Register evidence
**Register evidence** -> pick the case, choose a file (try `sample_data\sample_evidence_note.txt`), enter "Collected by" ->
**Register and hash evidence**. You get `EV-0001`, its SHA-256 hash, a REGISTERED custody event and block #1.

## 17. Record custody events
**Custody event** -> choose evidence and action (Transferred, Accessed, Analysis started/completed, Returned, Archived),
enter *Performed by*, *From/To* when relevant and *Purpose / remarks* -> **Record event**. A new block is created.
Events cannot be edited or deleted. Rules: transfers need different From/To; returns need To; analysis must start before it completes;
archived evidence accepts no more events.

## 18. Verify evidence
**Verify evidence** -> select an item -> **Verify now**. Results: `INTEGRITY VERIFIED`, `INTEGRITY MISMATCH`, `FILE MISSING`, `VERIFICATION ERROR`.
Both hashes are shown, and every run is saved in the history. The original hash is never overwritten.

## 19. Validate the blockchain
**Blockchain ledger** validates the whole chain every time it loads (hashes are recalculated, links checked, blocks cross-checked with
the database). The dashboard shows the same status. **Re-run validation** reloads it.

## 20. Generate a PDF report
**PDF reports** -> select evidence (tick *fresh verification* if wanted) -> **Generate PDF report**. Contains case/evidence details, original hash,
custody history with block numbers and hashes, latest verification, blockchain validation result/time and generation timestamp.

## 21. Run the tests
```powershell
python manage.py test
```
## 22. Stop the server
Press **Ctrl + C** in the terminal. Leave the virtual environment with `deactivate`.

## 23. Common errors
See [`docs/SETUP_AND_TROUBLESHOOTING.md`](docs/SETUP_AND_TROUBLESHOOTING.md) (execution policy, missing modules, no such table, port in use, upload limits, ...).

## 24. Security limitations
* SQLite + a local folder are fine for a demo but **not** high-assurance forensic storage (no encryption at rest, no write-once media, no off-site backup).
* The ledger is **tamper-evident, not tamper-proof**; someone who can rewrite the whole chain and database could create a valid-looking chain.
* A hash match proves unchanged *content*, not origin or authenticity; a mismatch is a reason to investigate, not proof of malice.
* A username plus a typed handler name does not independently prove real-world identity.
* All logged-in users have the same permissions (no role system, to stay simple).
* Development `SECRET_KEY` and `DEBUG=True` by default - do not expose this server to the internet.
* No claim of legal admissibility is made by the software or its reports.
* Implemented safeguards: Django auth and hashed passwords, CSRF protection, server-side validation, login required on every page,
  extension allow-list and size limit (`config/settings.py`), random storage filenames, private evidence folder with no URL route,
  no file contents in blocks, read-only admin for history tables, ledger must validate before new entries are accepted.
  There is deliberately no evidence download feature.

## 25. Folder structure
```
digital_evidence_chain_of_custody/
  manage.py  requirements.txt  README.md  .gitignore
  config/        settings.py, urls.py, wsgi.py, asgi.py
  evidence/      models, forms, views, services, hashing, storage, admin, templatetags, management/commands/demo_modify_file.py
  blockchain/    block.py, chain.py, validation.py, services.py, demo.py, models, views, management/commands/tamper_demo.py
  verification/  models, services, forms, views
  reports/       pdf_generator.py, views
  templates/     base.html, pages, partials
  static/        css/forensic.css, js/app.js, vendor/ (Bootstrap + Icons, offline)
  tests/         45 automated tests
  docs/          PROJECT_OVERVIEW.md  BLOCKCHAIN_EXPLAINED.md  SETUP_AND_TROUBLESHOOTING.md  VIVA_QUESTIONS.md
  sample_data/   synthetic sample file + README
  (created when you run the app: db.sqlite3, private_evidence/)
```

## 26. How to demonstrate tampering safely
1. **Ledger tamper demo (recommended):** sidebar **Tamper demo (safe)** - pick a scenario, tick the confirmation box, run. Or
   `python manage.py tamper_demo --scenario edit_data --block 2`. A synthetic in-memory chain is copied and the copy is altered; validation fails.
2. **Automated proof:** `python manage.py test tests.test_blockchain_core tests.test_ledger_database -v 2`.
3. **Modified evidence file:** follow `sample_data/README.md` (works only for cases titled `DEMO...`).

None of these alter your real ledger. The real ledger is never silently changed by the application.

## Time zones
Django stores timestamps in UTC and displays them in `TIME_ZONE` (default `Asia/Kolkata`, editable in `config/settings.py`). Blocks use UTC text.

## Licence notes
Bootstrap and Bootstrap Icons are MIT-licensed; their licence files are in `static/vendor/`.
