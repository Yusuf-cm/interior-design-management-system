from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer
from .serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    # Professional touch: Add search and filtering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['email']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Customer.objects.all()
        # Staff only see customers they created
        return Customer.objects.filter(created_by=user)

    def perform_create(self, serializer):
        # Automatically set the created_by field to the logged-in user
        serializer.save(created_by=self.request.user)