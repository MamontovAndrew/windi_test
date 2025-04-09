import pytest

@pytest.mark.asyncio
async def test_register_and_login(client):
    register_data = {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret"
    }
    response = await client.post("/auth/register", json=register_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@example.com"
    
    login_response = await client.post("/auth/login", data={"username": register_data["email"], "password": register_data["password"]})
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
