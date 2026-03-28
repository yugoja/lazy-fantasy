"""
Integration tests for the league invite / join flow.
Covers the new /leagues/preview/{code} endpoint and the join flow.
"""
import pytest
from app.models.user import User
from app.models.league import League, LeagueMember
from app.services.auth import get_password_hash, create_access_token


def make_user(db_session, username, email):
    user = User(username=username, email=email, hashed_password=get_password_hash("pass1234"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth(user):
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestLeagueInviteFlow:

    def test_preview_invalid_code_returns_404(self, client):
        r = client.get('/leagues/preview/BADCODE')
        assert r.status_code == 404

    def test_preview_requires_no_auth(self, client, db_session):
        owner = make_user(db_session, "owner1", "owner1@test.com")
        r = client.post('/leagues/', json={'name': 'My Test League', 'sport': 'cricket'},
                        headers=auth(owner))
        assert r.status_code == 201
        invite_code = r.json()['invite_code']

        # Preview with no Authorization header
        r = client.get(f'/leagues/preview/{invite_code}')
        assert r.status_code == 200
        data = r.json()
        assert data['name'] == 'My Test League'
        assert data['invite_code'] == invite_code
        assert data['member_count'] == 1  # just the owner

    def test_preview_normalises_lowercase_code(self, client, db_session):
        owner = make_user(db_session, "owner2", "owner2@test.com")
        r = client.post('/leagues/', json={'name': 'Case League', 'sport': 'cricket'},
                        headers=auth(owner))
        invite_code = r.json()['invite_code']

        r = client.get(f'/leagues/preview/{invite_code.lower()}')
        assert r.status_code == 200
        assert r.json()['invite_code'] == invite_code

    def test_preview_member_count_increments_after_join(self, client, db_session):
        owner = make_user(db_session, "owner3", "owner3@test.com")
        joiner = make_user(db_session, "joiner1", "joiner1@test.com")

        r = client.post('/leagues/', json={'name': 'Count League', 'sport': 'cricket'},
                        headers=auth(owner))
        invite_code = r.json()['invite_code']

        # Before join: 1 member
        assert client.get(f'/leagues/preview/{invite_code}').json()['member_count'] == 1

        # Joiner joins
        r = client.post('/leagues/join', json={'invite_code': invite_code}, headers=auth(joiner))
        assert r.status_code == 200

        # After join: 2 members
        assert client.get(f'/leagues/preview/{invite_code}').json()['member_count'] == 2

    def test_join_returns_league_with_correct_id(self, client, db_session):
        owner = make_user(db_session, "owner4", "owner4@test.com")
        joiner = make_user(db_session, "newuser", "new@test.com")

        r = client.post('/leagues/', json={'name': 'E2E League', 'sport': 'cricket'},
                        headers=auth(owner))
        league_id = r.json()['id']
        invite_code = r.json()['invite_code']

        r = client.post('/leagues/join', json={'invite_code': invite_code}, headers=auth(joiner))
        assert r.status_code == 200
        assert r.json()['id'] == league_id
        assert r.json()['name'] == 'E2E League'

    def test_already_member_returns_400(self, client, db_session):
        owner = make_user(db_session, "owner5", "owner5@test.com")

        r = client.post('/leagues/', json={'name': 'Dup League', 'sport': 'cricket'},
                        headers=auth(owner))
        invite_code = r.json()['invite_code']

        # Owner tries to rejoin their own league
        r = client.post('/leagues/join', json={'invite_code': invite_code}, headers=auth(owner))
        assert r.status_code == 400
        assert 'already a member' in r.json()['detail']
