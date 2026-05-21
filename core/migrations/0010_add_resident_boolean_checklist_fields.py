from django.db import migrations, models



def _contains_any(value, *terms):
    text = (value or '').lower()
    return any(term in text for term in terms)



def populate_boolean_fields(apps, schema_editor):
    Resident = apps.get_model('core', 'Resident')
    for resident in Resident.objects.all():
        resident.dnar_in_place = _contains_any(resident.legal_safeguarding_information, 'dnar', 'dnacpr') or _contains_any(
            resident.medical_conditions, 'dnar', 'dnacpr'
        )
        resident.is_diabetic = _contains_any(resident.medical_conditions, 'diabet')
        resident.has_peg = _contains_any(resident.medical_conditions, 'peg')
        resident.self_medicates = _contains_any(resident.administration_preferences, 'self med', 'self-med')
        resident.risk_assessment_in_place = bool((resident.legal_safeguarding_information or '').strip())
        resident.has_swallowing_difficulties = _contains_any(resident.medical_conditions, 'swallow', 'dysphagia')
        resident.on_oxygen = _contains_any(resident.medical_conditions, 'oxygen')
        resident.can_take_medication_orally = _contains_any(resident.mar_front_page_text, 'oral', 'orally')
        resident.requires_inhaler = _contains_any(resident.medical_conditions, 'inhaler') or _contains_any(
            resident.medication_alerts, 'inhaler'
        )
        resident.has_medication_capacity = bool((resident.mental_capacity or '').strip()) and not _contains_any(
            resident.mental_capacity, 'lack', 'no '
        )
        resident.has_parkinsons = _contains_any(resident.medical_conditions, 'parkinson')
        resident.mca_in_place = bool((resident.mental_capacity or '').strip())
        resident.has_dementia = _contains_any(resident.medical_conditions, 'dementia')
        resident.on_blood_thinning_medication = _contains_any(resident.medication_alerts, 'blood thinning', 'anticoag')
        resident.requires_pulse_or_bp_before_medication = _contains_any(
            resident.monitoring_requirements, 'pulse', 'blood pressure', 'bp'
        )
        resident.save(
            update_fields=[
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
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_remove_resident_non_pdf_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='resident',
            name='can_take_medication_orally',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='dnar_in_place',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='has_dementia',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='has_medication_capacity',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='has_parkinsons',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='has_peg',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='has_swallowing_difficulties',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='is_diabetic',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='mca_in_place',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='on_blood_thinning_medication',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='on_oxygen',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='requires_inhaler',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='requires_pulse_or_bp_before_medication',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='risk_assessment_in_place',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='resident',
            name='self_medicates',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(populate_boolean_fields, migrations.RunPython.noop),
    ]
