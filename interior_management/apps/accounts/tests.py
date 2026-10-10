from rest_framework.test import APITestCase
from .models import User
from apps.customers.models import Customer
from apps.jobs.models import Job


class StaffPermissionsTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='test-password')
        self.other = User.objects.create_user(username='other', password='test-password')
        self.admin = User.objects.create_user(username='owner', password='test-password', role='admin')
        self.own_customer = Customer.objects.create(name='Own customer', email='own@example.com', phone='0700000000', address='Test', created_by=self.staff)
        self.other_customer = Customer.objects.create(name='Other customer', email='other@example.com', phone='0700000001', address='Test', created_by=self.other)
        self.own_job = Job.objects.create(customer=self.own_customer, title='Own project', assigned_staff=self.staff, estimated_cost=100, actual_payment_received=40)
        self.other_job = Job.objects.create(customer=self.other_customer, title='Private project', assigned_staff=self.other, estimated_cost=900, actual_payment_received=600)
        self.client.force_authenticate(self.staff)

    def test_profile_cannot_promote_staff_or_change_identity(self):
        response = self.client.patch('/api/accounts/profile/', {'role': 'admin', 'username': 'owner2', 'first_name': 'Updated'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.role, User.IS_STAFF)
        self.assertEqual(self.staff.username, 'staff')
        self.assertEqual(self.staff.first_name, 'Updated')
        self.assertEqual(self.client.post('/api/accounts/register/', {}, format='json').status_code, 403)

    def test_staff_dashboard_only_reports_assigned_jobs(self):
        response = self.client.get('/api/dashboard/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['metrics']['total_customers'], 1)
        self.assertEqual(response.data['metrics']['total_jobs'], 1)
        self.assertEqual(response.data['financials']['total_revenue'], 40)
        self.assertEqual(response.data['financials']['pending_revenue'], 60)
        self.assertEqual([j['id'] for j in response.data['recent_activity']], [self.own_job.id])

    def test_admin_dashboard_reports_all_jobs(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/dashboard/summary/')
        self.assertEqual(response.data['metrics']['total_jobs'], 2)
        self.assertEqual(response.data['financials']['total_revenue'], 640)

    def test_staff_cannot_reassign_job(self):
        response = self.client.patch(f'/api/jobs/{self.own_job.id}/', {'assigned_staff': self.other.id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.own_job.refresh_from_db()
        self.assertEqual(self.own_job.assigned_staff_id, self.staff.id)

    def test_staff_cannot_link_another_users_customer(self):
        response = self.client.patch(f'/api/jobs/{self.own_job.id}/', {'customer': self.other_customer.id}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_staff_cannot_read_another_users_job(self):
        self.assertEqual(self.client.get(f'/api/jobs/{self.other_job.id}/').status_code, 404)

    def test_register_rejects_unknown_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/accounts/register/', {'username': 'new', 'email': 'new@example.com', 'password': 'test-password', 'role': 'invented'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_negative_financial_values_are_rejected(self):
        for field in ['estimated_cost', 'actual_payment_received']:
            response = self.client.patch(f'/api/jobs/{self.own_job.id}/', {field: -1}, format='json')
            self.assertEqual(response.status_code, 400, field)

    def test_staff_cannot_change_another_jobs_payment(self):
        response = self.client.patch(f'/api/jobs/{self.other_job.id}/', {'actual_payment_received': 0}, format='json')
        self.assertEqual(response.status_code, 404)
        self.other_job.refresh_from_db()
        self.assertEqual(self.other_job.actual_payment_received, 600)
