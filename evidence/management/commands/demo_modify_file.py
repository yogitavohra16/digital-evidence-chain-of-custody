"""demo_modify_file.py - DEMO ONLY: change a stored evidence file to show a hash mismatch.

Run:   python manage.py demo_modify_file EV-0001 --confirm
Undo:  python manage.py demo_modify_file EV-0001 --restore

SAFETY RULES
    * It refuses to work unless the evidence belongs to a case whose title starts
      with "DEMO", so real evidence cannot be changed by accident.
    * It requires --confirm.
    * It only appends a known marker to the end of the stored COPY; --restore
      removes exactly that marker.
    * It never changes the database or the blockchain, and never touches the original
      hash. That is the point: verification will report a MISMATCH.
"""
from django.core.management.base import BaseCommand, CommandError

from evidence.models import Evidence

MARKER = b"\n[DEMO-MODIFICATION]\n"


class Command(BaseCommand):
    """Append (or remove) a demo marker at the end of a stored evidence file."""

    help = "DEMO ONLY: modify the stored copy of evidence in a case titled 'DEMO...' to show a hash mismatch."

    def add_arguments(self, parser):
        """Arguments: the evidence ID and --confirm / --restore flags."""
        parser.add_argument("evidence_id")
        parser.add_argument("--confirm", action="store_true", help="Required to modify the file.")
        parser.add_argument("--restore", action="store_true", help="Remove the demo marker again.")

    def handle(self, *args, **options):
        """Apply the change after all safety checks pass."""
        try:
            evidence = Evidence.objects.select_related("case").get(evidence_id=options["evidence_id"])
        except Evidence.DoesNotExist:
            raise CommandError("No such evidence ID.")
        if not evidence.case.title.upper().startswith("DEMO"):
            raise CommandError("Refused: this evidence is not in a case whose title starts with 'DEMO'.")
        if not options["confirm"]:
            raise CommandError("Add --confirm to proceed (this modifies the stored COPY of the demo file).")

        path = evidence.stored_file.path
        with open(path, "rb") as handle:
            content = handle.read()

        if options["restore"]:
            if not content.endswith(MARKER):
                raise CommandError("The demo marker is not present; nothing to restore.")
            with open(path, "wb") as handle:
                handle.write(content[: -len(MARKER)])
            self.stdout.write(self.style.SUCCESS("Demo marker removed. Verification should now MATCH again."))
        else:
            with open(path, "ab") as handle:
                handle.write(MARKER)
            self.stdout.write(self.style.WARNING("Demo marker appended. Verification should now show a MISMATCH."))
