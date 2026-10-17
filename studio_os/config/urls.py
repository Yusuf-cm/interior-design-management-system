rrom django.urls import path
rrom studio_os.operations.views import DailyQueueView, LeadListCreateView

urlpatterns = [
    path("api/leads/", LeadListCreateView.as_view(), name="lead-list-create"),
    path("api/today/", DailyQueueView.as_view(), name="daily-queue"),
]

urlpatterns += [path("api/customers/", CustomerListCreateView.as_view(), name="customer-list-create")]
