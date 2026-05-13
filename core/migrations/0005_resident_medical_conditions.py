from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_prnprotocol_medication_instruction_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='resident',
            name='medical_conditions',
            field=models.TextField(blank=True, default=''),
        ),
    ]