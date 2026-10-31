from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (Activity, Assessment, Consultation, Customer, Lead, Membership, NextAction,
                     Organization, Project, Quote, QuoteEvent, QuoteRevision, WorkItem)


class ExecutionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("execution-owner")
        cls.coordinator = User.objects.create_user("execution-coordinator")
        cls.designer = User.objects.create_user("execution-designer")
        cls.field = User.objects.create_user("execution-field")
        cls.other_field = User.objects.create_user("execution-other-field")
        cls.foreign = User.objects.create_user("execution-foreign-owner")
        cls.org = Organization.objects.create(name="Nuru Interiors")
        cls.other = Organization.objects.create(name="Other Studio")
        for user, role in [(cls.owner,"OWNER"),(cls.coordinator,"COORDINATOR"),
                           (cls.designer,"DESIGNER"),(cls.field,"FIELD"),(cls.other_field,"FIELD")]:
            Membership.objects.create(organization=cls.org,user=user,role=role)
        Membership.objects.create(organization=cls.other,user=cls.foreign,role="OWNER")

    def make_quote(self, org, user, name):
        customer = Customer.objects.create(organization=org,name=name)
        lead = Lead.objects.create(organization=org,customer=customer,status="ASSESSED")
        visit = Consultation.objects.create(organization=org,lead=lead,assignee=user,location="Site",
            starts_at=timezone.now()-timedelta(hours=2),ends_at=timezone.now()-timedelta(hours=1),status="COMPLETED")
        assessment = Assessment.objects.create(organization=org,consultation=visit,
            scope="Paint lounge walls",status="READY_FOR_ESTIMATE",version=2)
        quote = Quote.objects.create(organization=org,assessment=assessment,currency="KES",
                                     status="APPROVED_TO_SHARE",version=3)
        revision = QuoteRevision.objects.create(organization=org,quote=quote,number=1,assessment_version=2,
            scope_snapshot="Paint lounge walls",currency="KES",
            items=[{"description":"Paint","quantity":"1.000","unit_price":"1500.00","amount":"1500.00"}],
            subtotal=Decimal("1500"),discount=0,tax_rate=0,tax=0,total=Decimal("1500"))
        quote.current_revision = revision
        quote.save()
        return lead, assessment, quote, revision

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.headers = {"HTTP_X_ORGANIZATION_ID":str(self.org.pk)}
        self.lead,self.assessment,self.quote,self.revision = self.make_quote(self.org,self.owner,"Amina")

    def event(self, kind, **changes):
        self.quote.refresh_from_db()
        data = {"expected_version":self.quote.version,"kind":kind,
                "reference":"Local test conversation","note":"Staff recorded customer communication",
                "occurred_at":timezone.now().isoformat(),**changes}
        if kind=="SHARED":
            data.setdefault("follow_up_due_at",(timezone.now()+timedelta(days=2)).isoformat())
        return self.client.post(f"/api/quotes/{self.quote.pk}/events/",data,format="json",**self.headers)

    def accepted(self):
        self.assertEqual(self.event("SHARED").status_code,200)
        self.assertEqual(self.event("ACCEPTED").status_code,200)
        self.quote.refresh_from_db()

    def convert(self, **changes):
        return self.client.post(f"/api/quotes/{self.quote.pk}/project/",
            {"expected_version":self.quote.version,"title":"Amina lounge","owner":self.owner.pk,
             "start_date":"2026-11-02","target_date":"2026-11-15","note":"Plan agreed scope",**changes},
            format="json",**self.headers)

    def project(self):
        self.accepted()
        response=self.convert()
        self.assertEqual(response.status_code,201)
        return Project.objects.get(pk=response.json()["id"])

    def project_command(self, project, command, **changes):
        project.refresh_from_db()
        return self.client.post(f"/api/projects/{project.pk}/command/",
            {"expected_version":project.version,"command":command,"note":"Project update",**changes},
            format="json",**self.headers)

    def add_work(self, project, **changes):
        return self.client.post(f"/api/projects/{project.pk}/work/",
            {"title":"Prepare walls","description":"Protect floor and prepare surfaces",
             "assignee":self.field.pk,"due_at":None,"note":"Plan preparation",**changes},
            format="json",**self.headers)

    def work_command(self, work, command, **changes):
        work.refresh_from_db()
        return self.client.post(f"/api/work/{work.pk}/command/",
            {"expected_version":work.version,"command":command,"note":"Recorded work update",**changes},
            format="json",**self.headers)

    def test_internal_approval_does_not_automatically_create_project_or_customer_event(self):
        self.assertFalse(Project.objects.exists())
        self.assertFalse(QuoteEvent.objects.exists())
        self.assertEqual(self.convert().status_code,409)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status,"ASSESSED")

    def test_manual_sharing_advances_inquiry_and_schedules_explicit_follow_up(self):
        due=timezone.now()+timedelta(days=3)
        response=self.event("SHARED",follow_up_due_at=due.isoformat())
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["status"],"SENT")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status,"QUOTED")
        task=NextAction.objects.get(origin_key=f"quote:{self.quote.pk}:reply")
        self.assertEqual(task.due_at,due)
        self.assertEqual(QuoteEvent.objects.get().revision_id,self.revision.pk)

    def test_event_requires_actual_time_reference_and_future_follow_up(self):
        for changes in [{"reference":""},{"note":" "},{"occurred_at":(timezone.now()+timedelta(days=1)).isoformat()},
                        {"follow_up_due_at":timezone.now().isoformat()}]:
            self.assertEqual(self.event("SHARED",**changes).status_code,400)
        self.assertFalse(QuoteEvent.objects.exists())

    def test_unreviewed_or_changed_source_cannot_be_recorded_as_shared(self):
        self.quote.status="DRAFT";self.quote.save()
        self.assertEqual(self.event("SHARED").status_code,409)
        self.quote.status="APPROVED_TO_SHARE";self.quote.save()
        self.assessment.version=3;self.assessment.save()
        self.assertEqual(self.event("SHARED").status_code,409)

    def test_customer_approval_requires_recorded_sharing(self):
        self.assertEqual(self.event("ACCEPTED").status_code,409)
        self.assertEqual(self.event("SHARED").status_code,200)
        before_share=timezone.now()-timedelta(minutes=1)
        self.assertEqual(self.event("ACCEPTED",occurred_at=before_share.isoformat()).status_code,400)

    def test_only_owner_can_record_customer_approval(self):
        self.event("SHARED")
        self.client.force_authenticate(user=self.coordinator)
        self.assertEqual(self.event("ACCEPTED").status_code,403)
        self.client.force_authenticate(user=self.field)
        self.assertEqual(self.event("ACCEPTED").status_code,403)

    def test_duplicate_event_is_conflict_without_extra_follow_up(self):
        version=self.quote.version
        self.event("SHARED")
        self.assertEqual(self.event("SHARED",expected_version=version).status_code,409)
        self.assertEqual(QuoteEvent.objects.count(),1)
        self.assertEqual(NextAction.objects.filter(origin_key=f"quote:{self.quote.pk}:reply").count(),1)

    def test_customer_change_request_allows_new_revision_without_overwriting_shared_prices(self):
        self.event("SHARED")
        self.event("REVISION_REQUESTED",note="Customer wants another finish")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status,"REVISION_REQUESTED")
        response=self.client.post(f"/api/quotes/{self.quote.pk}/revisions/",
            {"expected_version":self.quote.version,"expected_assessment_version":2,
             "items":[{"description":"New finish","quantity":"1","unit_price":"2000"}],"note":"Revised finish"},
            format="json",**self.headers)
        self.assertEqual(response.status_code,201)
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.total,Decimal("1500.00"))
        self.assertEqual(response.json()["current_revision"]["total"],"2000.00")

    def test_shared_quote_cannot_be_silently_revised(self):
        self.event("SHARED")
        self.quote.refresh_from_db()
        response=self.client.post(f"/api/quotes/{self.quote.pk}/revisions/",
            {"expected_version":self.quote.version,"expected_assessment_version":2,
             "items":[{"description":"Other","quantity":"1","unit_price":"2000"}],"note":"Skip response"},
            format="json",**self.headers)
        self.assertEqual(response.status_code,409)
        self.assertEqual(QuoteRevision.objects.count(),1)

    def test_decline_does_not_falsify_acceptance_or_create_project(self):
        self.event("SHARED")
        self.assertEqual(self.event("REJECTED").status_code,200)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status,"REJECTED")
        self.assertFalse(Project.objects.exists())
        self.assertTrue(NextAction.objects.filter(title="Review declined quotation").exists())

    def test_conversion_is_idempotent_and_preserves_accepted_revision(self):
        project=self.project()
        response=self.convert(title="Attempted duplicate",expected_version=1)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["id"],project.pk)
        self.assertEqual(response.json()["title"],"Amina lounge")
        self.assertEqual(Project.objects.count(),1)
        self.assertEqual(project.accepted_revision_id,self.revision.pk)
        self.assertEqual(project.accepted_revision.total,Decimal("1500.00"))
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status,"WON")

    def test_conversion_rejects_foreign_owner_invalid_dates_and_stale_version(self):
        self.accepted()
        for changes in [{"owner":self.foreign.pk},{"owner":self.field.pk},
                        {"target_date":"2026-11-01"},{"expected_version":1}]:
            self.assertIn(self.convert(**changes).status_code,[400,409])
        self.assertFalse(Project.objects.exists())

    def test_conversion_requires_owner_and_recorded_approval_evidence(self):
        self.accepted()
        self.client.force_authenticate(user=self.coordinator)
        self.assertEqual(self.convert().status_code,403)
        self.client.force_authenticate(user=self.owner)
        QuoteEvent.objects.filter(kind="ACCEPTED").delete()
        self.assertEqual(self.convert().status_code,409)

    def test_work_planning_generates_one_linked_daily_action(self):
        project=self.project()
        response=self.add_work(project)
        self.assertEqual(response.status_code,201)
        work=WorkItem.objects.get()
        task=NextAction.objects.get(work_item=work)
        self.assertEqual(task.origin_key,f"work:{work.pk}:execute")
        self.assertEqual(task.assignee_id,self.field.pk)
        self.assertIsNone(task.due_at)

    def test_project_must_be_active_for_start_or_completion(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.assertEqual(self.work_command(work,"start").status_code,409)
        self.assertEqual(self.project_command(project,"start").status_code,200)
        self.assertEqual(self.work_command(work,"start").status_code,200)
        self.assertEqual(self.project_command(project,"pause").status_code,200)
        self.assertEqual(self.work_command(work,"done").status_code,409)
        self.assertEqual(self.project_command(project,"resume").status_code,200)
        self.assertEqual(self.work_command(work,"done").status_code,200)
        self.assertTrue(NextAction.objects.get(work_item=work).done)

    def test_blocker_and_recovery_are_audited_and_visible(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.project_command(project,"start")
        self.client.force_authenticate(user=self.field)
        self.work_command(work,"start")
        response=self.work_command(work,"block",note="Paint delivery delayed")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["blocker_reason"],"Paint delivery delayed")
        self.assertTrue(NextAction.objects.get(work_item=work).title.startswith("Blocked:"))
        self.assertEqual(self.work_command(work,"unblock").status_code,200)
        work.refresh_from_db()
        self.assertEqual(work.blocker_reason,"")
        self.assertTrue(Activity.objects.filter(kind="WORK_ITEM_STATUS_CHANGED").exists())

    def test_field_project_data_excludes_prices_and_other_staff_work(self):
        project=self.project()
        mine=self.add_work(project).json()["id"]
        self.add_work(project,title="Private other staff task",assignee=self.other_field.pk)
        self.client.force_authenticate(user=self.field)
        response=self.client.get(f"/api/projects/{project.pk}/",**self.headers)
        self.assertEqual(response.status_code,200)
        data=response.json()
        for key in ["accepted_total","currency","accepted_revision","quote","scope","history","lead"]:
            self.assertNotIn(key,data)
        self.assertEqual([row["id"] for row in data["work_items"]],[mine])
        self.assertNotIn("Private other staff",response.content.decode())
        self.assertEqual(data["open_items"],1)

    def test_unassigned_field_staff_cannot_open_or_modify_project(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.client.force_authenticate(user=self.other_field)
        self.assertEqual(self.client.get(f"/api/projects/{project.pk}/",**self.headers).status_code,404)
        self.assertEqual(self.client.get("/api/projects/",**self.headers).json(),[])
        self.assertEqual(self.work_command(work,"block").status_code,404)

    def test_field_cannot_plan_cancel_reassign_or_reopen_work(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.client.force_authenticate(user=self.field)
        self.assertEqual(self.add_work(project).status_code,403)
        self.assertEqual(self.project_command(project,"start").status_code,403)
        self.assertEqual(self.work_command(work,"cancel").status_code,403)
        response=self.client.patch(f"/api/work/{work.pk}/",
            {"expected_version":1,"note":"Reassign","assignee":self.other_field.pk},
            format="json",**self.headers)
        self.assertEqual(response.status_code,403)

    def test_invalid_or_inactive_assignee_cannot_receive_work(self):
        project=self.project()
        self.assertEqual(self.add_work(project,assignee=self.foreign.pk).status_code,400)
        Membership.objects.filter(user=self.field,organization=self.org).update(active=False)
        self.assertEqual(self.add_work(project).status_code,400)
        self.assertEqual(self.add_work(project,assignee=None).status_code,201)

    def test_stale_work_updates_and_generic_completion_cannot_bypass_workflow(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        response=self.client.patch(f"/api/work/{work.pk}/",
            {"expected_version":1,"note":"Changed plan","title":"Different preparation"},
            format="json",**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.work_command(work,"block",expected_version=1).status_code,409)
        action=NextAction.objects.get(work_item=work)
        response=self.client.post(f"/api/actions/{action.pk}/complete/",
            {"expected_version":action.version,"note":"Skip workflow"},format="json",**self.headers)
        self.assertEqual(response.status_code,409)

    def test_cancellation_preserves_completed_items_and_cancels_open_work(self):
        project=self.project()
        completed=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        pending=WorkItem.objects.get(pk=self.add_work(project,title="Open task").json()["id"])
        self.project_command(project,"start")
        self.work_command(completed,"start")
        self.work_command(completed,"done")
        self.assertEqual(self.project_command(project,"cancel").status_code,200)
        completed.refresh_from_db();pending.refresh_from_db()
        self.assertEqual(completed.status,"DONE")
        self.assertEqual(pending.status,"CANCELLED")
        self.assertTrue(NextAction.objects.get(work_item=pending).cancelled)
        self.assertEqual(self.work_command(pending,"reopen").status_code,409)
        self.assertEqual(self.add_work(project).status_code,409)

    def test_manager_can_reopen_completed_work_without_duplicate_task(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.project_command(project,"start")
        self.work_command(work,"start");self.work_command(work,"done")
        self.assertEqual(self.work_command(work,"reopen").status_code,200)
        self.assertEqual(NextAction.objects.filter(work_item=work).count(),1)
        self.assertFalse(NextAction.objects.get(work_item=work).done)

    def test_cross_company_project_work_and_quote_ids_are_hidden(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()["id"])
        self.client.force_authenticate(user=self.foreign)
        self.headers={"HTTP_X_ORGANIZATION_ID":str(self.other.pk)}
        self.assertEqual(self.client.get("/api/projects/",**self.headers).json(),[])
        for path in [f"/api/projects/{project.pk}/",f"/api/work/{work.pk}/"]:
            self.assertEqual(self.client.get(path,**self.headers).status_code,404)
        self.assertEqual(self.project_command(project,"start").status_code,404)
        self.assertEqual(self.work_command(work,"block").status_code,404)
        self.assertEqual(self.convert().status_code,404)
        self.assertEqual(self.event("SHARED").status_code,404)

    def test_inactive_membership_blocks_execution_access(self):
        project=self.project()
        Membership.objects.filter(user=self.owner,organization=self.org).update(active=False)
        self.assertEqual(self.client.get("/api/projects/",**self.headers).status_code,403)
        self.assertEqual(self.project_command(project,"start").status_code,403)

    def test_project_cannot_claim_completion_without_handover_workflow(self):
        project=self.project()
        self.assertEqual(self.project_command(project,"complete").status_code,400)
        project.refresh_from_db()
        self.assertEqual(project.status,"PLANNED")

    def test_full_approved_quote_to_assigned_work_completion(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project,title="Prepare and paint lounge").json()["id"])
        self.assertEqual(self.project_command(project,"start").status_code,200)
        self.client.force_authenticate(user=self.field)
        self.assertEqual(self.work_command(work,"start").status_code,200)
        self.assertEqual(self.work_command(work,"block",note="Awaiting paint").status_code,200)
        self.assertEqual(self.work_command(work,"unblock",note="Paint delivered").status_code,200)
        self.assertEqual(self.work_command(work,"done",note="Walls prepared and painted").status_code,200)
        self.client.force_authenticate(user=self.owner)
        data=self.client.get(f"/api/projects/{project.pk}/",**self.headers).json()
        self.assertEqual(data["accepted_total"],"1500.00")
        self.assertEqual(data["open_items"],0)
        self.assertEqual(data["status"],"ACTIVE")
        self.assertEqual(data["work_items"][0]["status"],"DONE")
        self.assertEqual(Project.objects.count(),1)

    def test_customer_approval_can_restore_dormant_shared_inquiry(self):
        self.event('SHARED')
        self.lead.refresh_from_db()
        response=self.client.post(f'/api/leads/{self.lead.pk}/transition/',
            {'expected_version':self.lead.version,'status':'DORMANT','note':'Waiting for customer'},
            format='json',**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.event('ACCEPTED').status_code,200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status,'WON')

    def test_accepted_source_cannot_be_reopened_or_revised(self):
        self.accepted()
        response=self.client.post(f'/api/assessments/{self.assessment.pk}/command/',
            {'expected_version':2,'command':'reopen','note':'Silently change accepted scope'},
            format='json',**self.headers)
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.revision.total,Decimal('1500.00'))

    def test_linked_work_plan_cannot_be_changed_through_generic_action_endpoint(self):
        project=self.project()
        work=WorkItem.objects.get(pk=self.add_work(project).json()['id'])
        action=NextAction.objects.get(work_item=work)
        response=self.client.patch(f'/api/actions/{action.pk}/',
            {'expected_version':action.version,'title':'Conflicting title','note':'Bypass work planning'},
            format='json',**self.headers)
        self.assertEqual(response.status_code,409)
        work.refresh_from_db()
        self.assertEqual(work.title,'Prepare walls')

    def test_shared_follow_up_can_be_rescheduled_without_new_customer_event(self):
        response=self.event('SHARED')
        follow_up=response.json()['customer_follow_up']
        due=timezone.now()+timedelta(days=4)
        response=self.client.patch(f"/api/actions/{follow_up['id']}/",
            {'expected_version':follow_up['version'],'due_at':due.isoformat(),'note':'Customer asked for more time'},
            format='json',**self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(QuoteEvent.objects.count(),1)
        self.assertEqual(NextAction.objects.get(pk=follow_up['id']).due_at,due)

    def test_blocked_daily_label_respects_database_title_limit(self):
        project=self.project()
        title='A'*180
        work=WorkItem.objects.get(pk=self.add_work(project,title=title).json()['id'])
        self.assertEqual(self.work_command(work,'block',note='Materials unavailable').status_code,200)
        action=NextAction.objects.get(work_item=work)
        self.assertLessEqual(len(action.title),180)
        self.assertTrue(action.title.startswith('Blocked:'))
        work.refresh_from_db()
        self.assertEqual(work.title,title)

    def correction(self, **changes):
        self.quote.refresh_from_db()
        return self.client.post(f'/api/quotes/{self.quote.pk}/approval-correction/',
            {'expected_version':self.quote.version,'reference':'Clerical correction',
             'note':'Approval was entered against the wrong conversation',
             'follow_up_due_at':(timezone.now()+timedelta(days=1)).isoformat(),**changes},
            format='json',**self.headers)

    def test_approval_correction_before_conversion_preserves_original_history(self):
        self.accepted()
        response=self.correction()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['status'],'SENT')
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status,'QUOTED')
        self.assertEqual(QuoteEvent.objects.filter(kind='ACCEPTED').count(),1)
        self.assertEqual(QuoteEvent.objects.filter(kind='APPROVAL_CORRECTED').count(),1)
        self.assertEqual(self.convert().status_code,409)
        self.assertEqual(self.event('ACCEPTED').status_code,200)
        self.assertEqual(QuoteEvent.objects.filter(kind='ACCEPTED').count(),2)
        self.quote.refresh_from_db()
        self.assertEqual(self.convert().status_code,201)

    def test_converted_approval_cannot_be_rewritten_by_correction(self):
        self.project()
        self.assertEqual(self.correction().status_code,409)
        self.assertEqual(QuoteEvent.objects.filter(kind='APPROVAL_CORRECTED').count(),0)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status,'ACCEPTED')

    def test_correction_requires_owner_and_current_version(self):
        self.accepted()
        self.client.force_authenticate(user=self.coordinator)
        self.assertEqual(self.correction().status_code,403)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.correction(expected_version=1).status_code,409)
        self.assertEqual(self.correction(note=' ').status_code,400)

    def test_correction_kind_cannot_bypass_the_dedicated_guarded_endpoint(self):
        self.accepted()
        self.assertIn(self.event('APPROVAL_CORRECTED').status_code,[400,409])
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status,'ACCEPTED')
