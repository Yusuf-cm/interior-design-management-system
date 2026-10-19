from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Activity, Consultation, Lead, Membership, NextAction
from . import tests as existing_tests


class ConsultationWorkflowTests(TestCase):
    def setUp(self):
        existing_tests.TenantIsolationTests.setUp(self)
        self.headers = {"HTTP_X_ORGANIZATION_ID": str(self.org_a.pk)}
        self.start = timezone.now() + timedelta(days=1)
        self.lead = Lead.objects.create(
            organization=self.org_a, customer=self.customer_a, status=Lead.Status.QUALIFIED)

    def propose(self, lead=None, **changes):
        data = {"starts_at": self.start.isoformat(),
                "ends_at": (self.start + timedelta(hours=1)).isoformat(),
                "location": "Customer site", "assignee": self.a.pk, **changes}
        return self.client.post(f"/api/leads/{(lead or self.lead).pk}/consultations/",
                                data, format="json", **self.headers)

    def command(self, visit_id, command, version=1, **changes):
        return self.client.post(f"/api/consultations/{visit_id}/command/",
                                {"command": command, "expected_version": version,
                                 "note": "Recorded visit update", **changes},
                                format="json", **self.headers)

    def test_proposal_confirmation_and_visit_action(self):
        proposed = self.propose()
        self.assertEqual(proposed.status_code, 201)
        self.assertEqual(proposed.json()["status"], "PROPOSED")
        self.assertFalse(NextAction.objects.exists())
        response = self.command(proposed.json()["id"], "confirm")
        self.assertEqual(response.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "CONSULTATION_BOOKED")
        action = NextAction.objects.get()
        self.assertEqual(action.consultation_id, proposed.json()["id"])
        self.assertEqual(action.assignee_id, self.a.pk)
        self.assertEqual(action.due_at, self.start)

    def test_overlaps_blocked_without_leaking_details(self):
        first = self.propose().json()["id"]
        second = self.propose(location="Other site").json()["id"]
        self.assertEqual(self.command(first, "confirm").status_code, 200)
        response = self.command(second, "confirm")
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("Other site", str(response.data))
        self.assertEqual(Consultation.objects.get(pk=second).status, "PROPOSED")
        self.assertEqual(NextAction.objects.count(), 1)

    def test_adjacent_bookings_are_allowed(self):
        first = self.propose().json()["id"]
        second = self.propose(
            starts_at=(self.start+timedelta(hours=1)).isoformat(),
            ends_at=(self.start+timedelta(hours=2)).isoformat()).json()["id"]
        self.assertEqual(self.command(first, "confirm").status_code, 200)
        self.assertEqual(self.command(second, "confirm").status_code, 200)

    def test_reschedule_releases_slot_and_requires_reconfirmation(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        response = self.command(visit, "reschedule", version=2,
            starts_at=(self.start+timedelta(days=1)).isoformat(),
            ends_at=(self.start+timedelta(days=1, hours=1)).isoformat(),
            location="Changed site", assignee=self.a.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "RESCHEDULED")
        self.assertTrue(NextAction.objects.get(consultation_id=visit).cancelled)
        self.assertEqual(self.command(visit, "confirm", version=3).status_code, 200)
        action = NextAction.objects.get(consultation_id=visit)
        self.assertFalse(action.cancelled)
        self.assertEqual(action.due_at, self.start+timedelta(days=1))
        self.assertEqual(Activity.objects.filter(kind="CONSULTATION_RESCHEDULE").count(), 1)

    def test_complete_requires_start_time_and_note(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        self.assertEqual(self.command(visit, "complete", version=2).status_code, 400)
        with patch("studio_os.operations.consultations.timezone.now", return_value=self.start+timedelta(hours=2)):
            self.assertEqual(self.command(visit, "complete", version=2, note=" ").status_code, 400)
            response = self.command(visit, "complete", version=2, note="Measured living room")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "Measured living room")
        self.assertTrue(NextAction.objects.get(consultation_id=visit).done)
        self.assertTrue(NextAction.objects.filter(title="Prepare visit assessment").exists())
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "CONSULTATION_BOOKED")
        self.assertEqual(self.command(visit, "complete", version=3).status_code, 409)
        self.assertEqual(NextAction.objects.filter(title="Prepare visit assessment").count(), 1)

    def test_no_show_queues_follow_up(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        with patch("studio_os.operations.consultations.timezone.now", return_value=self.start+timedelta(hours=2)):
            self.assertEqual(self.command(visit, "no_show", version=2).status_code, 200)
        self.assertTrue(NextAction.objects.get(consultation_id=visit).cancelled)
        self.assertTrue(NextAction.objects.filter(title="Follow up on missed consultation").exists())

    def test_cancellation_releases_slot(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        self.assertEqual(self.command(visit, "cancel", version=2).status_code, 200)
        replacement = self.propose().json()["id"]
        self.assertEqual(self.command(replacement, "confirm").status_code, 200)

    def test_stale_and_invalid_commands_do_not_change_visit(self):
        visit = self.propose().json()["id"]
        self.assertEqual(self.command(visit, "complete").status_code, 409)
        self.command(visit, "confirm")
        self.assertEqual(self.command(visit, "cancel", version=1).status_code, 409)
        self.assertEqual(self.command(visit, "confirm", version=2).status_code, 409)
        self.assertEqual(Consultation.objects.get(pk=visit).status, "CONFIRMED")

    def test_unqualified_or_closed_inquiry_cannot_schedule(self):
        for state in [Lead.Status.NEW, Lead.Status.CONTACTED, Lead.Status.LOST, Lead.Status.WON]:
            self.lead.status = state
            self.lead.save()
            self.assertEqual(self.propose().status_code, 409)

    def test_invalid_dates_and_assignment_rejected(self):
        for changes in [
            {"ends_at": self.start.isoformat()},
            {"starts_at": (timezone.now()-timedelta(days=1)).isoformat()},
            {"assignee": self.b.pk}, {"location": " "},
        ]:
            self.assertEqual(self.propose(**changes).status_code, 400)
        self.assertFalse(Consultation.objects.exists())

    def test_cross_tenant_routes_and_lists(self):
        foreign = Lead.objects.create(organization=self.org_b, customer=self.customer_b,
                                      status=Lead.Status.QUALIFIED)
        self.assertEqual(self.propose(lead=foreign).status_code, 404)
        visit = Consultation.objects.create(
            organization=self.org_b, lead=foreign, assignee=self.b,
            starts_at=self.start, ends_at=self.start+timedelta(hours=1), location="Secret")
        self.assertEqual(self.command(visit.pk, "confirm").status_code, 404)
        self.assertEqual(self.client.get("/api/consultations/", **self.headers).json(), [])

    def test_field_staff_only_see_and_record_assigned_outcomes(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        Membership.objects.filter(user=self.a).update(role=Membership.Role.FIELD)
        self.assertEqual(self.propose().status_code, 403)
        self.assertEqual(self.command(visit, "cancel", version=2).status_code, 403)
        self.assertEqual(len(self.client.get("/api/consultations/", **self.headers).json()), 1)
        with patch("studio_os.operations.consultations.timezone.now", return_value=self.start+timedelta(hours=2)):
            self.assertEqual(self.command(visit, "complete", version=2).status_code, 200)

    def test_generic_action_routes_cannot_bypass_visit_outcome(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        action = NextAction.objects.get(consultation_id=visit)
        response = self.client.post(f"/api/actions/{action.pk}/complete/",
            {"expected_version": 1, "note": "Bypass"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 409)
        response = self.client.patch(f"/api/actions/{action.pk}/",
            {"expected_version": 1, "note": "Bypass", "title": "Changed"}, format="json", **self.headers)
        self.assertEqual(response.status_code, 409)

    def test_lost_inquiry_cancels_visits_and_actions(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        self.lead.refresh_from_db()
        response = self.client.post(f"/api/leads/{self.lead.pk}/transition/",
            {"expected_version": self.lead.version, "status": "LOST", "note": "Client withdrew"},
            format="json", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Consultation.objects.get(pk=visit).status, "CANCELLED")
        self.assertTrue(NextAction.objects.get(consultation_id=visit).cancelled)
        self.assertEqual(self.command(visit, "confirm", version=3).status_code, 409)

    def test_inactive_assignee_cannot_be_confirmed(self):
        visit = self.propose().json()["id"]
        Membership.objects.filter(user=self.a).update(active=False)
        self.client.force_authenticate(user=self.b)
        Membership.objects.create(user=self.b, organization=self.org_a, role=Membership.Role.OWNER)
        self.assertEqual(self.command(visit, "confirm").status_code, 400)

    def test_confirm_rescheduled_slot_checks_conflicts_again(self):
        first = self.propose().json()["id"]
        second = self.propose(
            starts_at=(self.start+timedelta(hours=2)).isoformat(),
            ends_at=(self.start+timedelta(hours=3)).isoformat()).json()["id"]
        self.command(first, "confirm")
        self.command(second, "confirm")
        self.command(second, "reschedule", version=2,
            starts_at=(self.start+timedelta(minutes=30)).isoformat(),
            ends_at=(self.start+timedelta(hours=2)).isoformat(),
            location="Changed", assignee=self.a.pk)
        self.assertEqual(self.command(second, "confirm", version=3).status_code, 409)
        self.assertEqual(Consultation.objects.get(pk=second).status, "RESCHEDULED")

    def test_field_staff_cannot_access_other_assignees_visit(self):
        visit = self.propose().json()["id"]
        Membership.objects.create(user=self.b, organization=self.org_a, role=Membership.Role.FIELD)
        self.client.force_authenticate(user=self.b)
        self.assertEqual(self.command(visit, "complete").status_code, 404)
        self.assertEqual(self.client.get("/api/consultations/", **self.headers).json(), [])

    def test_inactive_or_anonymous_request_cannot_read_visits(self):
        self.propose()
        Membership.objects.filter(user=self.a).update(active=False)
        self.assertEqual(self.client.get("/api/consultations/", **self.headers).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get("/api/consultations/", **self.headers).status_code, [401, 403])

    def test_inquiry_detail_includes_consultation_history(self):
        visit = self.propose().json()["id"]
        self.command(visit, "cancel")
        response = self.client.get(f"/api/leads/{self.lead.pk}/", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["consultations"][0]["status"], "CANCELLED")

    def test_invalid_reschedule_is_atomic(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        self.assertEqual(self.command(visit, "reschedule", version=2, location="Missing dates").status_code, 400)
        self.assertEqual(Consultation.objects.get(pk=visit).version, 2)
        self.assertFalse(NextAction.objects.get(consultation_id=visit).cancelled)

    def test_visit_action_is_unique_after_repeated_confirmation(self):
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        self.assertEqual(self.command(visit, "confirm").status_code, 409)
        self.assertEqual(NextAction.objects.filter(consultation_id=visit).count(), 1)

    def test_field_completion_queues_assessment_for_office_not_field_staff(self):
        from django.contrib.auth import get_user_model
        office = get_user_model().objects.create_user("office-designer")
        Membership.objects.create(user=office, organization=self.org_a, role=Membership.Role.DESIGNER)
        visit = self.propose().json()["id"]
        self.command(visit, "confirm")
        Membership.objects.filter(user=self.a).update(role=Membership.Role.FIELD)
        with patch("studio_os.operations.consultations.timezone.now", return_value=self.start+timedelta(hours=2)):
            self.assertEqual(self.command(visit, "complete", version=2).status_code, 200)
        task = NextAction.objects.get(origin_key=f"visit:{visit}:assessment")
        self.assertEqual(task.assignee, office)

    def test_designer_cannot_take_over_another_staff_members_visit(self):
        from django.contrib.auth import get_user_model
        designer = get_user_model().objects.create_user("other-designer")
        Membership.objects.create(user=designer, organization=self.org_a, role=Membership.Role.DESIGNER)
        visit = self.propose().json()["id"]
        self.client.force_authenticate(user=designer)
        response = self.command(visit, "reschedule", starts_at=(self.start+timedelta(days=1)).isoformat(),
            ends_at=(self.start+timedelta(days=1,hours=1)).isoformat(), location="Other site", assignee=designer.pk)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Consultation.objects.get(pk=visit).assignee_id, self.a.pk)
