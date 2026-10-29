from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Assessment, Consultation, Customer, Lead, Membership, Organization, Quote, QuoteRevision


class QuoteRegisterPrintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("print-owner")
        cls.field = User.objects.create_user("print-field")
        cls.other_owner = User.objects.create_user("foreign-print-owner")
        cls.org = Organization.objects.create(name="Nuru Interiors")
        cls.other = Organization.objects.create(name="Foreign Interiors")
        Membership.objects.create(organization=cls.org, user=cls.owner, role="OWNER")
        Membership.objects.create(organization=cls.org, user=cls.field, role="FIELD")
        Membership.objects.create(organization=cls.other, user=cls.other_owner, role="OWNER")

    def setUp(self):
        customer = Customer.objects.create(organization=self.org, name="<script>client</script>")
        self.lead = Lead.objects.create(organization=self.org, customer=customer, status="ASSESSED")
        visit = Consultation.objects.create(organization=self.org, lead=self.lead, assignee=self.owner,
            starts_at=timezone.now()-timedelta(hours=2), ends_at=timezone.now()-timedelta(hours=1),
            location="Site", status="COMPLETED", outcome="Private visit outcome")
        self.assessment = Assessment.objects.create(organization=self.org, consultation=visit,
            scope="Paint living room", notes="Private internal margin discussion", status="READY_FOR_ESTIMATE", version=2)
        self.quote = Quote.objects.create(organization=self.org, assessment=self.assessment,
                                           currency="KES", status="APPROVED_TO_SHARE")
        self.revision = self.make_revision(1, "1500.00")
        self.quote.current_revision = self.revision
        self.quote.save()
        self.client = APIClient()
        self.client.force_login(self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.pk)}

    def make_revision(self, number, total):
        return QuoteRevision.objects.create(
            organization=self.org, quote=self.quote, number=number, assessment_version=2,
            scope_snapshot="Paint living room", notes_snapshot="Private internal margin discussion",
            provisional_reason_snapshot="Private provisional approval reason",
            currency="KES", items=[{"description":"Paint", "quantity":"1.000", "unit_price":total, "amount":total}],
            subtotal=Decimal(total), discount=0, tax_rate=0, tax=0, total=Decimal(total))

    def url(self, suffix=""):
        return f"/quotes/{self.quote.pk}/print/?organization={self.org.pk}"+suffix

    def test_register_filters_and_scopes_company_quotes(self):
        response = self.client.get("/api/quotes/?status=APPROVED_TO_SHARE", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["lead"], self.lead.pk)
        self.assertEqual(response.json()[0]["current_revision"]["total"], "1500.00")
        self.assertEqual(self.client.get("/api/quotes/?status=DRAFT", **self.headers).json(), [])
        self.assertEqual(self.client.get("/api/quotes/?status=bogus", **self.headers).status_code, 400)
        self.client.force_login(self.other_owner)
        self.assertEqual(self.client.get("/api/quotes/",
            HTTP_X_ORGANIZATION_ID=str(self.other.pk)).json(), [])

    def test_approved_print_excludes_private_notes_and_escapes_customer_text(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reviewed estimate")
        self.assertContains(response, "1,500.00")
        self.assertNotContains(response, "Private internal")
        self.assertNotContains(response, "Private visit")
        self.assertNotContains(response, "Private provisional")
        self.assertContains(response, "&lt;script&gt;client&lt;/script&gt;")
        self.assertContains(response, "Preliminary estimate")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, "APPROVED_TO_SHARE")

    def test_changed_source_or_draft_print_is_marked_internal(self):
        self.assessment.version = 3
        self.assessment.save()
        self.assertContains(self.client.get(self.url()), "Not approved for sharing")
        self.quote.status = "DRAFT"
        self.quote.save()
        self.assertContains(self.client.get(self.url()), "Internal draft")

    def test_old_revision_print_is_archived_and_retains_original_amount(self):
        self.quote.current_revision = self.make_revision(2, "2000.00")
        self.quote.save()
        response = self.client.get(self.url("&revision=1"))
        self.assertContains(response, "Archived revision")
        self.assertContains(response, "1,500.00")
        self.assertNotContains(response, "2,000.00")

    def test_anonymous_field_and_foreign_users_cannot_print(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.client.force_login(self.field)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.get("/api/quotes/", **self.headers).status_code, 403)
        self.client.force_login(self.other_owner)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        response = self.client.get(f"/quotes/{self.quote.pk}/print/?organization={self.other.pk}")
        self.assertEqual(response.status_code, 404)

    def test_print_query_validation_and_lost_quote(self):
        self.assertEqual(self.client.get(f"/quotes/{self.quote.pk}/print/").status_code, 400)
        self.assertEqual(self.client.get(self.url("&revision=bad")).status_code, 400)
        self.assertEqual(self.client.get(self.url("&revision=99")).status_code, 404)
        self.lead.status = "LOST"
        self.lead.save()
        self.assertContains(self.client.get(self.url()), "Internal draft")
