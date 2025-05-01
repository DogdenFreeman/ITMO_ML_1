from fastapi.testclient import TestClient
from app.core.config import settings

def test_register_user(client: TestClient):
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "newuser@example.com", "password": "newpassword"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "balance" in data
    assert data["balance"] == 0.0

def test_register_duplicate_user(client: TestClient):
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "duplicate@example.com", "password": "password"},
    )
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "duplicate@example.com", "password": "password"},
    )
    assert response.status_code == 400
    assert "Такой пользователь уже существует" in response.json()["detail"]

def test_login_user(client: TestClient, auth_token: str):
    assert auth_token.startswith("Bearer ")

def test_topup_balance(client: TestClient, auth_token: str):
    topup_amount = 50.5
    headers = {"Authorization": auth_token}

    response_before = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert response_before.status_code == 200
    balance_before = response_before.json()["balance"]

    response_topup = client.post(
        f"{settings.API_V1_STR}/users/me/balance/topup",
        headers=headers,
        json={"amount": topup_amount},
    )
    assert response_topup.status_code == 200
    data_topup = response_topup.json()
    assert data_topup["balance"] == balance_before + topup_amount

    response_history = client.get(
        f"{settings.API_V1_STR}/users/me/history/transactions",
        headers=headers
    )
    assert response_history.status_code == 200
    transactions = response_history.json()
    topup_found = any(
        t["transaction_type"] == "topup" and t["amount"] == topup_amount
        for t in transactions
    )
    assert topup_found, "Транзакция пополнения не найдена в истории"

def test_topup_negative_amount(client: TestClient, auth_token: str):
    headers = {"Authorization": auth_token}
    response = client.post(
        f"{settings.API_V1_STR}/users/me/balance/topup",
        headers=headers,
        json={"amount": -10},
    )
    assert response.status_code == 400
    assert "Сумма пополнения должна быть положительной" in response.json()["detail"]

def test_create_prediction_success(client: TestClient, auth_token: str):
    headers = {"Authorization": auth_token}
    prediction_cost = settings.PREDICTION_COST
    client.post(
        f"{settings.API_V1_STR}/users/me/balance/topup",
        headers=headers,
        json={"amount": prediction_cost + 10},
    )

    response_before = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    balance_before = response_before.json()["balance"]

    prediction_input = {"input_data": {"feature1": 1.23, "feature2": "test"}}
    response_predict = client.post(
        f"{settings.API_V1_STR}/predictions/",
        headers=headers,
        json=prediction_input,
    )
    assert response_predict.status_code == 202

    data_predict = response_predict.json()
    assert data_predict["status"] == "pending"
    assert data_predict["cost"] == prediction_cost
    assert "id" in data_predict

    response_after = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    balance_after = response_after.json()["balance"]

    import pytest
    assert balance_after == pytest.approx(balance_before - prediction_cost)

    response_history = client.get(
        f"{settings.API_V1_STR}/users/me/history/transactions",
        headers=headers
    )
    assert response_history.status_code == 200
    transactions = response_history.json()
    fee_found = any(
        t["transaction_type"] == "prediction_fee" and t["amount"] == -prediction_cost
        for t in transactions
    )
    assert fee_found, "Транзакция списания за предсказание не найдена"

def test_create_prediction_insufficient_funds(client: TestClient, auth_token: str):
    headers = {"Authorization": auth_token}

    prediction_input = {"input_data": {"feature1": 4.56, "feature2": "fail"}}
    response_predict = client.post(
        f"{settings.API_V1_STR}/predictions/",
        headers=headers,
        json=prediction_input,
    )
    assert response_predict.status_code == 402
    assert "Недостаточно средств" in response_predict.json()["detail"]