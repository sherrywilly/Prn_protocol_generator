from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_add_resident_boolean_checklist_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PRNProtocol',
        ),
    ]
