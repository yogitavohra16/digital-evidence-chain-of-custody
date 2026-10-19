# Setup and Troubleshooting (Windows 11, PowerShell, VS Code)

## Prerequisites
* Python **3.13.x** from python.org (tick "Add python.exe to PATH" and install the `py` launcher).
* Visual Studio Code (optional but recommended) with the Python extension.

## Setup
```powershell
# 1. Open the extracted folder (the one containing manage.py)
cd C:\path\to\digital_evidence_chain_of_custody

# 2. Create and activate a virtual environment
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Create the database tables (also creates the genesis block)
python manage.py migrate

# 5. Create your login account
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```
Open <http://127.0.0.1:8000/> and sign in. Stop the server with **Ctrl + C**.

## Run the tests
```powershell
python manage.py test
```
Tests use a temporary database and temporary evidence folder; your real data is untouched.

## Common problems
| Problem | Fix |
|---|---|
| `py` is not recognised | Reinstall Python and tick the launcher; or use `python -m venv venv` |
| `running scripts is disabled` when activating | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then activate again |
| `No module named django` | The virtual environment is not active (prompt should start with `(venv)`) - activate it and re-run `pip install -r requirements.txt` |
| `Could not import Django` | Same as above |
| `No such table` | Run `python manage.py migrate` in the folder containing `manage.py` |
| `Error: That port is already in use` | `python manage.py runserver 8001` |
| Pillow / ReportLab fails to install | Upgrade pip, use Python 3.13 64-bit, re-run `pip install -r requirements.txt` |
| Styles look unstyled | Use `runserver` (it serves `/static/` automatically with DEBUG on); hard-refresh with Ctrl+F5 |
| Upload rejected: "type not allowed" | Extension must be in `ALLOWED_EVIDENCE_EXTENSIONS` (`config/settings.py`) |
| Upload rejected: "larger than ... limit" | Raise `MAX_EVIDENCE_UPLOAD_BYTES` in `config/settings.py` |
| "Evidence was NOT registered ... ledger" | The ledger failed validation. Open **Blockchain ledger** to see which block is wrong. Nothing is auto-repaired. |
| FILE MISSING during verification | The stored file in `private_evidence\` was moved or deleted |
| Time looks different from UTC | Intentional: stored in UTC, shown in `TIME_ZONE` (default Asia/Kolkata) |
| Forgot password | `python manage.py changepassword <username>` |
| Start over from scratch | Stop the server, delete `db.sqlite3` and the `private_evidence` folder, run `migrate` again |

## Environment variables (optional)
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`True`/`False`), `DJANGO_ALLOWED_HOSTS` (comma separated).
PowerShell example: `$env:DJANGO_DEBUG = "True"`. No `.env` file is needed for local use.
