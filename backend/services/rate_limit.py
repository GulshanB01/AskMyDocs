from datetime import date

from backend.db import QuestionUsage, db


DAILY_QUESTION_LIMIT = 50


def get_daily_question_count(user_id: int) -> int:
    usage = QuestionUsage.get_or_none(
        (QuestionUsage.user_id == user_id)
        & (QuestionUsage.usage_date == date.today().isoformat())
    )
    return usage.count if usage else 0


def get_remaining_questions(user_id: int) -> int:
    return max(DAILY_QUESTION_LIMIT - get_daily_question_count(user_id), 0)


def increment_question_count(user_id: int):
    today = date.today().isoformat()
    with db.atomic():
        usage = QuestionUsage.get_or_none(
            (QuestionUsage.user_id == user_id)
            & (QuestionUsage.usage_date == today)
        )
        if usage:
            usage.count += 1
            usage.save()
        else:
            QuestionUsage.create(user_id=user_id, usage_date=today, count=1)
