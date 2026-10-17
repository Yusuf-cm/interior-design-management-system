from django.urls import path
from studio_os.operations.views import (
    CustomerListCreateView, DailyQueueView, LeadListCreateView,
    LeadDetailView, ActionCompleteView, LeadTransitionView, ActionCreateView, ActionUpdateView,
)

urlpatterns = [
    path("api/customers/", CustomerListCreateView.as_view()),
    path("api/leads/", LeadListCreateView.as_view()),
    path("api/leads/<int:pk>/", LeadDetailView.as_view()),
    path("api/leads/<int:pk>/transition/", LeadTransitionView.as_view()),
    path("api/leads/<int:pk>/actions/", ActionCreateView.as_view()),
    path("api/actions/<int:pk>/", ActionUpdateView.as_view()),
    path("api/today/", DailyQueueView.as_view()),
    path("api/actions/<int:pk>/complete/", ActionCompleteView.as_view()),
]
