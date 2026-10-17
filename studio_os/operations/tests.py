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
