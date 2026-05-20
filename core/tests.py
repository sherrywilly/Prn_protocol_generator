import io
import json
import zipfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import AuditLog, PRNProtocol, Resident


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
            care_summary='Resident requires clear explanations and pain monitoring.',
            mar_front_page_text='Check allergy status and monitor pain response after PRN administration.',
        )


class ResidentModelTest(AuthenticatedPortalTestCase):
    def test_resident_str(self):
        self.assertEqual(str(self.resident), 'Jane Smith (Room 7)')

    def test_multiline_helpers(self):
        self.resident.allergies = 'Penicillin\nLatex'
        self.assertEqual(self.resident.get_allergies_list(), ['Penicillin', 'Latex'])

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
            'care_summary': 'Resident requires blood glucose monitoring.',
            'mar_front_page_text': 'Verify allergy status and diabetic monitoring needs.',
        })
        self.assertEqual(Resident.objects.count(), 2)
        new = Resident.objects.get(name='New Resident')
        self.assertRedirects(response, reverse('resident_detail', args=[new.pk]))
        self.assertTrue(AuditLog.objects.filter(action='create', entity_type='Resident', entity_id=str(new.pk)).exists())

    def test_resident_mark_reviewed(self):
        response = self.client.post(reverse('resident_mark_reviewed', args=[self.resident.pk]))
        self.assertRedirects(response, reverse('resident_detail', args=[self.resident.pk]))
        self.resident.refresh_from_db()
        self.assertEqual(self.resident.review_status, Resident.REVIEW_STATUS_REVIEWED)
        self.assertEqual(self.resident.reviewed_by, self.user)

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


class PRNProtocolModelTest(AuthenticatedPortalTestCase):
    def setUp(self):
        super().setUp()
        self.protocol = PRNProtocol.objects.create(
            resident=self.resident,
            medicine_name='Paracetamol',
            form='Tablets',
            strength='500mg',
            route_of_administration='Oral',
            dose_and_frequency='1-2 tablets as required',
            min_time_interval='4 hours',
            max_dose_24h='8 tablets',
            medication_instruction='Use only when pain is reported and document the dose given.',
            capacity_statement='Staff must monitor for signs of pain.',
            reason_for_administration='For relief of mild to moderate pain.',
            special_instructions='Take with water\nDo not crush tablets',
            additional_information='Watch for allergic reactions\nReport if pain persists',
        )

    def test_protocol_str(self):
        self.assertEqual(str(self.protocol), 'Paracetamol - Jane Smith')

    def test_get_special_instructions_list(self):
        items = self.protocol.get_special_instructions_list()
        self.assertEqual(len(items), 2)
        self.assertIn('Take with water', items)

    def test_get_additional_information_list(self):
        items = self.protocol.get_additional_information_list()
        self.assertEqual(len(items), 2)

    def test_protocol_detail_view(self):
        response = self.client.get(reverse('protocol_detail', args=[self.protocol.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paracetamol')

    def test_protocol_create_view_get(self):
        response = self.client.get(reverse('protocol_create', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)

    def test_protocol_create_view_post(self):
        response = self.client.post(
            reverse('protocol_create', args=[self.resident.pk]),
            {
                'medicine_name': 'Ibuprofen',
                'form': 'Tablets',
                'strength': '400mg',
                'route_of_administration': 'Oral',
                'medication_instruction': 'Give only if resident asks for it.',
                'dose_and_frequency': '1 tablet as required',
                'min_time_interval': '6 hours',
                'max_dose_24h': '3 tablets',
                'capacity_statement': 'Resident can request.',
                'reason_for_administration': 'For pain relief.',
            },
        )
        self.assertEqual(self.resident.protocols.count(), 2)
        self.assertEqual(response.status_code, 302)

    def test_protocol_autofill_by_medicine_returns_latest_protocol_data(self):
        PRNProtocol.objects.create(
            resident=self.resident,
            medicine_name='Paracetamol',
            form='Capsules',
            strength='650mg',
            route_of_administration='Oral',
            dose_and_frequency='1 capsule when needed',
            min_time_interval='6 hours',
            max_dose_24h='4 capsules',
            medication_instruction='Use only for severe pain.',
            capacity_statement='Prompt resident to describe pain before giving dose.',
            reason_for_administration='For short-term severe pain episodes.',
            special_instructions='Take with water',
            additional_information='Escalate if pain does not settle',
        )

        response = self.client.get(reverse('protocol_autofill_by_medicine'), {'medicine_name': 'paracetamol'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['found'])
        self.assertEqual(payload['data']['form'], 'Capsules')
        self.assertEqual(payload['data']['strength'], '650mg')
        self.assertEqual(payload['data']['medication_instruction'], 'Use only for severe pain.')
        self.assertNotIn('capacity_statement', payload['data'])

    def test_protocol_autofill_by_medicine_not_found(self):
        response = self.client.get(reverse('protocol_autofill_by_medicine'), {'medicine_name': 'Unknown Medicine'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['found'])
        self.assertEqual(payload['data'], {})

    def test_protocol_pdf_view(self):
        response = self.client.get(reverse('protocol_pdf', args=[self.protocol.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_protocol_docx_view(self):
        response = self.client.get(reverse('protocol_docx', args=[self.protocol.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertIn('.docx', response['Content-Disposition'])
        document_xml = zipfile.ZipFile(io.BytesIO(response.content)).read('word/document.xml').decode('utf-8')
        self.assertNotIn('mental_capacity', document_xml)
        self.assertNotIn('medical_conditions', document_xml)

    def test_ai_suggest_endpoint_no_key(self):
        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({'medicine_name': 'Paracetamol'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

    def test_ai_suggest_missing_medicine_name(self):
        response = self.client.post(reverse('ai_suggest'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_ai_suggest_ignores_resident_details(self):
        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({
                'medicine_name': 'Paracetamol',
                'resident_first_name': 'Jane',
                'resident_mental_capacity': 'Has capacity',
                'medication_instruction': 'Use if needed',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    @patch('core.views.get_ai_protocol_suggestions')
    def test_ai_suggest_passes_form_and_route_context(self, mock_get_ai_protocol_suggestions):
        mock_get_ai_protocol_suggestions.return_value = {}

        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({
                'medicine_name': 'Hydromol',
                'form': 'Cream',
                'route_of_administration': 'Topical',
                'resident_first_name': 'Jane',
                'resident_mental_capacity': 'Has capacity',
                'medication_instruction': 'Apply sparingly',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        mock_get_ai_protocol_suggestions.assert_called_once_with(
            'Hydromol',
            form='Cream',
            route_of_administration='Topical',
            resident_first_name='Jane',
            resident_mental_capacity='Has capacity',
            resident_medical_conditions='',
            medication_instruction='Apply sparingly',
        )

    @patch('core.views.get_ai_protocol_suggestions')
    def test_ai_suggest_uses_first_name_context(self, mock_get_ai_protocol_suggestions):
        mock_get_ai_protocol_suggestions.return_value = {}

        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({'medicine_name': 'Ibuprofen', 'resident_first_name': 'Jane Smith'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        mock_get_ai_protocol_suggestions.assert_called_once_with(
            'Ibuprofen',
            form='',
            route_of_administration='',
            resident_first_name='Jane Smith',
            resident_mental_capacity='',
            resident_medical_conditions='',
            medication_instruction='',
        )

    @patch('core.views.get_ai_protocol_suggestions')
    def test_ai_suggest_passes_medical_conditions(self, mock_get_ai_protocol_suggestions):
        mock_get_ai_protocol_suggestions.return_value = {}

        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({
                'medicine_name': 'Paracetamol',
                'resident_medical_conditions': 'Arthritis\nChronic pain',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        mock_get_ai_protocol_suggestions.assert_called_once_with(
            'Paracetamol',
            form='',
            route_of_administration='',
            resident_first_name='',
            resident_mental_capacity='',
            resident_medical_conditions='Arthritis\nChronic pain',
            medication_instruction='',
        )
