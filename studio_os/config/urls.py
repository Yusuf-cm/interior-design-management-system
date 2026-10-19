from django.urls import path
from studio_os.operations.views import (
    CustomerListCreateView, DailyQueueView, LeadListCreateView,
    LeadDetailView, ActionCompleteView, LeadTransitionView, ActionCreateView, ActionUpdateView,
)

from studio_os.operations.consultations import (
    ConsultationListView, ConsultationCreateView, ConsultationCommandView,
)

from studio_os.operations.assessments import (
    AssessmentCreateView, AssessmentDetailView, AssessmentCommandView,
)
from studio_os.operations.quotes import (
    QuoteCreateView, QuoteDetailView, QuoteRevisionView, QuoteReviewView,
)

from studio_os.operations.workspace import workspace, session, sign_in, sign_out, StaffDirectoryView

urlpatterns = [
    path("", workspace, name="studio-workspace"),
    path("api/session/", session),
    path("api/session/login/", sign_in),
    path("api/session/logout/", sign_out),
    path("api/staff/", StaffDirectoryView.as_view()),
    path("api/consultations/<int:pk>/assessment/", AssessmentCreateView.as_view()),
    path("api/assessments/<int:pk>/", AssessmentDetailView.as_view()),
    path("api/assessments/<int:pk>/command/", AssessmentCommandView.as_view()),
    path("api/assessments/<int:pk>/quote/", QuoteCreateView.as_view()),
    path("api/quotes/<int:pk>/", QuoteDetailView.as_view()),
    path("api/quotes/<int:pk>/revisions/", QuoteRevisionView.as_view()),
    path("api/quotes/<int:pk>/review/", QuoteReviewView.as_view()),
    path('api/consultations/', ConsultationListView.as_view()),
    path('api/leads/<int:pk>/consultations/', ConsultationCreateView.as_view()),
    path('api/consultations/<int:pk>/command/', ConsultationCommandView.as_view()),
    path("api/customers/", CustomerListCreateView.as_view()),
    path("api/leads/", LeadListCreateView.as_view()),
    path("api/leads/<int:pk>/", LeadDetailView.as_view()),
    path("api/leads/<int:pk>/transition/", LeadTransitionView.as_view()),
    path("api/leads/<int:pk>/actions/", ActionCreateView.as_view()),
    path("api/actions/<int:pk>/", ActionUpdateView.as_view()),
    path("api/today/", DailyQueueView.as_view()),
    path("api/actions/<int:pk>/complete/", ActionCompleteView.as_view()),
]
