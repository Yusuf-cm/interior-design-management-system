from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Activity, Customer, Lead, Membership, NextAction, Organization


class TenantIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user("owner-a", password="test-only")
        self.b = User.objects.create_user("owner-b", password="test-only")
        self.org_a = Organization.objects.create(name="Studio A")
        self.org_b = Organization.objects.create(name="Studio B")
        Membership.objects.create(user=self.a, organization=self.org_a, role=Membership.Role.OWNER)
        Membership.objects.create(user=self.b, organization=self.org_b, role=Membership.Role.OWNER)
        self.customer_a = Customer.objects.create(organization=self.org_a, name="Amina")
        self.customer_b = Customer.objects.create(organization=self.org_b, name="Other")
        self.client = APIClient()
        self.client.force_authenticate(user=self.a)

    def test_cross_tenant_customer_rejected(self):
        response = self.client.post("/api/leads/", {"customer": self.customer_b.id, "brief": "Renovation"}, format="json", HTTP_X_ORGANIZATION_ID=str(self.org_a.id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    def test_cross_tenant_header_rejected(self):
        response = self.client.get("/api/leads/", HTTP_X_ORGANIZATION_ID=str(self.org_b.id))
        self.assertEqual(response.status_code, 403)

    def test_lead_creation_generates_activity_and_action(self):
        response = self.client.post("/api/leads/", {"customer": self.customer_a.id, "brief": "Renovation"}, format="json", HTTP_X_ORGANIZATION_ID=str(self.org_a.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Activity.objects.filter(organization=self.org_a).count(), 1)
        self.assertEqual(NextAction.objects.filter(organization=self.org_a).count(), 1)

    def test_daily_queue_is_tenant_scoped(self):
        lead = Lead.objects.create(organization=self.org_b, customer=self.customer_b)
        NextAction.objects.create(organization=self.org_b, lead=lead, title="Private task")
        response = self.client.get("/api/today/", HTTP_X_ORGANIZATION_ID=str(self.org_a.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_anonymous_request_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/leads/", HTTP_X_ORGANIZATION_ID=str(self.org_a.id))
        self.assertIn(response.status_code, [401, 403])



class CustomerWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("studio-owner", password="test-only")
        self.field = User.objects.create_user("field-worker", password="test-only")
        self.org = Organization.objects.create(name="Nuru Interiors")
        self.other = Organization.objects.create(name="Other Studio")
        Membership.objects.create(user=self.owner, organization=self.org, role=Membership.Role.OWNER)
        Membership.objects.create(user=self.field, organization=self.org, role=Membership.Role.FIELD)
        Customer.objects.create(organization=self.other, name="Private Other Client")
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.id)}

    def test_owner_can_create_customer_without_supplying_tenant(self):
        response = self.client.post("/api/customers/", {"name": "Amina", "phone": "+254700000000"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Customer.objects.get(name="Amina").organization, self.org)

    def test_customer_list_excludes_other_company(self):
        response = self.client.get("/api/customers/", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_field_staff_cannot_create_customer(self):
        self.client.force_authenticate(user=self.field)
        response = self.client.post("/api/customers/", {"name": "Unauthorized"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 403)

    def test_client_cannot_override_organization(self):
        response = self.client.post("/api/customers/", {"name": "Amina", "organization": self.other.id}, format="json", **self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Customer.objects.get(name="Amina").organization, self.org)


class DailyActionWorkflowTests(TestCase):
    def setUp(self):
        TenantIsolationTests.setUp(self)
        from django.utils import timezone
        self.now = timezone.now()
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org_a.pk)}
        self.lead = Lead.objects.create(organization=self.org_a, customer=self.customer_a)
        self.action = NextAction.objects.create(
            organization=self.org_a, lead=self.lead, assignee=self.a,
            title="Respond", due_at=self.now,
        )

    def complete(self, action=None, **payload):
        return self.client.post(
            f"/api/actions/{(action or self.action).pk}/complete/",
            payload or {"note": "Called customer"}, format="json", **self.headers,
        )

    def test_complete_with_follow_up_is_idempotent(self):
        from datetime import timedelta
        payload = {"note": "Customer requested a call tomorrow",
                   "follow_up_title": "Call tomorrow",
                   "follow_up_due_at": (self.now + timedelta(days=1)).isoformat()}
        self.assertEqual(self.complete(**payload).status_code, 200)
        self.assertEqual(self.complete(**payload).status_code, 200)
        self.assertEqual(NextAction.objects.filter(lead=self.lead).count(), 2)
        self.assertEqual(Activity.objects.filter(kind="ACTION_COMPLETED").count(), 1)
        response = self.client.get("/api/today/", **self.headers)
        self.assertEqual(response.json(), [])

    def test_invalid_follow_up_rolls_back(self):
        self.assertEqual(self.complete(note="Called", follow_up_title="Call").status_code, 400)
        self.action.refresh_from_db()
        self.assertFalse(self.action.done)
        self.assertFalse(Activity.objects.exists())

    def test_cross_tenant_detail_and_completion_are_hidden(self):
        foreign_lead = Lead.objects.create(organization=self.org_b, customer=self.customer_b)
        foreign_action = NextAction.objects.create(organization=self.org_b, lead=foreign_lead, title="Secret")
        self.assertEqual(self.complete(foreign_action).status_code, 404)
        self.assertEqual(self.client.get(f"/api/leads/{foreign_lead.pk}/", **self.headers).status_code, 404)
        foreign_action.refresh_from_db()
        self.assertFalse(foreign_action.done)

    def test_inactive_membership_blocks_all_routes(self):
        Membership.objects.filter(user=self.a).update(active=False)
        for url in ["/api/customers/", "/api/leads/", "/api/today/", f"/api/leads/{self.lead.pk}/"]:
            self.assertEqual(self.client.get(url, **self.headers).status_code, 403)
        self.assertEqual(self.complete().status_code, 403)

    def test_field_staff_only_access_assigned_actions(self):
        Membership.objects.filter(user=self.a).update(role=Membership.Role.FIELD)
        other_action = NextAction.objects.create(
            organization=self.org_a, lead=self.lead, assignee=self.b, title="Other staff task")
        for url in ["/api/customers/", "/api/leads/", f"/api/leads/{self.lead.pk}/"]:
            self.assertEqual(self.client.get(url, **self.headers).status_code, 403)
        self.assertEqual(self.complete(other_action).status_code, 404)
        self.assertEqual([a["id"] for a in self.client.get("/api/today/", **self.headers).json()], [self.action.pk])
        self.assertEqual(self.complete().status_code, 200)

    def test_history_contains_recorded_note(self):
        self.complete(note="Asked about living room dimensions")
        response = self.client.get(f"/api/leads/{self.lead.pk}/", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["activities"][0]["details"]["note"], "Asked about living room dimensions")

    def test_queue_includes_overdue_and_undated_but_not_future(self):
        from datetime import timedelta
        for title, due in [("Overdue", self.now-timedelta(days=1)),
                           ("Undated", None), ("Future", self.now+timedelta(days=2))]:
            NextAction.objects.create(organization=self.org_a, lead=self.lead, title=title, due_at=due)
        titles = {a["title"] for a in self.client.get("/api/today/", **self.headers).json()}
        self.assertEqual(titles, {"Respond", "Overdue", "Undated"})

    def test_session_authentication_works_and_csrf_is_required(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="owner-a", password="test-only"))
        self.assertEqual(client.get("/api/today/", **self.headers).status_code, 200)
        self.assertEqual(client.post("/api/customers/", {"name": "Blocked"}, **self.headers).status_code, 403)

    def test_full_customer_inquiry_response_flow(self):
        customer = self.client.post("/api/customers/", {"name": "New customer"}, format="json", **self.headers)
        self.assertEqual(customer.status_code, 201)
        lead = self.client.post("/api/leads/", {"customer": customer.json()["id"], "brief": "Living room refresh"},
                                format="json", **self.headers)
        self.assertEqual(lead.status_code, 201)
        action = NextAction.objects.get(lead_id=lead.json()["id"])
        self.assertEqual(self.complete(action, note="Spoke with customer; gathering measurements").status_code, 200)
        detail = self.client.get(f'/api/leads/{lead.json()["id"]}/', **self.headers).json()
        self.assertEqual([a["kind"] for a in detail["activities"]], ["LEAD_CREATED", "ACTION_COMPLETED"])
        self.assertTrue(detail["actions"][0]["done"])

    def test_blank_note_and_past_follow_up_rejected(self):
        from datetime import timedelta
        self.assertEqual(self.complete(note=" ").status_code, 400)
        self.assertEqual(self.complete(note="Called", follow_up_title="Call",
                         follow_up_due_at=(self.now-timedelta(days=1)).isoformat()).status_code, 400)
        self.action.refresh_from_db()
        self.assertFalse(self.action.done)
