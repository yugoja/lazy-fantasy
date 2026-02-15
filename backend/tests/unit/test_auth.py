"""Unit tests for authentication endpoints."""
import pytest


@pytest.mark.unit
class TestAuthentication:
    """Test user authentication flows."""

    def test_signup_success(self, client):
        """Test successful user signup."""
        response = client.post(
            "/auth/signup",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "password" not in data

    def test_signup_duplicate_username(self, client, test_user):
        """Test signup fails with duplicate username."""
        response = client.post(
            "/auth/signup",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_duplicate_email(self, client, test_user):
        """Test signup fails with duplicate email."""
        response = client.post(
            "/auth/signup",
            json={
                "username": "differentuser",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_username(self, client):
        """Test login fails with invalid username."""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401

    def test_login_invalid_password(self, client, test_user):
        """Test login fails with invalid password."""
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
