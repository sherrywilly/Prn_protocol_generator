import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Resident, PRNProtocol


PHONE_PATTERN = re.compile(r'^[0-9+()\-\s]{7,20}$')


class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = [
            'name',
            'room_number',
            'date_of_birth',
            'photo',
            'nhs_number',
            'mental_capacity',
            'medical_conditions',
            'allergies',
            'medication_alerts',
            'gp_name',
            'gp_surgery',
            'gp_contact',
            'pharmacy_name',
            'pharmacy_contact',
            'next_of_kin',
            'next_of_kin_contact',
            'emergency_contact_name',
            'emergency_contact_relationship',
            'emergency_contact_phone',
            'monitoring_requirements',
            'administration_preferences',
            'legal_safeguarding_information',
            'care_summary',
            'mar_front_page_text',
            'care_plan_reviewed',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'care_plan_reviewed': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'nhs_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 123 456 7890'}),
            'next_of_kin': forms.TextInput(attrs={'class': 'form-control'}),
            'next_of_kin_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'gp_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gp_surgery': forms.TextInput(attrs={'class': 'form-control'}),
            'gp_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'pharmacy_name': forms.TextInput(attrs={'class': 'form-control'}),
            'pharmacy_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'mental_capacity': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3}),
            'medical_conditions': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4}),
            'allergies': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'One allergy or sensitivity per line'}),
            'medication_alerts': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 3, 'placeholder': 'Enter medication-specific alerts or contraindications'}),
            'monitoring_requirements': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'Enter each monitoring requirement on a new line'}),
            'administration_preferences': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'Enter preferred administration approaches on new lines'}),
            'legal_safeguarding_information': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'Safeguarding, consent, DOLS, or best-interest notes'}),
            'care_summary': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 4, 'placeholder': 'Concise summary for handover and MAR front sheets'}),
            'mar_front_page_text': forms.Textarea(attrs={'class': 'form-control voice-input', 'rows': 5, 'placeholder': 'Standardised MAR front-page text'}),
        }

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

    def clean_emergency_contact_phone(self):
        return self._clean_phone(self.cleaned_data.get('emergency_contact_phone'), 'Emergency contact phone')

    def clean(self):
        cleaned_data = super().clean()
        allergies = (cleaned_data.get('allergies') or '').lower()
        medication_alerts = (cleaned_data.get('medication_alerts') or '').lower()
        if 'no known allergies' in allergies and len([line for line in allergies.splitlines() if line.strip()]) > 1:
            self.add_error('allergies', 'Remove extra entries when recording “No known allergies”.')
        if 'nkda' in medication_alerts and cleaned_data.get('allergies'):
            self.add_error('medication_alerts', 'Medication alerts should not say NKDA when allergies are recorded.')
        return cleaned_data


class PRNProtocolForm(forms.ModelForm):
    class Meta:
        model = PRNProtocol
        exclude = ['resident', 'created_at', 'updated_at']
        widgets = {
            'medicine_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_medicine_name',
                'list': 'medicineSuggestions',
                'autocomplete': 'off',
            }),
            'form': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. tablets, capsules, powder sachets'}),
            'strength': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500mg'}),
            'route_of_administration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. oral, topical'}),
            'dose_and_frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-2 tablets as needed'}),
            'min_time_interval': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 4 hours'}),
            'max_dose_24h': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 8 tablets'}),
            'medication_instruction': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter medication-specific instructions to guide AI suggestions'}),
            'capacity_statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'reason_for_administration': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter each instruction on a new line'}),
            'additional_information': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter each piece of information on a new line'}),
            'gp_other': forms.TextInput(attrs={'class': 'form-control'}),
            'prepared_by_name': forms.TextInput(attrs={'class': 'form-control'}),
            'prepared_by_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'prepared_by_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'approved_by_name': forms.TextInput(attrs={'class': 'form-control'}),
            'approved_by_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'approved_by_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'review_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reviewed_by_name': forms.TextInput(attrs={'class': 'form-control'}),
            'reviewed_by_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'reviewed_by_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'checked_by_name': forms.TextInput(attrs={'class': 'form-control'}),
            'checked_by_designation': forms.TextInput(attrs={'class': 'form-control'}),
            'checked_by_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'new_review_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
