"""Interactive local setup; no public registration or default credentials."""
from getpass import getpass
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from studio_os.operations.models import Membership, Organization


class Command(BaseCommand):
    help = "Create an isolated local studio and owner account (prompts for password)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--studio", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "studio_os.config.settings" or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("This command only supports the isolated Studio.OS SQLite settings.")
        username = options["username"].strip()
        studio = options["studio"].strip()
        if not username or len(username) > 150 or not studio or len(studio) > 180:
            raise CommandError("Provide a valid username and studio name.")
        if get_user_model().objects.filter(username=username).exists():
            raise CommandError("Username already exists; no account or membership was changed.")
        password = getpass("New owner password: ")
        if len(password) < 12:
            raise CommandError("Use a password with at least 12 characters.")
        if password != getpass("Confirm password: "):
            raise CommandError("Passwords did not match.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages))
        user = get_user_model().objects.create_user(username=username, password=password)
        org = Organization.objects.create(name=studio)
        Membership.objects.create(user=user, organization=org, role=Membership.Role.OWNER)
        self.stdout.write(self.style.SUCCESS("Studio and owner account created. Sign in through the local workspace."))
