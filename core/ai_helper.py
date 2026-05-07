import os
import json
import logging

logger = logging.getLogger(__name__)


def get_ai_protocol_suggestions(medicine_name):
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        return {}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = f"""You are a clinical pharmacist assistant helping care home staff fill in a PRN (Pro Re Nata / as needed) medication protocol form.
Do not request, use, or infer any personally identifiable resident information.

Medicine: {medicine_name}
Resident context: generic care-home resident (no personal details shared)

Please provide the following information in JSON format:
{{
  "capacity_statement": "A statement about whether the resident can request medication or if staff need to monitor for symptoms",
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
