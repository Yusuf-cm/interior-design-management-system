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
    QuoteCreateView, QuoteDetailView, QuoteRevisionView, QuoteReviewView, QuoteListView, QuoteEventView, ApprovalCorrectionView,
)

from studio_os.operations.workspace import workspace, session, sign_in, sign_out, change_password, StaffDirectoryView

from studio_os.operations.team import TeamView, TeamMemberView

from studio_os.operations.printing import print_quote

from studio_os.operations.projects import (
    ProjectCreateView, ProjectListView, ProjectDetailView, ProjectCommandView,
    WorkCreateView, WorkDetailView, WorkCommandView,
)

urlpatterns = [
    path("api/quotes/<int:pk>/approval-correction/", ApprovalCorrectionView.as_view()),
    path("api/quotes/<int:pk>/events/", QuoteEventView.as_view()),
    path("api/quotes/<int:pk>/project/", ProjectCreateView.as_view()),
    path("api/projects/", ProjectListView.as_view()),
    path("api/projects/<int:pk>/", ProjectDetailView.as_view()),
    path("api/projects/<int:pk>/command/", ProjectCommandView.as_view()),
    path("api/projects/<int:pk>/work/", WorkCreateView.as_view()),
    path("api/work/<int:pk>/", WorkDetailView.as_view()),
    path("api/work/<int:pk>/command/", WorkCommandView.as_view()),
    path("quotes/<int:pk>/print/", print_quote, name="quote-print"),
    path("api/team/", TeamView.as_view()),
    path("api/team/<int:pk>/", TeamMemberView.as_view()),
    path("api/quotes/", QuoteListView.as_view()),
    path("api/session/password/", change_password),
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
