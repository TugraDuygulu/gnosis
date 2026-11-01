"""Grade history for supported staff writes, stored in Django's existing log."""

import json

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType

from core.models import Grade


def history_key(enrollment_id):
    return f"Gnosis grade history / enrollment {enrollment_id}"


def grade_state(grade):
    return {
        "score": None if grade.score is None else str(grade.score),
        "assessment": grade.assessment.name,
        "maximum": str(grade.assessment.max_score),
        "assessment_id": grade.assessment_id,
        "enrollment_id": grade.enrollment_id,
    }


def record_grade_change(user, grade, before, *, source, operation):
    """Call inside the grade write's transaction; logging failure aborts it."""
    after = None if operation == "delete" else grade_state(grade)
    if before is not None and after is not None and before == after:
        return None
    state = after or before
    event = {
        "version": 1, "operation": operation, "source": source,
        "before": before, "after": after,
    }
    return LogEntry.objects.create(
        user_id=user.pk,
        content_type=ContentType.objects.get_for_model(Grade),
        object_id=str(grade.pk),
        object_repr=history_key(state["enrollment_id"]),
        action_flag={"create": ADDITION, "change": CHANGE, "delete": DELETION}[operation],
        change_message=json.dumps([
            {"changed": {"fields": ["grade score"]}},
            {"gnosis_grade_change": event},
        ]),
    )


def history_entries(enrollment_id):
    return LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(Grade),
        object_repr=history_key(enrollment_id),
    ).select_related("user").order_by("-action_time", "-pk")


def history_row(entry):
    try:
        event = json.loads(entry.change_message)[1]["gnosis_grade_change"]
        before, after = event["before"], event["after"]
        state = after or before
        return {
            "time": entry.action_time, "actor": entry.user.get_username(),
            "assessment": state["assessment"], "maximum": state["maximum"],
            "old": before["score"] if before else None,
            "new": after["score"] if after else None,
            "operation": event["operation"], "source": event["source"],
        }
    except (ValueError, KeyError, IndexError, TypeError):
        return {"unavailable": True, "time": entry.action_time}
