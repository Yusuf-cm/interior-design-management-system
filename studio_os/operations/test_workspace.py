import json
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Membership, Organization


class WorkspaceSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("workspace-owner", password="local-test-password")
        cls.other = get_user_model().objects.create_user("workspace-other")
        cls.field = get_user_model().objects.create_user("workspace-field")
        cls.org = Organization.objects.create(name="Nuru Interiors")
        cls.private = Organization.objects.create(name="Private other studio")
        Membership.objects.create(organization=cls.org, user=cls.user, role=Membership.Role.OWNER)
        Membership.objects.create(organization=cls.org, user=cls.field, role=Membership.Role.FIELD)
        Membership.objects.create(organization=cls.private, user=cls.other, role=Membership.Role.OWNER)

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def test_shell_renders_without_private_data_and_assets_are_available(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Studio.OS")
        self.assertContains(response, 'type="module"')
        self.assertNotContains(response, "Nuru Interiors")
        self.assertNotContains(response, "Private other studio")
        self.assertIn("no-store", response.headers["Cache-Control"])
        for name in ["workspace.css", "workspace.mjs", "ui-utils.mjs"]:
            self.assertTrue(finders.find("studio_os/"+name))

    def test_anonymous_bootstrap_exposes_no_company_information(self):
        response = self.client.get("/api/session/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertEqual(response.json()["organizations"], [])
        self.assertIsNone(response.json()["user"])
        self.assertTrue(response.json()["csrf_token"])

    def test_login_requires_csrf_and_rotates_session_context(self):
        bootstrap = self.client.get("/api/session/").json()
        payload = {"username": "workspace-owner", "password": "local-test-password"}
        response = self.client.post("/api/session/login/", payload, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.client.post("/api/session/login/", payload, format="json",
                                    HTTP_X_CSRFTOKEN=bootstrap["csrf_token"])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual([org["name"] for org in data["organizations"]], ["Nuru Interiors"])
        self.assertEqual(data["organizations"][0]["role"], "OWNER")
        self.assertNotEqual(data["csrf_token"], bootstrap["csrf_token"])
        self.assertNotIn("password", response.content.decode())
        self.assertTrue(response.cookies["sessionid"]["httponly"])
        self.assertEqual(response.cookies["sessionid"]["samesite"], "Lax")

    def test_logout_requires_csrf_and_removes_access(self):
        self.client.login(username="workspace-owner", password="local-test-password")
        bootstrap = self.client.get("/api/session/").json()
        self.assertEqual(self.client.post("/api/session/logout/", {}, format="json").status_code, 403)
        response = self.client.post("/api/session/logout/", {}, format="json",
                                    HTTP_X_CSRFTOKEN=bootstrap["csrf_token"])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertEqual(self.client.get("/api/leads/", HTTP_X_ORGANIZATION_ID=str(self.org.pk)).status_code, 403)

    def test_invalid_login_has_generic_error_and_no_session(self):
        token = self.client.get("/api/session/").json()["csrf_token"]
        for username in ["workspace-owner", "missing-user"]:
            response = self.client.post("/api/session/login/",
                {"username": username, "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["detail"], "Username or password is incorrect")
        self.assertFalse(self.client.get("/api/session/").json()["authenticated"])

    def test_bad_login_payload_and_disabled_account(self):
        token = self.client.get("/api/session/").json()["csrf_token"]
        self.user.is_active = False
        self.user.save()
        for payload in [[], {"username": [], "password": "test"},
                        {"username": "workspace-owner", "password": "local-test-password"}]:
            response = self.client.post("/api/session/login/", payload, format="json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)

    def test_staff_directory_is_scoped_and_field_staff_cannot_read_it(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/staff/", HTTP_X_ORGANIZATION_ID=str(self.org.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["id"] for row in response.json()}, {self.user.pk, self.field.pk})
        self.assertNotIn("password", response.content.decode())
        self.assertNotIn("email", response.content.decode())
        self.assertEqual(self.client.get("/api/staff/",
            HTTP_X_ORGANIZATION_ID=str(self.private.pk)).status_code, 403)
        self.client.force_authenticate(user=self.field)
        self.assertEqual(self.client.get("/api/staff/",
            HTTP_X_ORGANIZATION_ID=str(self.org.pk)).status_code, 403)

    def test_inactive_membership_is_absent_from_bootstrap(self):
        Membership.objects.filter(user=self.user).update(active=False)
        self.client.login(username="workspace-owner", password="local-test-password")
        self.assertTrue(self.client.get("/api/session/").json()["authenticated"])
        self.assertEqual(self.client.get("/api/session/").json()["organizations"], [])

    def test_session_authenticated_workflow_write_requires_csrf(self):
        self.client.login(username="workspace-owner", password="local-test-password")
        token = self.client.get("/api/session/").json()["csrf_token"]
        headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.pk)}
        self.assertEqual(self.client.post("/api/customers/", {"name": "Amina"}, format="json", **headers).status_code, 403)
        response = self.client.post("/api/customers/", {"name": "Amina"}, format="json",
                                    HTTP_X_CSRFTOKEN=token, **headers)
        self.assertEqual(response.status_code, 201)


class LocalWorkspaceSetupTests(TestCase):
    def test_setup_creates_owner_without_persisting_plaintext_password(self):
        from unittest.mock import patch
        from django.core.management import call_command
        with patch("studio_os.operations.management.commands.create_studio_workspace.getpass",
                   side_effect=["local-demo-password", "local-demo-password"]):
            call_command("create_studio_workspace", username="new-owner", studio="New studio", verbosity=0)
        user = get_user_model().objects.get(username="new-owner")
        self.assertTrue(user.check_password("local-demo-password"))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertEqual(Membership.objects.get(user=user).role, Membership.Role.OWNER)

    def test_setup_refuses_existing_user_and_mismatched_password(self):
        from unittest.mock import patch
        from django.core.management import call_command, CommandError
        get_user_model().objects.create_user("existing-owner")
        with self.assertRaises(CommandError):
            call_command("create_studio_workspace", username="existing-owner", studio="New studio")
        with patch("studio_os.operations.management.commands.create_studio_workspace.getpass",
                   side_effect=["local-demo-password", "different-password"]):
            with self.assertRaises(CommandError):
                call_command("create_studio_workspace", username="another-owner", studio="New studio")
        self.assertFalse(Organization.objects.exists())

    def test_local_setup_rejects_non_sqlite_settings(self):
        from django.core.management import call_command, CommandError
        from unittest.mock import patch
        with patch("studio_os.operations.management.commands.create_studio_workspace.settings") as settings:
            settings.SETTINGS_MODULE = "another.settings"
            with self.assertRaises(CommandError):
                call_command("create_studio_workspace", username="new", studio="Studio")
