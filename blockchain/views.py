"""views.py - the blockchain ledger page and the safe tamper demonstration."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .demo import SCENARIOS, run_tamper_demo
from .services import get_ledger_rows


@login_required
def ledger(request):
    """Show every block and the validation status of the stored chain.

    The chain is re-validated each time this page loads: hashes are recalculated from
    the stored block data (never trusted), links are checked, and the blocks are
    cross-checked against the database. Nothing is repaired or rewritten.
    """
    rows, result = get_ledger_rows()
    page = Paginator(rows, 20).get_page(request.GET.get("page"))
    return render(request, "blockchain/ledger.html", {"page": page, "result": result})


@login_required
def tamper_demo(request):
    """Safe demonstration of tamper detection on an in-memory SYNTHETIC chain.

    It needs an explicit confirmation tick-box (POST) before it runs, and it never
    touches real evidence or the real ledger.
    """
    demo = None
    error = ""
    if request.method == "POST":
        if request.POST.get("confirm") != "yes":
            error = "Please tick the confirmation box to run the demonstration."
        else:
            try:
                demo = run_tamper_demo(
                    scenario=request.POST.get("scenario", "edit_data"),
                    block_index=int(request.POST.get("block_index", "2")),
                )
            except ValueError as problem:
                error = str(problem)
    return render(request, "blockchain/tamper_demo.html", {
        "demo": demo, "error": error, "scenarios": SCENARIOS.items(),
    })
