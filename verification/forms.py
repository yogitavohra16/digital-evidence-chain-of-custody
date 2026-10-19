"""forms.py - the evidence picker on the verification page."""
from django import forms

from evidence.models import Evidence


class VerifyEvidenceForm(forms.Form):
    """Choose which registered evidence item to verify."""

    evidence = forms.ModelChoiceField(
        queryset=Evidence.objects.none(), to_field_name="evidence_id",
        label="Evidence item", empty_label="Select evidence",
    )

    def __init__(self, *args, **kwargs):
        """Fill the drop-down with all registered evidence."""
        super().__init__(*args, **kwargs)
        self.fields["evidence"].queryset = Evidence.objects.select_related("case").order_by("evidence_id")
        self.fields["evidence"].label_from_instance = (
            lambda obj: f"{obj.evidence_id} - {obj.original_filename}"
        )
