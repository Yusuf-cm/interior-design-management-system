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
