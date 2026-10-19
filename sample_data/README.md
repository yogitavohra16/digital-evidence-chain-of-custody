# Sample data (synthetic)

`sample_evidence_note.txt` is a tiny, made-up text file you can upload as evidence
during a demonstration. It contains no real or sensitive data.

## Make your own sample files (PowerShell, run inside the project folder)

```powershell
"My own demo evidence file" | Out-File -Encoding ascii sample_data\my_demo_file.txt
```

## Compare hashes yourself (PowerShell)

```powershell
Get-FileHash sample_data\sample_evidence_note.txt -Algorithm SHA256
```

The value shown should equal the "Original SHA-256" displayed by the application
after you register that file (PowerShell prints it in upper case; the app uses lower case).

## Demonstrate a hash MISMATCH safely

1. Create a case whose title **starts with the word DEMO** (for example `DEMO case`).
2. Register `sample_evidence_note.txt` in that case (suppose it becomes `EV-0001`).
3. Open **Verify evidence** and verify it -> `INTEGRITY VERIFIED`.
4. In PowerShell (project folder, virtual environment active):
   ```powershell
   python manage.py demo_modify_file EV-0001 --confirm
   ```
5. Verify again -> `INTEGRITY MISMATCH`. The original hash was NOT changed.
6. Undo the change:
   ```powershell
   python manage.py demo_modify_file EV-0001 --confirm --restore
   ```

The command refuses to touch evidence that is not in a case titled `DEMO...`.
