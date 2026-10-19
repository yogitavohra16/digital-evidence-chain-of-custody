"""views.py - the evidence verification page."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .forms import VerifyEvidenceForm
from .models import VerificationRecord
from .services import verify_evidence


@login_required
def verify_view(request):
    """Show the evidence picker; on POST run the verification and show the outcome.

    A view receives the request and returns a response (here, an HTML page).
    Verification changes data (it adds a history row), so it only runs on POST,
    which is protected by the CSRF token in the form.
    """
    latest_record = None
    if request.method == "POST":
        form = VerifyEvidenceForm(request.POST)
        if form.is_valid():
            latest_record = verify_evidence(form.cleaned_data["evidence"], request.user)
            if latest_record.result == VerificationRecord.Result.MATCH:
                messages.success(request, "Verification completed.")
            else:
                messages.warning(request, "Verification completed - review the result below.")
    else:
        # Allow ?evidence=EV-0001 to preselect an item (links from other pages).
        form = VerifyEvidenceForm(initial={"evidence": request.GET.get("evidence", "")})

    history = VerificationRecord.objects.select_related("evidence", "verified_by")
    selected = request.GET.get("evidence") or (latest_record.evidence.evidence_id if latest_record else "")
    if selected:
        history = history.filter(evidence__evidence_id=selected)
    return render(request, "verification/verify.html", {
        "form": form,
        "record": latest_record,
        "history": history[:15],
        "filtered_by": selected,
    })
