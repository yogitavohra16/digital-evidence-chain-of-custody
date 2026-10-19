"""views.py - the functions that answer web requests for cases, evidence and custody.

WHAT IS A VIEW?
    A view receives an HTTP request and returns an HTTP response (usually an HTML
    page built from a template). `@login_required` redirects anonymous visitors to
    the login page, so every page below needs authentication.

HOW TEMPLATES SHOW DATABASE DATA
    A view collects data (for example `Evidence.objects.all()`), passes it to
    `render(request, "template.html", {...})` as a "context" dictionary, and the
    template prints values with {{ variable }} and loops with {% for %}.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from blockchain.models import BlockRecord
from blockchain.services import LedgerInvalidError, validate_stored_chain

from .forms import CaseForm, CustodyEventForm, EvidenceRegistrationForm
from .models import Case, CustodyEvent, Evidence
from .services import add_custody_event, create_case, register_evidence


def _paginate(request, queryset, per_page=12):
    """Split a queryset into pages. Returns the Page for ?page=N (default 1)."""
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


@login_required
def dashboard(request):
    """Dashboard: statistics are counted from the real database on every page load."""
    chain_result = validate_stored_chain()
    context = {
        "total_cases": Case.objects.count(),
        "total_evidence": Evidence.objects.count(),
        "total_events": CustodyEvent.objects.count(),
        "total_blocks": BlockRecord.objects.count(),
        "latest_evidence": Evidence.objects.select_related("case")[:5],
        "recent_events": CustodyEvent.objects.select_related("evidence", "block_record")
                                             .order_by("-timestamp", "-id")[:8],
        "chain_result": chain_result,
    }
    return render(request, "dashboard.html", context)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
@login_required
def case_list(request):
    """List cases. Supports ?q=text (Case ID or title) and ?status=OPEN."""
    cases = Case.objects.select_related("created_by")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        cases = cases.filter(Q(case_id__icontains=query) | Q(title__icontains=query))
    if status in Case.Status.values:
        cases = cases.filter(status=status)
    return render(request, "cases/case_list.html", {
        "page": _paginate(request, cases), "query": query,
        "status": status, "status_choices": Case.Status.choices,
    })


@login_required
def case_create(request):
    """Show the 'new case' form (GET) or validate it and save the case (POST)."""
    form = CaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            case = create_case(user=request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Case {case.case_id} was created.")
            return redirect("case_detail", case_id=case.case_id)
    return render(request, "cases/case_form.html", {"form": form})


@login_required
def case_detail(request, case_id):
    """One case with its evidence items and the custody history of all of them."""
    case = get_object_or_404(Case.objects.select_related("created_by"), case_id=case_id)
    evidence_items = case.evidence_items.all()
    events = (CustodyEvent.objects.filter(evidence__case=case)
              .select_related("evidence", "block_record").order_by("timestamp", "id"))
    return render(request, "cases/case_detail.html", {
        "case": case, "evidence_items": evidence_items, "events": events,
    })


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
@login_required
def evidence_list(request):
    """List evidence. Supports ?q= (Evidence ID / filename), ?case= and ?status=."""
    items = Evidence.objects.select_related("case", "registered_by")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    case_id = request.GET.get("case", "")
    if query:
        items = items.filter(Q(evidence_id__icontains=query) | Q(original_filename__icontains=query))
    if status in Evidence.Status.values:
        items = items.filter(status=status)
    if case_id:
        items = items.filter(case__case_id=case_id)
    return render(request, "evidence/evidence_list.html", {
        "page": _paginate(request, items), "query": query, "status": status,
        "case_id": case_id, "status_choices": Evidence.Status.choices,
        "cases": Case.objects.order_by("case_id"),
    })


@login_required
def evidence_register(request):
    """Upload and register a new evidence file (hash + first custody event + block)."""
    initial = {"case": Case.objects.filter(case_id=request.GET.get("case", "")).first()}
    form = EvidenceRegistrationForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            evidence = register_evidence(
                case=form.cleaned_data["case"],
                uploaded_file=form.cleaned_data["evidence_file"],
                notes=form.cleaned_data["notes"],
                user=request.user,
                handler_name=form.cleaned_data["handler_name"],
            )
        except LedgerInvalidError as error:
            messages.error(request, f"Evidence was NOT registered. {error}")
        except (ValidationError, IntegrityError, OSError) as error:
            form.add_error(None, getattr(error, "messages", [str(error)]))
        else:
            messages.success(
                request, f"Evidence {evidence.evidence_id} was registered and its first "
                         "custody block was created."
            )
            return redirect("evidence_detail", evidence_id=evidence.evidence_id)
    return render(request, "evidence/evidence_form.html", {"form": form})


@login_required
def evidence_detail(request, evidence_id):
    """Details of one evidence item, with its custody events and latest verification."""
    evidence = get_object_or_404(Evidence.objects.select_related("case", "registered_by"),
                                 evidence_id=evidence_id)
    events = evidence.custody_events.select_related("block_record")
    latest_verification = evidence.verification_records.first()
    return render(request, "evidence/evidence_detail.html", {
        "evidence": evidence, "events": events,
        "latest_verification": latest_verification,
        "verification_count": evidence.verification_records.count(),
    })


# ---------------------------------------------------------------------------
# Chain of custody
# ---------------------------------------------------------------------------
@login_required
def custody_history(request, evidence_id):
    """The complete chain of custody of one evidence item, oldest event first."""
    evidence = get_object_or_404(Evidence.objects.select_related("case"), evidence_id=evidence_id)
    events = evidence.custody_events.select_related("block_record", "recorded_by")
    return render(request, "evidence/custody_history.html", {"evidence": evidence, "events": events})


@login_required
def custody_add(request):
    """Record a custody event (form) and create its blockchain block."""
    initial = {"evidence": request.GET.get("evidence", "")}
    form = CustodyEventForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            event = add_custody_event(
                evidence=data["evidence"], action_type=data["action_type"], user=request.user,
                handler_name=data["handler_name"], from_party=data["from_party"],
                to_party=data["to_party"], remarks=data["remarks"],
            )
        except LedgerInvalidError as error:
            messages.error(request, f"The event was NOT recorded. {error}")
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            messages.error(request, "The event was NOT recorded because of a database conflict. Please try again.")
        else:
            messages.success(
                request, f"Custody event recorded in block #{event.block_record.block_index}."
            )
            return redirect("custody_history", evidence_id=event.evidence.evidence_id)
    return render(request, "evidence/custody_form.html", {"form": form})
