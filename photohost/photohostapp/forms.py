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
        (90, _("3 months")),
        (180, _("6 months")),
    )

    lifetime_days = forms.TypedChoiceField(
        choices=LIFETIME_CHOICES,
        coerce=int,
        initial=7,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Deletion time"),
    )

    set_password = forms.BooleanField(
        required=False,
        label="Set password"
    )
    multi_upload = forms.BooleanField(
        required=False,
        initial=False,
        label="Multi-upload",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "id_multi_upload",
            }
        ),
    )

    section_password = forms.CharField(
        required=False,
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter section password",
                "autocomplete": "new-password",
                "id": "sectionPassword",
            }
        )
    )
    class Meta:
        model = Section
        fields = ["keep_original_filenames", "lifetime_days"]

    def clean(self):
        cleaned_data = super().clean()

        set_password = cleaned_data.get("set_password")
        password = cleaned_data.get("section_password")

        if set_password and not password:
            self.add_error(
                "section_password",
                "Please enter a password."
            )

        return cleaned_data

    def save(self, commit=True):
        section = super().save(commit=False)

        if self.cleaned_data.get("set_password"):
            section.set_section_password(
                self.cleaned_data["section_password"]
            )
        else:
            section.set_section_password("")

        if commit:
            section.save()
            self.save_m2m()

        return section




class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultiUploadForm(forms.Form):
    files = forms.FileField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=True
    )