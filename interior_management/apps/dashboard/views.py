from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models  # <--- Added this
from django.db.models import Sum, Count
from apps.customers.models import Customer
from apps.jobs.models import Job

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Customer Metrics
        visible_customers = Customer.objects.all() if request.user.role == 'admin' else Customer.objects.filter(created_by=request.user)
        visible_jobs = Job.objects.all() if request.user.role == 'admin' else Job.objects.filter(assigned_staff=request.user)
        total_customers = visible_customers.count()
        
        # 2. Job Metrics using Aggregation
        job_stats = visible_jobs.aggregate(
            total_jobs=Count('id'),
            active_jobs=Count('id', filter=models.Q(status='ACTIVE')),
            completed_jobs=Count('id', filter=models.Q(status='COMPLETED')),
            total_est_revenue=Sum('estimated_cost'),
            total_actual_revenue=Sum('actual_payment_received')
        )

        # 3. Financial Calculations
        actual_revenue = job_stats['total_actual_revenue'] or 0
        estimated_revenue = job_stats['total_est_revenue'] or 0
        pending_revenue = estimated_revenue - actual_revenue

        # 4. Recent Activity (Corrected order_by)
        recent_jobs = visible_jobs.select_related('customer').order_by('-created_at')[:5]
        recent_jobs_data = [
            {
                "id": job.id,
                "title": job.title,
                "customer": job.customer.name,
                "status": job.status,
                "created_at": job.created_at
            } for job in recent_jobs
        ]

        return Response({
            "metrics": {
                "total_customers": total_customers,
                "total_jobs": job_stats['total_jobs'],
                "active_jobs": job_stats['active_jobs'],
                "completed_jobs": job_stats['completed_jobs'],
            },
            "financials": {
                "total_revenue": actual_revenue,
                "pending_revenue": pending_revenue,
            },
            "recent_activity": recent_jobs_data
        })