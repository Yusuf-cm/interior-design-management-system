from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (Activity, Assessment, Consultation, Customer, Lead, Membership, NextAction,
                     Organization, Quote, QuoteRevision)


class AssessmentQuoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner-estimate")
        cls.designer = get_user_model().objects.create_user("designer-estimate")
        cls.field = get_user_model().objects.create_user("field-estimate")
        cls.other_owner = get_user_model().objects.create_user("other-owner")
        cls.org = Organization.objects.create(name="Nuru Interiors")
        cls.other = Organization.objects.create(name="Other company")
        for user, role in [(cls.owner, Membership.Role.OWNER), (cls.designer, Membership.Role.DESIGNER),
                           (cls.field, Membership.Role.FIELD)]:
            Membership.objects.create(user=user, organization=cls.org, role=role)
        Membership.objects.create(user=cls.other_owner, organization=cls.other, role=Membership.Role.OWNER)
        cls.customer = Customer.objects.create(organization=cls.org, name="Amina")
        cls.foreign_customer = Customer.objects.create(organization=cls.other, name="Private customer")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org.pk)}
        self.lead = Lead.objects.create(organization=self.org, customer=self.customer,
                                        status=Lead.Status.CONSULTATION_BOOKED)
        self.visit = Consultation.objects.create(
            organization=self.org, lead=self.lead, assignee=self.designer,
            starts_at=timezone.now()-timedelta(hours=2), ends_at=timezone.now()-timedelta(hours=1),
            location="Customer site", status=Consultation.Status.COMPLETED, outcome="Measured site")
        self.measurements = [{"label": "Living room length", "value": "4.200", "unit": "m", "required": True}]

    def create_assessment(self, **changes):
        return self.client.post(f"/api/consultations/{self.visit.pk}/assessment/",
            {"scope": "Paint living room walls", "notes": "Protect existing floor",
             "measurements": self.measurements, **changes}, format="json", **self.headers)

    def assessment_command(self, pk, command="ready", version=1, **changes):
        return self.client.post(f"/api/assessments/{pk}/command/",
            {"expected_version": version, "command": command, "note": "Reviewed observations", **changes},
            format="json", **self.headers)

    def ready_assessment(self, **changes):
        response = self.create_assessment(**changes)
        self.assertEqual(response.status_code, 201)
        pk = response.json()["id"]
        self.assertEqual(self.assessment_command(pk).status_code, 200)
        return Assessment.objects.get(pk=pk)

    def quote(self, assessment, **changes):
        return self.client.post(f"/api/assessments/{assessment.pk}/quote/",
            {"expected_assessment_version": assessment.version,
             "items": [{"description": "Paint", "quantity": "2.000", "unit_price": "1000.00"},
                       {"description": "Labour", "quantity": "1.000", "unit_price": "500.00"}],
             **changes}, format="json", **self.headers)

    def review(self, pk, command="submit", version=1, **changes):
        return self.client.post(f"/api/quotes/{pk}/review/",
            {"expected_version": version, "command": command, "note": "Checked draft", **changes},
            format="json", **self.headers)

    def revision(self, quote, assessment, version=None, **changes):
        return self.client.post(f"/api/quotes/{quote.pk}/revisions/",
            {"expected_version": quote.version if version is None else version,
             "expected_assessment_version": assessment.version, "note": "Supplier changed price",
             "items": [{"description": "Updated paint", "quantity": "1.000", "unit_price": "3000.00"}],
             **changes}, format="json", **self.headers)

    def test_assessment_requires_completed_visit_and_is_unique(self):
        self.visit.status = Consultation.Status.CONFIRMED
        self.visit.save()
        self.assertEqual(self.create_assessment().status_code, 409)
        self.visit.status = Consultation.Status.COMPLETED
        self.visit.save()
        self.assertEqual(self.create_assessment().status_code, 201)
        self.assertEqual(self.create_assessment().status_code, 409)
        self.assertEqual(Assessment.objects.count(), 1)

    def test_missing_dimensions_block_readiness(self):
        self.measurements[0]["value"] = None
        response = self.create_assessment()
        pk = response.json()["id"]
        self.assertIn("Living room length", response.json()["missing_information"])
        self.assertEqual(self.assessment_command(pk).status_code, 400)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONSULTATION_BOOKED)

    def test_owner_provisional_exception_is_visible(self):
        self.measurements[0]["value"] = None
        pk = self.create_assessment().json()["id"]
        response = self.assessment_command(pk, provisional_reason="Preliminary budget only; revisit required")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Living room length", response.json()["missing_information"])
        self.assertTrue(response.json()["provisional_reason"])
        assessment = Assessment.objects.get(pk=pk)
        result = self.quote(assessment).json()
        self.assertEqual(result["current_revision"]["provisional_reason_snapshot"],
                         "Preliminary budget only; revisit required")

    def test_designer_cannot_authorize_provisional_estimate(self):
        self.measurements[0]["value"] = None
        pk = self.create_assessment().json()["id"]
        self.client.force_authenticate(user=self.designer)
        self.assertEqual(self.assessment_command(pk, provisional_reason="Skip measurement").status_code, 403)
        self.assertEqual(Assessment.objects.get(pk=pk).status, Assessment.Status.DRAFT)

    def test_scope_and_measurement_plan_are_required(self):
        pk = self.create_assessment(scope="", measurements=[]).json()["id"]
        self.assertEqual(self.assessment_command(pk, provisional_reason="Owner override").status_code, 400)
        pk2 = pk
        response = self.client.patch(f"/api/assessments/{pk2}/",
            {"expected_version": 1, "note": "Add scope", "scope": "Design lounge"},
            format="json", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.assessment_command(pk2, version=2).status_code, 400)

    def test_measurement_validation(self):
        for measurement in [
            {"label": "Length", "value": "-2", "unit": "m"},
            {"label": "Length", "value": "NaN", "unit": "m"},
            {"label": "Length", "value": "2", "unit": "unknown"},
        ]:
            self.assertEqual(self.create_assessment(measurements=[measurement]).status_code, 400)
        self.assertEqual(self.create_assessment(measurements=self.measurements*2).status_code, 400)

    def test_readiness_advances_lead_and_creates_single_estimate_action(self):
        assessment = self.ready_assessment()
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.ASSESSED)
        self.assertEqual(NextAction.objects.filter(origin_key=f"assessment:{assessment.pk}:estimate").count(), 1)
        self.assertEqual(self.assessment_command(assessment.pk, version=2).status_code, 409)

    def test_edit_stale_or_ready_assessment_is_rejected(self):
        pk = self.create_assessment().json()["id"]
        url = f"/api/assessments/{pk}/"
        payload = {"expected_version": 1, "note": "Correct scope", "scope": "Paint ceiling too"}
        self.assertEqual(self.client.patch(url, payload, format="json", **self.headers).status_code, 200)
        self.assertEqual(self.client.patch(url, payload, format="json", **self.headers).status_code, 409)
        self.assessment_command(pk, version=2)
        payload["expected_version"] = 3
        self.assertEqual(self.client.patch(url, payload, format="json", **self.headers).status_code, 409)

    def test_quote_decimal_totals_and_untrusted_fields(self):
        assessment = self.ready_assessment()
        response = self.quote(assessment, discount="100.00", tax_rate="0.160000",
                              total="1.00", currency="USD", status="APPROVED_TO_SHARE",
                              organization=self.other.pk)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["currency"], "KES")
        rev = data["current_revision"]
        self.assertEqual(rev["subtotal"], "2500.00")
        self.assertEqual(rev["tax"], "384.00")
        self.assertEqual(rev["total"], "2784.00")
        self.assertEqual(rev["scope_snapshot"], assessment.scope)
        self.assertEqual(rev["notes_snapshot"], "Protect existing floor")

    def test_quote_requires_ready_current_source(self):
        pk = self.create_assessment().json()["id"]
        assessment = Assessment.objects.get(pk=pk)
        self.assertEqual(self.quote(assessment).status_code, 409)
        self.assessment_command(pk)
        self.assertEqual(self.quote(assessment).status_code, 409)
        assessment.refresh_from_db()
        self.assertEqual(self.quote(assessment).status_code, 201)
        self.assertEqual(self.quote(assessment).status_code, 409)

    def test_invalid_prices_discount_and_tax_rejected(self):
        assessment = self.ready_assessment()
        for data in [{"discount": "99999"}, {"tax_rate": "1.1"}, {"items": []},
                     {"items": [{"description": "Bad", "quantity": "0", "unit_price": "10"}]},
                     {"items": [{"description": "Bad", "quantity": "1", "unit_price": "-1"}]}]:
            self.assertEqual(self.quote(assessment, **data).status_code, 400)
        self.assertFalse(Quote.objects.exists())

    def test_review_requires_owner_and_explicit_submission(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.assertEqual(self.review(pk, command="approve").status_code, 409)
        self.client.force_authenticate(user=self.designer)
        self.assertEqual(self.review(pk).status_code, 200)
        action = NextAction.objects.get(origin_key=f"quote:{pk}:review")
        self.assertEqual(action.assignee, self.owner)
        self.assertEqual(self.review(pk, command="approve", version=2).status_code, 403)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.review(pk, command="approve", version=2).status_code, 200)
        action.refresh_from_db()
        self.assertTrue(action.done)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.ASSESSED)

    def test_revision_preserves_old_prices_and_resets_approval(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        self.review(pk, "approve", version=2)
        quote = Quote.objects.get(pk=pk)
        original = quote.current_revision
        response = self.revision(quote, assessment)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "DRAFT")
        original.refresh_from_db()
        self.assertEqual(original.total, Decimal("2500.00"))
        self.assertEqual(response.json()["current_revision"]["total"], "3000.00")
        self.assertEqual(quote.revisions.count(), 2)
        original.total = Decimal("1")
        with self.assertRaises(ValueError):
            original.save()

    def test_stale_quote_edit_and_approval_rejected_without_extra_revision(self):
        assessment = self.ready_assessment()
        quote = Quote.objects.get(pk=self.quote(assessment).json()["id"])
        self.assertEqual(self.revision(quote, assessment).status_code, 201)
        self.assertEqual(self.revision(quote, assessment).status_code, 409)
        self.assertEqual(self.review(quote.pk, version=1).status_code, 409)
        self.assertEqual(quote.revisions.count(), 2)

    def test_reopen_revokes_review_and_requires_new_snapshot(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        self.review(pk, "approve", version=2)
        self.assertEqual(self.assessment_command(assessment.pk, "reopen", version=2).status_code, 200)
        quote = Quote.objects.get(pk=pk)
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(self.review(pk, version=quote.version).status_code, 409)
        self.assertEqual(self.assessment_command(assessment.pk, version=3).status_code, 200)
        assessment.refresh_from_db()
        self.assertEqual(self.review(pk, version=quote.version).status_code, 409)
        self.assertEqual(self.revision(quote, assessment).status_code, 201)
        quote.refresh_from_db()
        self.assertEqual(self.review(pk, version=quote.version).status_code, 200)

    def test_field_staff_cannot_access_assessment_or_quotes(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.client.force_authenticate(user=self.field)
        for url in [f"/api/assessments/{assessment.pk}/", f"/api/quotes/{pk}/"]:
            self.assertEqual(self.client.get(url, **self.headers).status_code, 403)
        self.assertEqual(self.review(pk).status_code, 403)
        self.assertEqual(self.create_assessment().status_code, 403)

    def test_cross_company_reads_and_writes_are_hidden(self):
        assessment = self.ready_assessment()
        quote = Quote.objects.get(pk=self.quote(assessment).json()["id"])
        self.client.force_authenticate(user=self.other_owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.other.pk)}
        for url in [f"/api/assessments/{assessment.pk}/", f"/api/quotes/{quote.pk}/"]:
            self.assertEqual(self.client.get(url, **self.headers).status_code, 404)
        self.assertEqual(self.assessment_command(assessment.pk).status_code, 404)
        self.assertEqual(self.quote(assessment).status_code, 404)
        self.assertEqual(self.revision(quote, assessment).status_code, 404)
        self.assertEqual(self.review(quote.pk).status_code, 404)

    def test_inactive_membership_blocks_new_workflows(self):
        assessment = self.ready_assessment()
        Membership.objects.filter(user=self.owner, organization=self.org).update(active=False)
        self.assertEqual(self.quote(assessment).status_code, 403)
        self.assertEqual(self.client.get(f"/api/assessments/{assessment.pk}/", **self.headers).status_code, 403)

    def test_closed_inquiry_blocks_assessment_and_quote_mutations(self):
        assessment = self.ready_assessment()
        quote = Quote.objects.get(pk=self.quote(assessment).json()["id"])
        self.lead.status = Lead.Status.LOST
        self.lead.save()
        self.assertEqual(self.assessment_command(assessment.pk, "reopen", version=2).status_code, 409)
        self.assertEqual(self.revision(quote, assessment).status_code, 409)
        self.assertEqual(self.review(quote.pk).status_code, 409)

    def test_workflow_tasks_cannot_be_completed_to_bypass_review(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        action = NextAction.objects.get(origin_key=f"quote:{pk}:review")
        response = self.client.post(f"/api/actions/{action.pk}/complete/",
            {"expected_version": action.version, "note": "Bypass approval"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Quote.objects.get(pk=pk).status, Quote.Status.REVIEW)

    def test_inquiry_detail_contains_assessment_and_current_quote(self):
        assessment = self.ready_assessment()
        self.quote(assessment)
        data = self.client.get(f"/api/leads/{self.lead.pk}/", **self.headers).json()
        self.assertEqual(len(data["assessments"]), 1)
        self.assertEqual(data["quotes"][0]["current_revision"]["total"], "2500.00")

    def test_return_to_draft_and_resubmit_reuses_review_task(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        self.assertEqual(self.review(pk, "return_to_draft", version=2).status_code, 200)
        self.assertTrue(NextAction.objects.get(origin_key=f"quote:{pk}:review").cancelled)
        self.assertEqual(self.review(pk, version=3).status_code, 200)
        self.assertEqual(NextAction.objects.filter(origin_key=f"quote:{pk}:review").count(), 1)
        self.assertFalse(NextAction.objects.get(origin_key=f"quote:{pk}:review").cancelled)

    def test_no_active_owner_blocks_submission_transactionally(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        Membership.objects.filter(user=self.owner).update(active=False)
        self.client.force_authenticate(user=self.designer)
        self.assertEqual(self.review(pk).status_code, 409)
        self.assertEqual(Quote.objects.get(pk=pk).status, Quote.Status.DRAFT)
        self.assertFalse(NextAction.objects.filter(origin_key=f"quote:{pk}:review").exists())

    def test_complete_inquiry_to_reviewed_estimate_flow(self):
        customer = self.client.post("/api/customers/", {"name": "New renovation client"},
                                    format="json", **self.headers).json()
        lead = self.client.post("/api/leads/", {"customer": customer["id"], "brief": "Lounge renovation"},
                                format="json", **self.headers).json()
        for number, stage in [(1, "CONTACTED"), (2, "QUALIFIED")]:
            response = self.client.post(f'/api/leads/{lead["id"]}/transition/',
                {"expected_version": number, "status": stage, "note": "Customer conversation recorded"},
                format="json", **self.headers)
            self.assertEqual(response.status_code, 200)
        start = timezone.now()+timedelta(days=1)
        proposal = self.client.post(f'/api/leads/{lead["id"]}/consultations/',
            {"starts_at": start.isoformat(), "ends_at": (start+timedelta(hours=1)).isoformat(),
             "location": "Client lounge", "assignee": self.owner.pk}, format="json", **self.headers)
        self.assertEqual(proposal.status_code, 201)
        visit_id = proposal.json()["id"]
        command_url = f"/api/consultations/{visit_id}/command/"
        self.assertEqual(self.client.post(command_url,
            {"expected_version": 1, "command": "confirm", "note": "Visit agreed"},
            format="json", **self.headers).status_code, 200)
        with patch("studio_os.operations.consultations.timezone.now", return_value=start+timedelta(hours=2)):
            self.assertEqual(self.client.post(command_url,
                {"expected_version": 2, "command": "complete", "note": "Measured lounge"},
                format="json", **self.headers).status_code, 200)
        assessment_task = NextAction.objects.get(origin_key=f"visit:{visit_id}:assessment")
        response = self.client.post(f"/api/consultations/{visit_id}/assessment/",
            {"scope": "Paint lounge", "notes": "Keep sofa protected", "measurements": self.measurements},
            format="json", **self.headers)
        self.assertEqual(response.status_code, 201)
        assessment_task.refresh_from_db()
        self.assertTrue(assessment_task.done)
        assessment_id = response.json()["id"]
        self.assertEqual(self.assessment_command(assessment_id).status_code, 200)
        assessment = Assessment.objects.get(pk=assessment_id)
        quote_data = self.quote(assessment).json()
        self.assertEqual(self.review(quote_data["id"]).status_code, 200)
        self.assertEqual(self.review(quote_data["id"], "approve", version=2).status_code, 200)
        detail = self.client.get(f'/api/leads/{lead["id"]}/', **self.headers).json()
        self.assertEqual(detail["status"], "ASSESSED")
        self.assertEqual(detail["quotes"][0]["status"], "APPROVED_TO_SHARE")
        self.assertTrue(detail["quotes"][0]["source_current"])
        self.assertEqual(detail["quotes"][0]["current_revision"]["total"], "2500.00")
        self.assertTrue(NextAction.objects.get(origin_key=f"assessment:{assessment_id}:estimate").done)
        self.assertTrue(NextAction.objects.get(origin_key=f'quote:{quote_data["id"]}:review').done)

    def test_reopen_clears_exception_and_duplicate_tasks(self):
        self.measurements[0]["value"] = None
        pk = self.create_assessment().json()["id"]
        self.assessment_command(pk, provisional_reason="Preliminary only")
        self.assessment_command(pk, "reopen", version=2)
        self.assertEqual(Assessment.objects.get(pk=pk).provisional_reason, "")
        self.assertEqual(self.assessment_command(pk, version=3).status_code, 400)
        self.assertEqual(self.assessment_command(pk, version=3, provisional_reason="Still preliminary").status_code, 200)
        self.assertEqual(NextAction.objects.filter(origin_key=f"assessment:{pk}:estimate").count(), 1)
        self.assertTrue(NextAction.objects.get(origin_key=f"assessment:{pk}:recheck").done)

    def test_review_command_never_accepts_or_sends_estimate(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        for command in ["send", "accept", "mark_paid"]:
            self.assertEqual(self.review(pk, command).status_code, 400)
        self.assertEqual(Quote.objects.get(pk=pk).status, Quote.Status.DRAFT)

    def test_lost_inquiry_revokes_pending_or_approved_quote(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        self.review(pk, "approve", version=2)
        self.lead.refresh_from_db()
        response = self.client.post(f"/api/leads/{self.lead.pk}/transition/",
            {"expected_version": self.lead.version, "status": "LOST", "note": "Client declined"},
            format="json", **self.headers)
        self.assertEqual(response.status_code, 200)
        quote = Quote.objects.get(pk=pk)
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(quote.version, 4)
        self.assertIn(pk, Activity.objects.get(kind="LEAD_STATUS_CHANGED").details["revoked_quote_ids"])

    def test_reopened_source_has_explicit_quote_audit_entry(self):
        assessment = self.ready_assessment()
        pk = self.quote(assessment).json()["id"]
        self.review(pk)
        self.review(pk, "approve", version=2)
        self.assessment_command(assessment.pk, "reopen", version=2)
        entry = Activity.objects.get(kind="QUOTE_SOURCE_REOPENED")
        self.assertEqual(entry.details["quote_id"], pk)
        self.assertEqual(entry.details["previous_status"], "APPROVED_TO_SHARE")
        self.assertEqual(entry.details["new_status"], "DRAFT")
