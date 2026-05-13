import json
import os
import logging

logger = logging.getLogger(__name__)


def _build_route_specific_guidance(form, route_of_administration):
    combined = f"{form} {route_of_administration}".lower()

    if any(term in combined for term in ('cream', 'ointment', 'gel', 'lotion', 'topical', 'patch')):
        return (
            'This is a topical preparation. Do not mention taking with food, taking with water, swallowing, '
            'chewing, crushing, or other oral administration advice. Focus on where to apply it, how much to apply, '
            'skin checks, handwashing, gloves if appropriate, and avoiding broken or irritated skin unless prescribed.'
        )

    if any(term in combined for term in ('eye', 'ophthalmic', 'ear', 'otic', 'nasal', 'spray', 'drop', 'drops')):
        return (
            'This is not an oral preparation. Do not mention taking with food or swallowing. Focus on the correct '
            'site of administration, hygiene, positioning, and avoiding contamination of the applicator or dropper.'
        )

    if any(term in combined for term in ('inhaled', 'inhaler', 'nebuliser', 'nebule')):
        return (
            'This is an inhaled preparation. Do not mention taking with food. Focus on inhalation technique, '
            'breathing/response monitoring, and when staff should escalate if symptoms persist or worsen.'
        )

    return (
        'Only include advice that matches the stated form and route of administration. If the route is non-oral, '
        'do not include oral advice such as taking with food or water.'
    )


def _first_name_or_default(resident_first_name):
    if not resident_first_name:
        return 'the resident'
    return resident_first_name.strip().split()[0] or 'the resident'


def _get_openai_client():
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def get_ai_protocol_suggestions(
    medicine_name,
    form='',
    route_of_administration='',
    resident_first_name='',
    resident_mental_capacity='',
    resident_medical_conditions='',
    medication_instruction='',
):
    client = _get_openai_client()
    if client is None:
        return {}

    try:
        route_guidance = _build_route_specific_guidance(form, route_of_administration)
        resident_reference = _first_name_or_default(resident_first_name)
        prompt = f"""You are a clinical pharmacist assistant helping care home staff fill in a PRN (Pro Re Nata / as needed) medication protocol form.
Do not request, use, or infer any personally identifiable resident information.

Medicine: {medicine_name}
Form: {form or 'Not provided'}
Route of administration: {route_of_administration or 'Not provided'}
Resident reference to use in the wording: {resident_reference}
Resident mental capacity: {resident_mental_capacity or 'Not provided'}
Resident medical conditions: {resident_medical_conditions or 'Not provided'}
Medication instruction from staff: {medication_instruction or 'Not provided'}

If a real first name is available, use only that first name. If not, use \"the resident\".
Use resident medical conditions and mental-capacity context to make advice appropriate and practical for this medicine.
If conditions or instructions are provided, adapt the output so the points clearly link to those details.
Keep points concise, action-oriented, and suitable for care-home staff handover notes.
{route_guidance}

Please provide the following information in JSON format:
{{
  \"capacity_statement\": \"A statement about whether the resident can request medication or if staff need to monitor for symptoms, including that capacity can change and should be reviewed regularly\",
  \"reason_for_administration\": \"Detailed description of the condition being treated, signs and symptoms, expected outcome\",
  \"special_instructions\": [\"instruction 1\", \"instruction 2\", \"instruction 3\"],
  \"additional_information\": [\"info 1\", \"info 2\", \"info 3\"]
}}

Be specific to the medication {medicine_name}. Use clinical but accessible language appropriate for care home staff."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        logger.exception('AI suggestion failed for medicine: %s', medicine_name)
        return {}


def _fallback_resident_profile_assistance(profile_data):
    missing_information = []
    for key, label in (
        ('medical_conditions', 'Medical conditions'),
        ('allergies', 'Allergies'),
        ('medication_alerts', 'Medication alerts'),
        ('gp_name', 'GP name'),
        ('pharmacy_name', 'Pharmacy name'),
        ('emergency_contact_name', 'Emergency contact name'),
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
        'care_summary': profile_data.get('care_summary', '').strip() or 'Resident MAR summary pending staff completion. Include key conditions, allergy status, monitoring triggers, and contact escalation points.',
        'mar_front_page_text': profile_data.get('mar_front_page_text', '').strip() or 'AI-generated draft: verify all resident identifiers, allergy status, medication alerts, monitoring requirements, and safeguarding details before this MAR profile is saved or printed.',
        'legal_safeguarding_information': legal_info or 'Confirm consent, capacity, best-interest decisions, safeguarding alerts, and any restrictions relevant to medicine administration before use.',
    }

    concise_summary = generated_fields['care_summary']
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
            'emergency_contact_available': bool(profile_data.get('emergency_contact_name')),
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
    \"care_summary\": \"...\",
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
