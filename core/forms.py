from django import forms
from .models import Resident, PRNProtocol


class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = ['name', 'room_number', 'date_of_birth']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PRNProtocolForm(forms.ModelForm):
    class Meta:
        model = PRNProtocol
        exclude = ['resident', 'created_at', 'updated_at']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_medicine_name'}),
            'form': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. tablets, capsules, powder sachets'}),
            'strength': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500mg'}),
            'route_of_administration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. oral, topical'}),
            'dose_and_frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-2 tablets as needed'}),
            'min_time_interval': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 4 hours'}),
            'max_dose_24h': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 8 tablets'}),
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
