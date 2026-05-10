from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from .models import Resident, PRNProtocol


class ResidentModelTest(TestCase):
    def setUp(self):
        self.resident = Resident.objects.create(
            name='Test Resident',
            room_number='10',
            date_of_birth=date(1950, 1, 15),
        )

    def test_resident_str(self):
        self.assertEqual(str(self.resident), 'Test Resident (Room 10)')

    def test_resident_list_view(self):
        response = self.client.get(reverse('resident_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Resident')

    def test_resident_detail_view(self):
        response = self.client.get(reverse('resident_detail', args=[self.resident.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Resident')

    def test_resident_create_view_get(self):
        response = self.client.get(reverse('resident_create'))
        self.assertEqual(response.status_code, 200)

    def test_resident_create_view_post(self):
        response = self.client.post(reverse('resident_create'), {
            'name': 'New Resident',
            'room_number': '5',
            'date_of_birth': '1940-06-01',
        })
        self.assertEqual(Resident.objects.count(), 2)
        new = Resident.objects.get(name='New Resident')
        self.assertRedirects(response, reverse('resident_detail', args=[new.pk]))


class PRNProtocolModelTest(TestCase):
    def setUp(self):
        self.resident = Resident.objects.create(
            name='Jane Smith',
            room_number='7',
            date_of_birth=date(1945, 3, 20),
        )
        self.protocol = PRNProtocol.objects.create(
            resident=self.resident,
            medicine_name='Paracetamol',
            form='Tablets',
            strength='500mg',
            route_of_administration='Oral',
            dose_and_frequency='1-2 tablets as required',
            min_time_interval='4 hours',
            max_dose_24h='8 tablets',
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
        self.assertContains(response, "Resident capacity can change.")

    def test_protocol_create_view_post(self):
        response = self.client.post(
            reverse('protocol_create', args=[self.resident.pk]),
            {
                'medicine_name': 'Ibuprofen',
                'form': 'Tablets',
                'strength': '400mg',
                'route_of_administration': 'Oral',
                'dose_and_frequency': '1 tablet as required',
                'min_time_interval': '6 hours',
                'max_dose_24h': '3 tablets',
                'capacity_statement': 'Resident can request.',
                'reason_for_administration': 'For pain relief.',
            },
        )
        self.assertEqual(self.resident.protocols.count(), 2)

    def test_protocol_pdf_view(self):
        response = self.client.get(reverse('protocol_pdf', args=[self.protocol.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_ai_suggest_endpoint_no_key(self):
        """AI suggest returns empty dict when no API key is set."""
        import json
        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({'medicine_name': 'Paracetamol'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # No API key → empty dict (graceful failure)
        self.assertIsInstance(data, dict)

    def test_ai_suggest_missing_medicine_name(self):
        import json
        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_ai_suggest_ignores_resident_details(self):
        import json
        response = self.client.post(
            reverse('ai_suggest'),
            data=json.dumps({'medicine_name': 'Paracetamol', 'resident_name': 'Jane Smith'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
