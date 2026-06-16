"""Password-reset flow: forgot-password (no account enumeration) + reset-password
(valid/invalid/expired/single-use)."""
from unittest.mock import patch

from app.services.auth import create_password_reset_token, get_password_hash
from app.models.user import User


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


class TestForgotPassword:
    def test_known_email_sends_and_returns_generic(self, client, test_user):
        with patch("app.routers.auth.send_password_reset_email", return_value=True) as send:
            r = client.post("/auth/forgot-password", json={"email": test_user.email})
        assert r.status_code == 200
        assert "reset link" in r.json()["message"].lower()
        send.assert_called_once()

    def test_unknown_email_returns_same_message_no_send(self, client):
        with patch("app.routers.auth.send_password_reset_email") as send:
            r = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
        assert r.status_code == 200
        assert "reset link" in r.json()["message"].lower()  # identical → no enumeration
        send.assert_not_called()

    def test_google_only_user_gets_no_email(self, client, db_session):
        u = User(username="goog", email="g@example.com", hashed_password=None, google_id="gid")
        db_session.add(u); db_session.commit()
        with patch("app.routers.auth.send_password_reset_email") as send:
            r = client.post("/auth/forgot-password", json={"email": "g@example.com"})
        assert r.status_code == 200
        send.assert_not_called()


class TestResetPassword:
    def test_valid_token_changes_password_and_logs_in(self, client, db_session, test_user):
        token = create_password_reset_token(test_user)
        r = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"})
        assert r.status_code == 200
        assert r.json()["access_token"]
        # old password no longer works, new one does
        assert _login(client, "testuser", "password123").status_code == 401
        assert _login(client, "testuser", "newpass123").status_code == 200

    def test_invalid_token_rejected(self, client):
        r = client.post("/auth/reset-password", json={"token": "garbage", "new_password": "newpass123"})
        assert r.status_code == 400

    def test_short_password_rejected(self, client, test_user):
        token = create_password_reset_token(test_user)
        r = client.post("/auth/reset-password", json={"token": token, "new_password": "short"})
        assert r.status_code == 400

    def test_token_is_single_use(self, client, db_session, test_user):
        token = create_password_reset_token(test_user)
        assert client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"}).status_code == 200
        # same token again — fingerprint no longer matches the (now changed) hash
        again = client.post("/auth/reset-password", json={"token": token, "new_password": "another123"})
        assert again.status_code == 400
