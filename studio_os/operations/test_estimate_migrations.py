from datetime import timedelta
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class EstimateMigrationTests(TransactionTestCase):
    old = [("operations", "0003_consultation_nextaction_consultation_and_more")]
    new = [("operations", "0004_assessment_quote_quoterevision_nextaction_origin_key_and_more")]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_visit_and_action_survive_upgrade_reverse_reapply(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        old_apps = executor.loader.project_state(self.old).apps
        org = old_apps.get_model("operations", "Organization").objects.create(name="Existing studio")
        user = old_apps.get_model("auth", "User").objects.create(username="existing-staff")
        customer = old_apps.get_model("operations", "Customer").objects.create(organization_id=org.pk, name="Existing client")
        lead = old_apps.get_model("operations", "Lead").objects.create(organization_id=org.pk, customer_id=customer.pk)
        visit = old_apps.get_model("operations", "Consultation").objects.create(
            organization_id=org.pk, lead_id=lead.pk, assignee_id=user.pk,
            starts_at=timezone.now(), ends_at=timezone.now()+timedelta(hours=1),
            location="Existing site", status="COMPLETED", outcome="Existing observations")
        action = old_apps.get_model("operations", "NextAction").objects.create(
            organization_id=org.pk, lead_id=lead.pk, consultation_id=visit.pk,
            title="Existing visit action", done=True, version=2)
        executor = MigrationExecutor(connection)
        executor.migrate(self.new)
        new_apps = executor.loader.project_state(self.new).apps
        saved = new_apps.get_model("operations", "NextAction").objects.get(pk=action.pk)
        self.assertEqual(saved.origin_key, "")
        self.assertEqual(saved.consultation_id, visit.pk)
        self.assertTrue(saved.done)
        self.assertEqual(saved.version, 2)
        assessment = new_apps.get_model("operations", "Assessment").objects.create(
            organization_id=org.pk, consultation_id=visit.pk, scope="Draft observations")
        self.assertEqual(assessment.scope, "Draft observations")
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        old_apps = executor.loader.project_state(self.old).apps
        self.assertEqual(old_apps.get_model("operations", "Consultation").objects.get(pk=visit.pk).outcome,
                         "Existing observations")
        executor = MigrationExecutor(connection)
        executor.migrate(self.new)
        new_apps = executor.loader.project_state(self.new).apps
        self.assertEqual(new_apps.get_model("operations", "NextAction").objects.get(pk=action.pk).version, 2)
