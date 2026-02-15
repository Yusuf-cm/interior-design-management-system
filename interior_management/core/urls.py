from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse # Add this import

# Simple view for Render's health check
def health_check(request):
    return HttpResponse("Studio.OS API is Running", status=200)

urlpatterns = [
    path('', health_check), # This is the "Heartbeat" for Render
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/jobs/', include('apps.jobs.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
]