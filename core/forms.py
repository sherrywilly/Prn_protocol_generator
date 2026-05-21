import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Resident


PHONE_PATTERN = re.compile(r'^[0-9+()\-\s]{7,20}$')


class ResidentForm(forms.ModelForm):
    def _normalize_multivalue_text(self, value):
        items = []
        for chunk in str(value or '').replace(';', '\n').splitlines():
            for part in chunk.split(','):
                cleaned = part.strip()
                if cleaned and cleaned not in items:
                    items.append(cleaned)
        return '\n'.join(items)

    class Meta:
        model = Resident
        fields = [
            'name',
            'room_number',
            'residential_or_nursing',
            'date_of_birth',
            'photo',
            'nhs_number',
            'medical_conditions',
            'allergies',
            'gp_name',
            'gp_surgery',
            'gp_contact',
            'pharmacy_name',
            'pharmacy_contact',
            'next_of_kin',
            'next_of_kin_contact',
            'mental_capacity',
            'medication_alerts',
            'monitoring_requirements',
            'administration_preferences',
            'legal_safeguarding_information',
            'mar_front_page_text',
            'dnar_in_place',
            'is_diabetic',
            'has_peg',
            'self_medicates',
            'risk_assessment_in_place',
            'has_swallowing_difficulties',
            'on_oxygen',
            'can_take_medication_orally',
            'requires_inhaler',
            'has_medication_capacity',
            'has_parkinsons',
            'mca_in_place',
            'has_dementia',
            'on_blood_thinning_medication',
            'requires_pulse_or_bp_before_medication',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'residential_or_nursing': forms.Select(attrs={'class': 'form-control'}),
            'nhs_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 123 456 7890'}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'gp_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gp_surgery': forms.TextInput(attrs={'class': 'form-control'}),
            'gp_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'pharmacy_name': forms.TextInput(attrs={'class': 'form-control'}),
            'pharmacy_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'mental_capacity': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'Capacity and consent context for medication decisions'}),
            'medication_alerts': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'Critical medication alerts and escalation triggers'}),
            'monitoring_requirements': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'What to monitor before/after medication'}),
            'administration_preferences': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'What level of support is needed for medication administration'}),
            'legal_safeguarding_information': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'Legal and safeguarding information relevant to medication'}),
            'mar_front_page_text': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'Additional MAR guidance shown on exports'}),
            'medical_conditions': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'Add one condition per tag or line'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'One allergy or sensitivity per line'}),
            'dnar_in_place': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_diabetic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_peg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'self_medicates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'risk_assessment_in_place': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_swallowing_difficulties': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'on_oxygen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_take_medication_orally': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_inhaler': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_medication_capacity': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_parkinsons': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mca_in_place': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_dementia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'on_blood_thinning_medication': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_pulse_or_bp_before_medication': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_medical_conditions(self):
        return self._normalize_multivalue_text(self.cleaned_data.get('medical_conditions'))

    def clean_allergies(self):
        return self._normalize_multivalue_text(self.cleaned_data.get('allergies'))

    def _clean_phone(self, value, field_name):
        value = (value or '').strip()
        if value and not PHONE_PATTERN.match(value):
            raise ValidationError(f'{field_name} must contain only digits, spaces, and common phone symbols.')
        return value

    def clean_nhs_number(self):
        value = re.sub(r'\s+', '', (self.cleaned_data.get('nhs_number') or ''))
        if value and (not value.isdigit() or len(value) != 10):
            raise ValidationError('NHS number must contain exactly 10 digits.')
        return value

    def clean_next_of_kin_contact(self):
        return self._clean_phone(self.cleaned_data.get('next_of_kin_contact'), 'Next of kin contact')

    def clean_gp_contact(self):
        return self._clean_phone(self.cleaned_data.get('gp_contact'), 'GP contact')

    def clean_pharmacy_contact(self):
        return self._clean_phone(self.cleaned_data.get('pharmacy_contact'), 'Pharmacy contact')

    def clean(self):
        cleaned_data = super().clean()
        allergies = (cleaned_data.get('allergies') or '').lower()
        medication_alerts = (cleaned_data.get('medication_alerts') or '').lower()
        if 'no known allergies' in allergies and len([line for line in allergies.splitlines() if line.strip()]) > 1:
            self.add_error('allergies', 'Remove extra entries when recording “No known allergies”.')
        if 'nkda' in medication_alerts and cleaned_data.get('allergies'):
            self.add_error('medication_alerts', 'Medication alerts should not say NKDA when allergies are recorded.')
        return cleaned_data

class ResidentImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Import file',
        help_text='Upload a .csv or .xlsx file exported from your care records system.',
        widget=forms.ClearableFileInput(
            attrs={'class': 'form-control', 'accept': '.csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
        ),
    )
