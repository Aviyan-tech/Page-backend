# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
# pyrefly: ignore [missing-import]
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.database import Base

# Setup an in-memory SQLite database for test runs to avoid modifying local development data
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the get_db dependency in the application
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Bind engine and recreate tables for each test method to guarantee absolute isolation
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_post():
    # 1. Unauthorized attempt (No key)
    response = client.post(
        "/posts",
        json={"title": "Test Title", "content": "Test Content", "category": "Test Category"}
    )
    assert response.status_code == 403

    # 2. Authorized creation
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Test Title", "content": "Test Content", "category": "Test Category", "status": "draft"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Title"
    assert data["status"] == "draft"
    assert data["views"] == 0
    assert "id" in data

    # 3. Prevent duplicate titles
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Test Title", "content": "Other content", "category": "Test Category", "status": "draft"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_posts_and_filtering():
    # Insert fixtures
    client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "FastAPI asynchronous", "content": "Python is fast", "category": "Tech", "status": "published"}
    )
    client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Baking cookies", "content": "Use sugar and flour", "category": "Cooking", "status": "draft"}
    )

    # 1. Get all
    response = client.get("/posts")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # 2. Filter by category
    response = client.get("/posts?category=Tech")
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "FastAPI asynchronous"

    # 3. Filter by status
    response = client.get("/posts?status=draft")
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Baking cookies"

    # 4. Search checking both title and content
    response = client.get("/posts?search=python")
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "FastAPI asynchronous"

    # 5. Search with pagination and sorting
    response = client.get("/posts?sort_by=views&order=desc")
    assert len(response.json()) == 2


def test_put_update_post():
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Old Title", "content": "Old Content", "category": "Old", "status": "draft"}
    )
    post_id = response.json()["id"]

    # Update post
    response = client.put(
        f"/posts/{post_id}",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "New Title", "content": "New Content", "category": "New", "status": "published"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["status"] == "published"


def test_patch_partial_update_post():
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Original Title", "content": "Original Content", "category": "Original", "status": "draft"}
    )
    post_id = response.json()["id"]

    # Partial update status only
    response = client.patch(
        f"/posts/{post_id}",
        headers={"X-API-Key": "secret-api-key"},
        json={"status": "published"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Original Title"
    assert data["status"] == "published"


def test_delete_post():
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "To Delete", "content": "Delete me", "category": "Trash", "status": "draft"}
    )
    post_id = response.json()["id"]

    # Delete post
    response = client.delete(
        f"/posts/{post_id}",
        headers={"X-API-Key": "secret-api-key"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Post deleted successfully"

    # Get post should return 404
    response = client.get(f"/posts/{post_id}")
    assert response.status_code == 404


def test_increment_view():
    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "View post", "content": "Check views", "category": "Test", "status": "draft"}
    )
    post_id = response.json()["id"]

    # Increment view count twice
    client.post(f"/posts/{post_id}/view")
    response = client.post(f"/posts/{post_id}/view")
    assert response.status_code == 200
    assert response.json()["views"] == 2


def test_dashboard_stats():
    # 1. Zero posts stats (should not crash)
    response = client.get("/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_posts"] == 0
    assert data["total_views"] == 0
    assert data["most_viewed_post"] is None

    # 2. Populated stats
    client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "First", "content": "One", "category": "A", "status": "published"}
    )
    response2 = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "Second", "content": "Two", "category": "B", "status": "draft"}
    )
    second_id = response2.json()["id"]

    # Increment second post views
    client.post(f"/posts/{second_id}/view")
    client.post(f"/posts/{second_id}/view")

    response = client.get("/dashboard/stats")
    data = response.json()
    assert data["total_posts"] == 2
    assert data["published_posts"] == 1
    assert data["draft_posts"] == 1
    assert data["total_views"] == 2
    assert data["most_viewed_post"]["id"] == second_id
    assert data["most_viewed_post"]["views"] == 2


def test_ai_summarize_fallback(monkeypatch):
    # Mock GROQ_API_KEY to empty to force fallback behavior
    monkeypatch.setattr("app.ai_service.GROQ_API_KEY", "")

    response = client.post(
        "/posts",
        headers={"X-API-Key": "secret-api-key"},
        json={"title": "AI Summary Test", "content": "FastAPI is a very nice modern web framework. It is fast to code and easy to maintain.", "category": "Tech", "status": "draft"}
    )
    post_id = response.json()["id"]

    # Summarize with fallback
    response = client.post(f"/posts/{post_id}/summarize")
    assert response.status_code == 200
    data = response.json()
    assert data["ai_summary"] is not None
    # Fallback to truncation
    assert data["ai_summary"] == "FastAPI is a very nice modern web framework. It is fast to code and easy to maintain."
