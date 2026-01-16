from django import forms
from .models import Section
from django.utils.translation import gettext_lazy as _
class ImageUploadForm(forms.Form):
    image = forms.ImageField()


class SectionCreateForm(forms.ModelForm):
    LIFETIME_CHOICES = (
        (1, _("1 day")),
        (3, _("3 days")),
        (7, _("1 week")),
        (14, _("2 weeks")),
        (30, _("1 month")),
        (60, _("2 months")),
    )

    lifetime_days = forms.TypedChoiceField(
        choices=LIFETIME_CHOICES,
        coerce=int,
        initial=7,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Deletion time"),
    )

    class Meta:
        model = Section
        fields = ["keep_original_filenames", "lifetime_days"]


class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultiUploadForm(forms.Form):
    files = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=True
    )