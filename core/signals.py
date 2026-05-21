from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


ROLE_PERMISSIONS = {
    'Care Staff': [
        'add_resident',
        'change_resident',
        'view_resident',
    ],
    'Clinical Reviewer': [
        'view_resident',
        'change_resident',
        'view_auditlog',
    ],
    'Portal Admin': [
        'add_resident',
        'change_resident',
        'delete_resident',
        'view_resident',
        'view_auditlog',
    ],
}


@receiver(post_migrate)
def ensure_role_groups(sender, **kwargs):
    if sender.name != 'core':
        return

    app_label = 'core'
    models = ['resident', 'auditlog']
    permission_cache = {}
    for model_name in models:
        for permission in Permission.objects.filter(content_type__app_label=app_label, content_type__model=model_name):
            permission_cache[permission.codename] = permission

    for group_name, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(
            [permission_cache[codename] for codename in codenames if codename in permission_cache]
        )
