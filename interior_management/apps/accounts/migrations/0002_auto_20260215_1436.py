from django.db import migrations
from django.contrib.auth import get_user_model

def create_initial_admin(apps, schema_editor):
    User = get_user_model()
    # Check if admin already exists so we don't create it twice
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@studio.os',
            password='TemporaryPassword123!', # Change this immediately after login!
            role='admin'
        )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'), # Make sure this matches your first migration name
    ]

    operations = [
        migrations.RunPython(create_initial_admin),
    ]