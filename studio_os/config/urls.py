from django.urls import path
from studio_os.operations.views import DailyQueueView, LeadListCreateView

urlpatterns = [
    path("api/leads/", LeadListCreateView.as_view(), name="lead-list-create"),
    path("api/today/", DailyQueueView.as_view(), name="daily-queue"),
]
