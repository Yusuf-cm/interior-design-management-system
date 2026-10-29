from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MembershipVersionMigrationTests(TransactionTestCase):
    old = [('operations','0004_assessment_quote_quoterevision_nextaction_origin_key_and_more')]
    new = [('operations','0005_membership_version')]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_company_role_and_access_survive_forward_reverse_reapply(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        apps = executor.loader.project_state(self.old).apps
        user = apps.get_model('auth','User').objects.create(username='existing-member')
        org = apps.get_model('operations','Organization').objects.create(name='Existing studio')
        member = apps.get_model('operations','Membership').objects.create(
            organization_id=org.pk,user_id=user.pk,role='DESIGNER',active=False)
        for target in [self.new,self.old,self.new]:
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            model = executor.loader.project_state(target).apps.get_model('operations','Membership')
            saved = model.objects.get(pk=member.pk)
            self.assertEqual(saved.organization_id,org.pk)
            self.assertEqual(saved.user_id,user.pk)
            self.assertEqual(saved.role,'DESIGNER')
            self.assertFalse(saved.active)
            if target==self.new:
                self.assertEqual(saved.version,1)
