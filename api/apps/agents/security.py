from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import AgentRun


@dataclass(frozen=True)
class AgentRunRejected(Exception):
    reason: str
    message: str = "The assistant usage limit has been reached. Please try again later."


@dataclass(frozen=True)
class AgentExecutionFailed(Exception):
    reason: str


def enforce_agent_run_limits(*, actor):
    """Enforce metadata-only per-user limits before reserving an agent run.

    The caller must hold a database row lock for the actor until it creates the
    pending AgentRun. That makes concurrent reservations serialize per user.
    """

    now = timezone.now()
    runs = AgentRun.objects.filter(actor_id=actor.pk)
    pending_cutoff = now - timedelta(
        seconds=max(settings.AGENT_REQUEST_TIMEOUT_SECONDS * 2, 60)
    )
    if runs.filter(
        status=AgentRun.Status.PENDING,
        created_at__gte=pending_cutoff,
    ).count() >= settings.AGENT_MAX_CONCURRENT_RUNS:
        raise AgentRunRejected("concurrent_run_limit")

    window_start = now - timedelta(seconds=settings.AGENT_RATE_LIMIT_WINDOW_SECONDS)
    if runs.filter(created_at__gte=window_start).count() >= settings.AGENT_RATE_LIMIT_REQUESTS:
        raise AgentRunRejected("request_rate_limit")

    budget_start = now - timedelta(seconds=settings.AGENT_TOKEN_BUDGET_WINDOW_SECONDS)
    usage = runs.filter(created_at__gte=budget_start).aggregate(
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
    )
    consumed = int(usage["input_tokens"] or 0) + int(usage["output_tokens"] or 0)
    if consumed >= settings.AGENT_USER_TOKEN_BUDGET:
        raise AgentRunRejected("token_budget_limit")
