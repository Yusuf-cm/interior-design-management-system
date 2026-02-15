from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Job
from .serializers import JobSerializer

class JobViewSet(viewsets.ModelViewSet):
    # Added this line to fix the AssertionError
    queryset = Job.objects.all() 
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer']
    search_fields = ['title', 'customer__name']
    ordering_fields = ['due_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Job.objects.all()
        # Staff only see jobs they are assigned to
        return Job.objects.filter(assigned_staff=user)

    def perform_create(self, serializer):
        serializer.save(assigned_staff=self.request.user)