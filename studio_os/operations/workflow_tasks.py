"""Stable origins keep internal workflow tasks from duplicating on retries."""
from django.db.models import F
from django.utils import timezone
from .models import NextAction


def plan_task(org, lead, origin, title, assignee):
    action, created = NextAction.objects.get_or_create(
        organization=org, origin_key=origin,
        defaults={"lead": lead, "title": title, "assignee": assignee, "due_at": timezone.now()},
    )
    if not created:
        NextAction.objects.filter(pk=action.pk).update(
            title=title, assignee=assignee, due_at=timezone.now(),
            done=False, cancelled=False, version=F("version") + 1)
    return action


def settle_task(org, origin, *, cancelled=False):
    NextAction.objects.filter(organization=org, origin_key=origin, done=False, cancelled=False).update(
        done=not cancelled, cancelled=cancelled, version=F("version") + 1,
    )
