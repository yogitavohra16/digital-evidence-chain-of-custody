"""forms.py - Django forms: they draw the HTML inputs AND validate what users send.

WHAT IS A FORM?
    A Django form lists the fields we expect. When a user submits the page, Django
    runs `is_valid()`, which checks every field and our custom `clean_*` methods.
    If anything is wrong, error messages are attached to the form and shown next to
    the field. Validation happens on the SERVER, so it cannot be bypassed from the
    browser.
"""
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Case, CustodyEvent, Evidence
from .services import validate_custody_event


class CaseForm(forms.Form):
    """Form for creating a case. (The Case ID is generated automatically.)"""

    title = forms.CharField(max_length=200, label="Case title",
                            help_text="A short name, e.g. 'Laptop image review'.")
    description = forms.CharField(required=False, label="Description",
                                  widget=forms.Textarea(attrs={"rows": 4}),
                                  help_text="Background and scope of the investigation.")
    status = forms.ChoiceField(choices=Case.Status.choices, initial=Case.Status.OPEN, label="Status")


class EvidenceRegistrationForm(forms.Form):
    """Form for registering a new evidence file."""

    case = forms.ModelChoiceField(queryset=Case.objects.none(), label="Case",
                                  empty_label="Select a case")
    evidence_file = forms.FileField(label="Evidence file")
    handler_name = forms.CharField(max_length=120, label="Collected by",
                                   help_text="Person who collected / is registering this evidence.")
    notes = forms.CharField(required=False, label="Description / notes",
                            widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        """Fill the case drop-down. Closed cases are not offered for new evidence."""
        super().__init__(*args, **kwargs)
        self.fields["case"].queryset = Case.objects.exclude(status=Case.Status.CLOSED)
        allowed = ", ".join(settings.ALLOWED_EVIDENCE_EXTENSIONS)
        max_mb = settings.MAX_EVIDENCE_UPLOAD_BYTES // (1024 * 1024)
        self.fields["evidence_file"].help_text = (
            f"Maximum size {max_mb} MB. Allowed types: {allowed}."
        )

    def clean_evidence_file(self):
        """Check the file's size and extension against the settings.

        Why: limits protect the server from huge uploads, and the allow-list keeps
        executable/script files out. (Evidence files are never executed anyway.)
        """
        uploaded = self.cleaned_data["evidence_file"]
        if uploaded.size == 0:
            raise ValidationError("The file is empty (0 bytes).")
        if uploaded.size > settings.MAX_EVIDENCE_UPLOAD_BYTES:
            max_mb = settings.MAX_EVIDENCE_UPLOAD_BYTES // (1024 * 1024)
            raise ValidationError(f"The file is larger than the {max_mb} MB limit.")
        extension = Path(uploaded.name).suffix.lower().lstrip(".")
        if not extension or extension not in settings.ALLOWED_EVIDENCE_EXTENSIONS:
            raise ValidationError(
                f"File type '.{extension}' is not allowed." if extension
                else "The file must have an extension (for example .txt or .pdf)."
            )
        return uploaded


class CustodyEventForm(forms.Form):
    """Form for recording a custody event for an existing evidence item."""

    evidence = forms.ModelChoiceField(
        queryset=Evidence.objects.none(), label="Evidence", empty_label="Select evidence",
        to_field_name="evidence_id",
    )
    action_type = forms.ChoiceField(label="Action", choices=[])
    handler_name = forms.CharField(
        max_length=120, label="Performed by",
        help_text="Name of the person handling the evidence. A name alone does not "
                  "prove real-world identity.",
    )
    from_party = forms.CharField(max_length=120, required=False, label="From")
    to_party = forms.CharField(max_length=120, required=False, label="To")
    remarks = forms.CharField(label="Purpose / remarks", widget=forms.Textarea(attrs={"rows": 3}),
                              help_text="Why is this action happening? Required for every event.")

    def __init__(self, *args, **kwargs):
        """Populate drop-downs. 'Registered' is automatic, so it is not selectable."""
        super().__init__(*args, **kwargs)
        self.fields["evidence"].queryset = Evidence.objects.select_related("case")
        self.fields["evidence"].label_from_instance = (
            lambda obj: f"{obj.evidence_id} - {obj.original_filename}"
        )
        self.fields["action_type"].choices = [
            (value, label) for value, label in CustodyEvent.ActionType.choices
            if value != CustodyEvent.ActionType.REGISTERED
        ]

    def clean(self):
        """Apply the same custody rules the service layer enforces.

        Showing the problems on the form gives friendly messages; the service layer
        checks again so the rules cannot be skipped.
        """
        cleaned = super().clean()
        evidence = cleaned.get("evidence")
        action_type = cleaned.get("action_type")
        if evidence and action_type:
            try:
                validate_custody_event(
                    evidence=evidence,
                    action_type=action_type,
                    handler_name=cleaned.get("handler_name", ""),
                    from_party=cleaned.get("from_party", ""),
                    to_party=cleaned.get("to_party", ""),
                    remarks=cleaned.get("remarks", ""),
                )
            except ValidationError as error:
                raise ValidationError(error.messages)
        return cleaned
