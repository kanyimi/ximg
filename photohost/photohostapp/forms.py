from django import forms
from .models import Section
from django.utils.translation import gettext_lazy as _
class ImageUploadForm(forms.Form):
    image = forms.ImageField()


class SectionCreateForm(forms.ModelForm):

    LIFETIME_CHOICES = (
        ("1d", _("1 day")),
        ("3d", _("3 days")),
        ("1w", _("1 week")),
        ("2w", _("2 weeks")),
        ("1m", _("1 month")),
        ("2m", _("2 months")),
    )

    lifetime = forms.ChoiceField(
        choices=LIFETIME_CHOICES,
        initial="1w",
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Deletion time")
    )

    class Meta:
        model = Section
        fields = ["keep_original_filenames"]
        labels = {
            "keep_original_filenames": _("Save original file names"),
        }
        widgets = {
            "keep_original_filenames": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            )
        }

    def clean_lifetime(self):
        """Convert lifetime codes to days"""
        mapping = {
            "1d": 1,
            "3d": 3,
            "1w": 7,
            "2w": 14,
            "1m": 30,
            "2m": 60,
        }
        value = self.cleaned_data["lifetime"]
        return mapping[value]

class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultiUploadForm(forms.Form):
    files = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=True
    )