from datetime import timedelta
from decimal import Decimal
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ExecutionMigrationTests(TransactionTestCase):
    old=[('operations','0005_membership_version')]
    new=[('operations','0006_alter_quote_status_project_quoteevent_workitem_and_more')]

    def tearDown(self):
        executor=MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_old_approval_is_preserved_without_inventing_customer_acceptance(self):
        executor=MigrationExecutor(connection);executor.migrate(self.old)
        apps=executor.loader.project_state(self.old).apps
        user=apps.get_model('auth','User').objects.create(username='migration-owner')
        org=apps.get_model('operations','Organization').objects.create(name='Existing studio')
        customer=apps.get_model('operations','Customer').objects.create(organization_id=org.pk,name='Existing customer')
        lead=apps.get_model('operations','Lead').objects.create(organization_id=org.pk,customer_id=customer.pk,status='ASSESSED')
        visit=apps.get_model('operations','Consultation').objects.create(organization_id=org.pk,lead_id=lead.pk,
            assignee_id=user.pk,location='Existing site',starts_at=timezone.now()-timedelta(hours=2),
            ends_at=timezone.now()-timedelta(hours=1),status='COMPLETED')
        assessment=apps.get_model('operations','Assessment').objects.create(organization_id=org.pk,
            consultation_id=visit.pk,scope='Existing scope',status='READY_FOR_ESTIMATE')
        quote=apps.get_model('operations','Quote').objects.create(organization_id=org.pk,assessment_id=assessment.pk,
            currency='KES',status='APPROVED_TO_SHARE',version=3)
        revision=apps.get_model('operations','QuoteRevision').objects.create(organization_id=org.pk,quote_id=quote.pk,
            number=1,assessment_version=1,scope_snapshot='Existing scope',currency='KES',
            subtotal=Decimal('1500'),discount=0,tax_rate=0,tax=0,total=Decimal('1500'))
        quote.current_revision_id=revision.pk;quote.save()
        task=apps.get_model('operations','NextAction').objects.create(organization_id=org.pk,lead_id=lead.pk,
            title='Existing follow-up',done=True)
        for target in [self.new,self.old,self.new]:
            executor=MigrationExecutor(connection);executor.migrate(target)
            apps=executor.loader.project_state(target).apps
            saved=apps.get_model('operations','Quote').objects.get(pk=quote.pk)
            self.assertEqual(saved.status,'APPROVED_TO_SHARE')
            self.assertEqual(saved.current_revision_id,revision.pk)
            self.assertEqual(saved.version,3)
            self.assertEqual(apps.get_model('operations','QuoteRevision').objects.get(pk=revision.pk).total,Decimal('1500.00'))
            self.assertTrue(apps.get_model('operations','NextAction').objects.get(pk=task.pk).done)
            if target==self.new:
                self.assertFalse(apps.get_model('operations','Project').objects.exists())
                self.assertFalse(apps.get_model('operations','QuoteEvent').objects.exists())
                self.assertIsNone(apps.get_model('operations','NextAction').objects.get(pk=task.pk).work_item_id)
