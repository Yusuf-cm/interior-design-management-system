from django.test import TestCase
from . import test_execution as fixtures
from .models import Activity, NextAction, ScopeChange, Membership


class ScopeChangeTests(TestCase):
    setUpTestData = classmethod(fixtures.ExecutionWorkflowTests.setUpTestData.__func__)
    setUp = fixtures.ExecutionWorkflowTests.setUp
    make_quote = fixtures.ExecutionWorkflowTests.make_quote
    event = fixtures.ExecutionWorkflowTests.event
    accepted = fixtures.ExecutionWorkflowTests.accepted
    convert = fixtures.ExecutionWorkflowTests.convert
    project = fixtures.ExecutionWorkflowTests.project
    project_command = fixtures.ExecutionWorkflowTests.project_command

    def propose(self, project, **changes):
        return self.client.post(f'/api/projects/{project.pk}/changes/', {
            'title':'Add hallway', 'description':'Paint hallway as well', 'estimated_delta':'250.50',
            'schedule_days':2, 'note':'Customer requested additional scope', **changes},
            format='json', **self.headers)

    def decide(self, project, change, **changes):
        return self.client.post(f'/api/projects/{project.pk}/changes/{change.pk}/decision/', {
            'expected_version':change.version, 'command':'approve', 'reference':'Customer call reference 42',
            'note':'Customer agreed to scope, price and timing', **changes}, format='json', **self.headers)

    def test_approval_preserves_original_baseline_and_settles_review(self):
        project=self.project()
        response=self.propose(project)
        self.assertEqual(response.status_code,201,response.data)
        change=ScopeChange.objects.get(pk=response.data['id'])
        task=NextAction.objects.get(origin_key=f'project:{project.pk}:change-{change.pk}')
        self.assertFalse(task.done)
        self.assertEqual(task.assignee,self.owner)
        self.assertEqual(self.decide(project,change).status_code,200)
        task.refresh_from_db();self.assertTrue(task.done)
        self.revision.refresh_from_db()
        self.assertEqual(str(self.revision.total),'1500.00')
        self.assertEqual(self.revision.scope_snapshot,'Paint lounge walls')
        self.assertTrue(Activity.objects.filter(kind='SCOPE_CHANGE_DECIDED',details__scope_change_id=change.pk).exists())
        self.assertEqual(self.decide(project,change).status_code,409)

    def test_stale_decision_has_no_side_effects(self):
        project=self.project();change=ScopeChange.objects.get(pk=self.propose(project).data['id'])
        self.assertEqual(self.decide(project,change,expected_version=99).status_code,409)
        change.refresh_from_db();self.assertEqual(change.status,'PROPOSED')
        self.assertFalse(Activity.objects.filter(kind='SCOPE_CHANGE_DECIDED').exists())

    def test_required_evidence_and_finite_decimal_validation(self):
        project=self.project()
        for invalid in ['NaN','Infinity','1.001','10000000000000000.00']:
            self.assertEqual(self.propose(project,estimated_delta=invalid).status_code,400)
        change=ScopeChange.objects.get(pk=self.propose(project,estimated_delta='-25.00',schedule_days=-1).data['id'])
        self.assertEqual(self.decide(project,change,reference='').status_code,400)
        self.assertEqual(self.decide(project,change,note='').status_code,400)

    def test_coordinator_can_propose_but_only_owner_can_decide(self):
        project=self.project();self.client.force_authenticate(self.coordinator)
        response=self.propose(project);self.assertEqual(response.status_code,201)
        change=ScopeChange.objects.get(pk=response.data['id'])
        self.assertEqual(self.decide(project,change).status_code,403)
        self.client.force_authenticate(self.designer)
        self.assertEqual(self.propose(project).status_code,403)

    def test_foreign_organization_cannot_read_or_mutate_changes(self):
        project=self.project();change=ScopeChange.objects.get(pk=self.propose(project).data['id'])
        self.client.force_authenticate(self.foreign);self.headers={'HTTP_X_ORGANIZATION_ID':str(self.other.pk)}
        self.assertEqual(self.propose(project).status_code,404)
        self.assertEqual(self.decide(project,change).status_code,404)
        self.assertEqual(self.client.get(f'/api/projects/{project.pk}/',**self.headers).status_code,404)

    def test_field_project_response_hides_scope_changes(self):
        project=self.project();self.propose(project)
        fixtures.ExecutionWorkflowTests.add_work(self,project)
        self.client.force_authenticate(self.field)
        response=self.client.get(f'/api/projects/{project.pk}/',**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertNotIn('scope_changes',response.data)
        self.assertNotIn('accepted_total',response.data)
        self.assertEqual(self.propose(project).status_code,403)

    def test_rejected_and_withdrawn_decisions_cancel_review(self):
        project=self.project()
        for command in ['reject','withdraw']:
            change=ScopeChange.objects.get(pk=self.propose(project).data['id'])
            self.assertEqual(self.decide(project,change,command=command).status_code,200)
            task=NextAction.objects.get(origin_key=f'project:{project.pk}:change-{change.pk}')
            self.assertTrue(task.cancelled);self.assertFalse(task.done)

    def test_cancellation_withdraws_pending_changes_and_tasks(self):
        project=self.project();change=ScopeChange.objects.get(pk=self.propose(project).data['id'])
        self.assertEqual(self.project_command(project,'cancel').status_code,200)
        self.assertEqual(self.propose(project).status_code,409)
        self.assertEqual(self.decide(project,change).status_code,409)
        change.refresh_from_db();self.assertEqual(change.status,'WITHDRAWN')
        self.assertTrue(NextAction.objects.get(origin_key=f'project:{project.pk}:change-{change.pk}').cancelled)

    def test_inactive_membership_cannot_propose(self):
        project=self.project()
        Membership.objects.filter(organization=self.org,user=self.owner).update(active=False)
        self.assertEqual(self.propose(project).status_code,403)
