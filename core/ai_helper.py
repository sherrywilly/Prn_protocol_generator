import json
import os
import logging

logger = logging.getLogger(__name__)


def _get_openai_client():
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def _fallback_resident_profile_assistance(profile_data):
    missing_information = []
    for key, label in (
        ('medical_conditions', 'Medical conditions'),
        ('allergies', 'Allergies'),
        ('medication_alerts', 'Medication alerts'),
        ('gp_name', 'GP name'),
        ('pharmacy_name', 'Pharmacy name'),
        ('monitoring_requirements', 'Monitoring requirements'),
        ('administration_preferences', 'Administration preferences'),
        ('legal_safeguarding_information', 'Legal / safeguarding information'),
    ):
        if not (profile_data.get(key) or '').strip():
            missing_information.append(label)

    medical_conditions = profile_data.get('medical_conditions', '').strip()
    allergies = profile_data.get('allergies', '').strip()
    medication_alerts = profile_data.get('medication_alerts', '').strip()
    monitoring_requirements = profile_data.get('monitoring_requirements', '').strip()
    administration_preferences = profile_data.get('administration_preferences', '').strip()
    legal_info = profile_data.get('legal_safeguarding_information', '').strip()

    inconsistencies = []
    if allergies and 'no known allergies' in allergies.lower() and len([line for line in allergies.splitlines() if line.strip()]) > 1:
        inconsistencies.append('Allergy details conflict with “No known allergies”.')
    if 'nkda' in medication_alerts.lower() and allergies:
        inconsistencies.append('Medication alerts mention NKDA while allergy details are recorded.')

    generated_fields = {
        'monitoring_requirements': monitoring_requirements or 'Record observations before and after administration where clinically indicated, and document any escalation triggers clearly.',
        'administration_preferences': administration_preferences or 'Use clear, calm explanations, offer fluids if safe, and record any resident preferences or refusals at the point of administration.',
        'mar_front_page_text': profile_data.get('mar_front_page_text', '').strip() or 'AI-generated draft: verify all resident identifiers, allergy status, medication alerts, monitoring requirements, and safeguarding details before this MAR profile is saved or printed.',
        'legal_safeguarding_information': legal_info or 'Confirm consent, capacity, best-interest decisions, safeguarding alerts, and any restrictions relevant to medicine administration before use.',
    }

    concise_summary = generated_fields['mar_front_page_text']
    if medical_conditions:
        concise_summary = f'Key conditions: {medical_conditions.splitlines()[0]}. {concise_summary}'
    if allergies:
        concise_summary += f' Allergy status: {allergies.splitlines()[0]}.'

    return {
        'label': 'AI-generated suggestions - staff review and approval required before saving.',
        'generated_fields': generated_fields,
        'missing_information': missing_information,
        'inconsistencies': inconsistencies,
        'summary': concise_summary,
    }


def get_ai_resident_profile_assistance(profile_data):
    fallback_payload = _fallback_resident_profile_assistance(profile_data)
    client = _get_openai_client()
    if client is None:
        return fallback_payload

    try:
        age = profile_data.get('age') or 'Unknown'
        sanitized_context = {
            'age': age,
            'medical_conditions': profile_data.get('medical_conditions', ''),
            'allergies': profile_data.get('allergies', ''),
            'medication_alerts': profile_data.get('medication_alerts', ''),
            'monitoring_requirements': profile_data.get('monitoring_requirements', ''),
            'administration_preferences': profile_data.get('administration_preferences', ''),
            'legal_safeguarding_information': profile_data.get('legal_safeguarding_information', ''),
            'mental_capacity': profile_data.get('mental_capacity', ''),
            'pharmacy_available': bool(profile_data.get('pharmacy_name')),
            'gp_available': bool(profile_data.get('gp_name')),
        }
        prompt = f"""You are assisting UK care-home staff with a MAR resident profile.
Use only the provided facts. Never fabricate medical information, diagnoses, contacts, allergies, or medication details.
Do not request or include personally identifiable information such as resident name, NHS number, date of birth, room number, GP contact numbers, or family contact numbers.
All suggestions must be clearly suitable for staff review and must require human approval before saving.
Only flag direct contradictions or obviously missing clinical/admin details. If unsure, return an empty list for inconsistencies.

Sanitised profile context:
{json.dumps(sanitized_context, indent=2)}

Return JSON with this shape:
{{
  \"label\": \"AI-generated suggestions - staff review and approval required before saving.\",
  \"generated_fields\": {{
    \"monitoring_requirements\": \"...\",
    \"administration_preferences\": \"...\",
    \"legal_safeguarding_information\": \"...\",
    \"mar_front_page_text\": \"...\"
  }},
  \"missing_information\": [\"...\"],
  \"inconsistencies\": [\"...\"],
  \"summary\": \"Concise resident summary for MAR front page\"
}}
"""
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            temperature=0.2,
        )
        payload = json.loads(response.choices[0].message.content)
        payload['missing_information'] = payload.get('missing_information') or fallback_payload['missing_information']
        payload['inconsistencies'] = payload.get('inconsistencies') or fallback_payload['inconsistencies']
        payload['label'] = 'AI-generated suggestions - staff review and approval required before saving.'
        return payload
    except Exception:
        logger.exception('Resident profile AI suggestion failed.')
        return fallback_payload
