# tests/test_reviews.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_create_review(client: AsyncClient):
    """Test creating a review."""
    response = await client.post(
        "/reviews/",
        json={"rating": 5, "comment": "Amazing product!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Amazing product!"
    assert "id" in data

async def test_read_review(client: AsyncClient):
    """Test reading a single review."""
    # First, create a review to read
    create_response = await client.post(
        "/reviews/",
        json={"rating": 4, "comment": "Very good"},
    )
    assert create_response.status_code == 201
    review_id = create_response.json()["id"]

    # Now, read it
    read_response = await client.get(f"/reviews/{review_id}")
    assert read_response.status_code == 200
    data = read_response.json()
    assert data["id"] == review_id
    assert data["rating"] == 4

async def test_read_reviews(client: AsyncClient):
    """Test reading a list of reviews."""
    # Create a couple of reviews
    await client.post("/reviews/", json={"rating": 5, "comment": "First"})
    await client.post("/reviews/", json={"rating": 3, "comment": "Second"})

    response = await client.get("/reviews/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # Using >= because other tests might have created reviews

async def test_update_review(client: AsyncClient):
    """Test updating a review."""
    create_response = await client.post("/reviews/", json={"rating": 1, "comment": "Bad"})
    review_id = create_response.json()["id"]

    update_response = await client.put(
        f"/reviews/{review_id}",
        json={"rating": 2, "comment": "Actually, it's not that bad"},
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["rating"] == 2
    assert data["comment"] == "Actually, it's not that bad"

async def test_delete_review(client: AsyncClient):
    """Test deleting a review."""
    create_response = await client.post("/reviews/", json={"rating": 1, "comment": "To be deleted"})
    review_id = create_response.json()["id"]

    delete_response = await client.delete(f"/reviews/{review_id}")
    
    assert delete_response.status_code == 204
    get_response = await client.get(f"/reviews/{review_id}")
    assert get_response.status_code == 404
