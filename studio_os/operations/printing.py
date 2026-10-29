"""Authenticated printable estimates. Viewing does not issue, send or accept a quote."""
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .models import Assessment, Lead, Membership, Quote, QuoteRevision


@never_cache
@require_GET
def print_quote(request, pk):
    if not request.user.is_authenticated or not request.user.is_active:
        return HttpResponseForbidden('Sign in to view this estimate.')
    try:
        org_id = int(request.GET.get('organization', ''))
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Select your studio before opening an estimate.')
    membership = Membership.objects.filter(user=request.user, organization_id=org_id, active=True).first()
    if not membership or membership.role == Membership.Role.FIELD:
        return HttpResponseForbidden('Estimate unavailable.')
    quote = get_object_or_404(Quote.objects.select_related(
        'organization', 'assessment__consultation__lead__customer', 'current_revision'),
        pk=pk, organization_id=org_id)
    revision = quote.current_revision
    if request.GET.get('revision'):
        try:
            number = int(request.GET['revision'])
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Choose a valid revision.')
        revision = get_object_or_404(QuoteRevision, quote=quote, organization_id=org_id, number=number)
    if revision is None:
        return HttpResponseBadRequest('This estimate has no revision yet.')
    current = revision.pk == quote.current_revision_id
    approved = (current and quote.status == Quote.Status.APPROVED
                and quote.assessment.status == Assessment.Status.READY
                and revision.assessment_version == quote.assessment.version
                and quote.assessment.consultation.lead.status != Lead.Status.LOST)
    return render(request, 'studio_os/quote_print.html', {
        'quote': quote, 'revision': revision, 'approved': approved, 'current': current,
        'customer': quote.assessment.consultation.lead.customer,
    })
