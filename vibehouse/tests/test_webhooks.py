import json

import pytest


@pytest.mark.asyncio
async def test_trello_webhook_valid(client):
    payload = {
        "action": {
            "type": "updateCard",
            "data": {
                "card": {"id": "abc123"},
                "listAfter": {"name": "In Progress"},
                "listBefore": {"name": "Backlog"},
            },
        },
    }

    response = await client.post(
        "/api/v1/webhooks/trello",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_trello_webhook_invalid_json(client):
    response = await client.post(
        "/api/v1/webhooks/trello",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
