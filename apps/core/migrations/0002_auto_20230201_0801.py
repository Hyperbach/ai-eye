from django.db import migrations

from core.enums import UserGroupType


def apply_migration(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.bulk_create([
        Group(name=UserGroupType.AIEYE_ADMINS.name),
        Group(name=UserGroupType.AIEYE_USERS.name),
    ])


def revert_migration(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(
        name__in=[
            UserGroupType.AIEYE_ADMINS.name,
            UserGroupType.AIEYE_USERS.name,
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(apply_migration, revert_migration)
    ]
