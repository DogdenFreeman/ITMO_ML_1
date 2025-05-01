import random


def predict(history: list, lesson_id: int) -> dict:

    attended_count = sum(1 for record in history if record.get('attended'))
    total_lessons = len(history)

    probability = attended_count / total_lessons if total_lessons > 0 else 0.5

    return {"prediction": f"Predicted probability for lesson {lesson_id}: {probability:.2f}", "probability": probability}