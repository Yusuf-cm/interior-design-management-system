from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Activity, Customer, Lead, Membership, NextAction, Organization


class TeamAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("team-owner", password="Initial-Studio-Key!2026")
        cls.designer = User.objects.create_user("team-designer")
        cls.other_owner = User.objects.create_user("different-owner")
        cls.org = Organization.objects.create(name="Studio One")
        cls.other = Organization.objects.create(name="Studio Two")
        cls.owner_member = Membership.objects.create(organization=cls.org, user=cls.owner, role="OWNER")
        cls.designer_member = Membership.objects.create(organization=cls.org, user=cls.designer, role="DESIGNER")
        cls.foreign_member = Membership.objects.create(organization=cls.other, user=cls.other_owner, role="OWNER")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.pk)}

    def add(self, **changes):
        return self.client.post("/api/team/", {"username": "new-colleague", "name": "New colleague",
            "role": "DESIGNER", "password": "Independent-Passphrase!492", **changes},
            format="json", **self.headers)

    def update(self, member=None, **changes):
        member = member or self.designer_member
        return self.client.patch(f"/api/team/{member.pk}/",
            {"expected_version": 1, "note": "Staff responsibilities changed", **changes},
            format="json", **self.headers)

    def test_owner_can_add_staff_without_global_admin_privileges_or_password_leak(self):
        response = self.add(is_staff=True, is_superuser=True, organization=self.other.pk)
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username="new-colleague")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("Independent-Passphrase!492"))
        self.assertEqual(Membership.objects.get(user=user).organization_id, self.org.pk)
        self.assertNotIn("password", response.content.decode())
        self.assertNotIn("Independent", str(Activity.objects.get(kind="TEAM_MEMBER_ADDED").details))

    def test_existing_global_account_is_not_linked_or_modified(self):
        self.assertEqual(self.add(username=self.other_owner.username).status_code, 409)
        self.assertFalse(Membership.objects.filter(user=self.other_owner, organization=self.org).exists())

    def test_weak_passwords_and_invalid_roles_are_rejected(self):
        for payload in [{"password": "short"}, {"password": "123456789012"},
                        {"role": "SUPERUSER"}, {"username": "contains spaces"}]:
            self.assertEqual(self.add(**payload).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 3)

    def test_nonowners_cannot_list_add_or_change_team(self):
        self.client.force_authenticate(user=self.designer)
        self.assertEqual(self.client.get("/api/team/", **self.headers).status_code, 403)
        self.assertEqual(self.add().status_code, 403)
        self.assertEqual(self.update(role="OWNER").status_code, 403)

    def test_other_company_members_are_hidden(self):
        response = self.client.get("/api/team/", **self.headers)
        self.assertEqual({member["user_id"] for member in response.json()}, {self.owner.pk, self.designer.pk})
        self.assertEqual(self.update(member=self.foreign_member, active=False).status_code, 404)

    def test_last_active_owner_cannot_be_removed(self):
        self.assertEqual(self.update(member=self.owner_member, active=False).status_code, 409)
        self.assertEqual(self.update(member=self.owner_member, role="DESIGNER").status_code, 409)

    def test_owner_handoff_requires_another_active_owner(self):
        self.assertEqual(self.update(role="OWNER").status_code, 200)
        self.assertEqual(self.update(member=self.owner_member, role="COORDINATOR").status_code, 200)
        self.owner_member.refresh_from_db()
        self.assertEqual(self.owner_member.role, "COORDINATOR")

    def test_disabled_global_user_does_not_count_as_another_active_owner(self):
        self.designer.is_active = False
        self.designer.save()
        Membership.objects.filter(pk=self.designer_member.pk).update(role="OWNER")
        self.assertEqual(self.update(member=self.owner_member, active=False).status_code, 409)

    def test_stale_edit_does_not_overwrite_access(self):
        self.assertEqual(self.update(active=False).status_code, 200)
        self.assertEqual(self.update(role="OWNER").status_code, 409)
        self.designer_member.refresh_from_db()
        self.assertFalse(self.designer_member.active)
        self.assertEqual(self.designer_member.version, 2)

    def test_deactivation_preserves_assignments_and_blocks_company_access(self):
        customer = Customer.objects.create(organization=self.org, name="Amina")
        lead = Lead.objects.create(organization=self.org, customer=customer)
        task = NextAction.objects.create(organization=self.org, lead=lead, assignee=self.designer, title="Existing work")
        response = self.update(active=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["open_actions"], 1)
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.designer.pk)
        self.client.force_authenticate(user=self.designer)
        self.assertEqual(self.client.get("/api/today/", **self.headers).status_code, 403)

    def test_reactivation_preserves_history_and_audits_actor_and_reason(self):
        self.update(active=False)
        response = self.update(expected_version=2, active=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 3)
        events = Activity.objects.filter(kind="TEAM_ACCESS_CHANGED")
        self.assertEqual(events.count(), 2)
        self.assertEqual(events.last().actor_id, self.owner.pk)
        self.assertEqual(events.last().details["note"], "Staff responsibilities changed")

    def test_password_change_requires_current_password_and_keeps_session(self):
        self.client.force_authenticate(user=None)
        self.client.login(username="team-owner", password="Initial-Studio-Key!2026")
        data = {"current_password": "wrong", "new_password": "Updated-Studio-Key!752"}
        self.assertEqual(self.client.post("/api/session/password/", data, format="json").status_code, 400)
        data["current_password"] = "Initial-Studio-Key!2026"
        response = self.client.post("/api/session/password/", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertFalse(self.client.login(username="team-owner", password="Initial-Studio-Key!2026"))
        self.assertTrue(self.client.login(username="team-owner", password="Updated-Studio-Key!752"))
