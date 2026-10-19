from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ConsultationMigrationTests(TransactionTestCase):
    """Rehearse the new migration with existing inquiry/action records."""
    old_target = [("operations", "0002_lead_version_nextaction_cancelled_nextaction_version")]
    new_target = [("operations", "0003_consultation_nextaction_consultation_and_more")]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_upgrade_and_reverse_preserve_existing_actions(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old_target)
        apps = executor.loader.project_state(self.old_target).apps
        org = apps.get_model("operations", "Organization").objects.create(name="Existing studio")
        customer = apps.get_model("operations", "Customer").objects.create(
            organization_id=org.pk, name="Existing customer")
        lead = apps.get_model("operations", "Lead").objects.create(
            organization_id=org.pk, customer_id=customer.pk, brief="Existing scope", version=3)
        action = apps.get_model("operations", "NextAction").objects.create(
            organization_id=org.pk, lead_id=lead.pk, title="Existing task", done=True, version=4)
        executor = MigrationExecutor(connection)
        executor.migrate(self.new_target)
        upgraded_apps = executor.loader.project_state(self.new_target).apps
        Lead = upgraded_apps.get_model("operations", "Lead")
        NextAction = upgraded_apps.get_model("operations", "NextAction")
        saved = NextAction.objects.get(pk=action.pk)
        self.assertIsNone(saved.consultation_id)
        self.assertTrue(saved.done)
        self.assertEqual(saved.version, 4)
        self.assertEqual(Lead.objects.get(pk=lead.pk).brief, "Existing scope")
        executor = MigrationExecutor(connection)
        executor.migrate(self.old_target)
        old_apps = executor.loader.project_state(self.old_target).apps
        saved = old_apps.get_model("operations", "NextAction").objects.get(pk=action.pk)
        self.assertEqual(saved.title, "Existing task")
        self.assertEqual(saved.version, 4)
        executor = MigrationExecutor(connection)
        executor.migrate(self.new_target)
        self.assertEqual(NextAction.objects.get(pk=action.pk).organization_id, org.pk)
