"""views.py - the report page and the PDF download."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from blockchain.services import validate_stored_chain
from evidence.models import Evidence
from verification.services import verify_evidence

from .pdf_generator import build_evidence_report


@login_required
def report_home(request):
    """Page where the user chooses which evidence to create a PDF report for."""
    evidence_items = Evidence.objects.select_related("case").order_by("evidence_id")
    return render(request, "reports/report_home.html", {
        "evidence_items": evidence_items,
        "selected": request.GET.get("evidence", ""),
    })


@login_required
def generate_report(request):
    """Build and return the PDF for ?evidence=EV-0001.

    Optional ?verify_now=1 runs a fresh integrity verification first (and saves it in
    the verification history) so the report contains an up-to-date result.
    """
    evidence = (Evidence.objects.select_related("case", "registered_by")
                .filter(evidence_id=request.GET.get("evidence", "")).first())
    if evidence is None:
        messages.error(request, "Please choose a registered evidence item.")
        return redirect("report_home")

    if request.GET.get("verify_now") == "1":
        verify_evidence(evidence, request.user)

    events = evidence.custody_events.select_related("block_record").order_by("timestamp", "id")
    latest_verification = evidence.verification_records.select_related("verified_by").first()
    chain_result = validate_stored_chain()   # fresh validation at report time
    pdf_bytes = build_evidence_report(
        evidence=evidence, events=events, latest_verification=latest_verification,
        chain_result=chain_result, validated_at=chain_result.checked_at, generated_by=request.user,
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"custody_report_{evidence.evidence_id}_{timezone.now():%Y%m%d_%H%M%S}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
