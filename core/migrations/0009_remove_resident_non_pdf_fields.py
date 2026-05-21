from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_resident_residential_or_nursing'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resident',
            name='care_plan_reviewed',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='care_summary',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='emergency_contact_name',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='emergency_contact_phone',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='emergency_contact_relationship',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='review_status',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='reviewed_at',
        ),
        migrations.RemoveField(
            model_name='resident',
            name='reviewed_by',
        ),
    ]
