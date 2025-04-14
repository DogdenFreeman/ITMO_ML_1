import random

def predict(history):
    # для примера предсказание вероятности следующего посещения на основе истории посещений
    attended_count = sum(record['attended'] for record in history)
    probability = attended_count / len(history) if history else 0.5
    return {"probability": probability}