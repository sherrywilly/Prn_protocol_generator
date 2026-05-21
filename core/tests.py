import io
import json
import zipfile
from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ResidentForm
from .models import AuditLog, Resident


User = get_user_model()


class PortalAccessTest(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('resident_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('login'))


class AuthenticatedPortalTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser('portaladmin', 'admin@example.com', 'password123')
        self.client.force_login(self.user)
        self.resident = Resident.objects.create(
            name='Jane Smith',
            room_number='7',
            date_of_birth=date(1945, 3, 20),
            medical_conditions='Arthritis',
            allergies='Penicillin',
            medication_alerts='Monitor for gastric irritation',
            monitoring_requirements='Document pain score before and after administration',
            administration_preferences='Explain medicines slowly and allow time for questions',
            legal_safeguarding_information='Best-interest discussion recorded in care plan',
            mar_front_page_text='Check allergy status and monitor pain response after medication administration.',
        )


class ResidentModelTest(AuthenticatedPortalTestCase):
    def test_resident_str(self):
        self.assertEqual(str(self.resident), 'Jane Smith (Room 7)')

    def test_multiline_helpers(self):
        self.resident.allergies = 'Penicillin\nLatex'
        self.assertEqual(self.resident.get_allergies_list(), ['Penicillin', 'Latex'])
        self.resident.medical_conditions = 'Arthritis\nHypertension'
        self.assertEqual(self.resident.get_medical_conditions_list(), ['Arthritis', 'Hypertension'])

    def test_resident_form_normalizes_multivalue_fields(self):
        form = ResidentForm(data={
            'name': 'New Resident',
            'room_number': '5',
            'residential_or_nursing': 'residential',
            'date_of_birth': '1940-06-01',
            'nhs_number': '1234567890',
            'medical_conditions': 'Diabetes, Hypertension; COPD',
            'allergies': 'Penicillin, Latex',
            'gp_name': 'Dr Jones',
            'gp_surgery': 'Health Centre',
            'gp_contact': '01234 567890',
            'pharmacy_name': 'Community Pharmacy',
            'pharmacy_contact': '01234 111222',
            'next_of_kin': 'Jane Relative',
            'next_of_kin_contact': '01234 333444',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['medical_conditions'], 'Diabetes\nHypertension\nCOPD')
        self.assertEqual(form.cleaned_data['allergies'], 'Penicillin\nLatex')

    def test_resident_list_view(self):
        response = self.client.get(reverse('resident_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MAR resident dashboard')
        self.assertContains(response, 'Jane Smith')

    def test_resident_detail_view(self):
        response = self.client.get(reverse('resident_detail', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medication alerts')
        self.assertContains(response, 'Best-interest discussion')

    def test_resident_create_view_get(self):
        response = self.client.get(reverse('resident_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create MAR resident profile')

    def test_resident_create_view_post_creates_audit_log(self):
        response = self.client.post(reverse('resident_create'), {
            'name': 'New Resident',
            'room_number': '5',
            'date_of_birth': '1940-06-01',
            'nhs_number': '1234567890',
            'mental_capacity': 'Has capacity to make day-to-day decisions.',
            'medical_conditions': 'Type 2 diabetes\nHypertension',
            'allergies': 'No known allergies',
            'medication_alerts': 'Observe for dizziness',
            'monitoring_requirements': 'Monitor blood glucose levels',
            'administration_preferences': 'Offer water with tablets',
            'legal_safeguarding_information': 'No restrictions recorded',
            'mar_front_page_text': 'Verify allergy status and diabetic monitoring needs.',
        })
        self.assertEqual(Resident.objects.count(), 2)
        new = Resident.objects.get(name='New Resident')
        self.assertRedirects(response, reverse('resident_detail', args=[new.pk]))
        self.assertTrue(AuditLog.objects.filter(action='create', entity_type='Resident', entity_id=str(new.pk)).exists())

    def test_resident_pdf_view(self):
        response = self.client.get(reverse('resident_pdf', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_resident_docx_view(self):
        response = self.client.get(reverse('resident_docx', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        document_xml = zipfile.ZipFile(io.BytesIO(response.content)).read('word/document.xml').decode('utf-8')
        self.assertIn('MAR RESIDENT PROFILE', document_xml)
        self.assertIn('Medication alerts', document_xml)
        self.assertIn('Critical Medical Alerts', document_xml)
        self.assertIn('Key Contacts', document_xml)

    def test_resident_print_view(self):
        response = self.client.get(reverse('resident_print', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MAR Resident Profile')

    def test_resident_ai_assist_returns_fallback_without_key(self):
        response = self.client.post(
            reverse('resident_ai_assist'),
            data=json.dumps({
                'medical_conditions': 'Diabetes',
                'allergies': 'Penicillin',
                'medication_alerts': 'Check for rash',
                'monitoring_requirements': '',
                'administration_preferences': '',
                'legal_safeguarding_information': '',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('generated_fields', payload)
        self.assertIn('monitoring_requirements', payload['generated_fields'])
        self.assertIn('staff review and approval required', payload['label'])

