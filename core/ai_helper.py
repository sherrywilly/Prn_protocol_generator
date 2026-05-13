import os
import json
import logging

logger = logging.getLogger(__name__)


def _build_route_specific_guidance(form, route_of_administration):
    combined = f"{form} {route_of_administration}".lower()

    if any(term in combined for term in ('cream', 'ointment', 'gel', 'lotion', 'topical', 'patch')):
        return (
            "This is a topical preparation. Do not mention taking with food, taking with water, swallowing, "
            "chewing, crushing, or other oral administration advice. Focus on where to apply it, how much to apply, "
            "skin checks, handwashing, gloves if appropriate, and avoiding broken or irritated skin unless prescribed."
        )

    if any(term in combined for term in ('eye', 'ophthalmic', 'ear', 'otic', 'nasal', 'spray', 'drop', 'drops')):
        return (
            "This is not an oral preparation. Do not mention taking with food or swallowing. Focus on the correct "
            "site of administration, hygiene, positioning, and avoiding contamination of the applicator or dropper."
        )

    if any(term in combined for term in ('inhaled', 'inhaler', 'nebuliser', 'nebule')):
        return (
            "This is an inhaled preparation. Do not mention taking with food. Focus on inhalation technique, "
            "breathing/response monitoring, and when staff should escalate if symptoms persist or worsen."
        )

    return (
        "Only include advice that matches the stated form and route of administration. If the route is non-oral, "
        "do not include oral advice such as taking with food or water."
    )


def _first_name_or_default(resident_first_name):
    if not resident_first_name:
        return 'the resident'
    return resident_first_name.strip().split()[0] or 'the resident'


def get_ai_protocol_suggestions(
    medicine_name,
    form='',
    route_of_administration='',
    resident_first_name='',
    resident_mental_capacity='',
    resident_medical_conditions='',
    medication_instruction='',
):
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        return {}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
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

If a real first name is available, use only that first name. If not, use "the resident".
Use resident medical conditions and mental-capacity context to make advice appropriate and practical for this medicine.
If conditions or instructions are provided, adapt the output so the points clearly link to those details.
Keep points concise, action-oriented, and suitable for care-home staff handover notes.

Please provide the following information in JSON format:
{{
  "capacity_statement": "A statement about whether the resident can request medication or if staff need to monitor for symptoms, including that capacity can change and should be reviewed regularly",
  "reason_for_administration": "Detailed description of the condition being treated, signs and symptoms, expected outcome",
  "special_instructions": ["instruction 1", "instruction 2", "instruction 3"],
  "additional_information": ["info 1", "info 2", "info 3"]
}}

Be specific to the medication {medicine_name}. Use clinical but accessible language appropriate for care home staff."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        logger.exception("AI suggestion failed for medicine: %s", medicine_name)
        return {}
