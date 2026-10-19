"""tamper_demo.py - command-line version of the safe tamper demonstration.

Run:  python manage.py tamper_demo
It uses an in-memory synthetic chain only. No database rows or files are changed.
"""
from django.core.management.base import BaseCommand

from blockchain.demo import SCENARIOS, run_tamper_demo


class Command(BaseCommand):
    """Print the validation result before and after tampering with a copy."""

    help = "Safely demonstrate blockchain tamper detection on an in-memory synthetic chain."

    def add_arguments(self, parser):
        """Optional arguments: which scenario and which block to tamper with."""
        parser.add_argument("--scenario", choices=list(SCENARIOS), default="edit_data")
        parser.add_argument("--block", type=int, default=2, help="Block number to tamper with (1-4).")

    def handle(self, *args, **options):
        """Run the demo and print a readable report."""
        demo = run_tamper_demo(options["scenario"], options["block"])
        self.stdout.write(f"Scenario: {demo['scenario_label']} (block #{demo['block_index']})\n")
        self.stdout.write("1) Original synthetic chain:")
        self.stdout.write("   " + demo["original_result"].message)
        self.stdout.write("\n2) After tampering with a COPY:")
        self.stdout.write("   " + demo["tampered_result"].message)
        for problem in demo["tampered_result"].all_problems:
            self.stdout.write(f"   - {problem}")
        self.stdout.write("\n" + demo["explanation"])
        self.stdout.write("\nNo database records or files were changed.")
