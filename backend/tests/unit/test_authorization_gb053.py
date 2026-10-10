"""GB053: M18 testing — OpenFGA authorization fallback paths and convenience functions."""

import pytest

from app.core.authorization import (
    AuthorizationTuple,
    OpenFGAClient,
    Relation,
)


class TestOpenFGAFallbackCheck:
    @pytest.fixture
    def client(self):
        c = OpenFGAClient()
        c._available = False
        c._local_tuples = []
        return c

    @pytest.mark.asyncio
    async def test_fallback_check_match(self, client):
        client._local_tuples = [
            AuthorizationTuple(user="user:alice", relation="can_view", object="project:p1"),
        ]
        result = await client._fallback_check("user:alice", "can_view", "project:p1")
        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_check_no_match(self, client):
        client._local_tuples = [
            AuthorizationTuple(user="user:alice", relation="can_view", object="project:p1"),
        ]
        result = await client._fallback_check("user:bob", "can_view", "project:p1")
        assert result is False

    @pytest.mark.asyncio
    async def test_fallback_check_wrong_relation(self, client):
        client._local_tuples = [
            AuthorizationTuple(user="user:alice", relation="can_view", object="project:p1"),
        ]
        result = await client._fallback_check("user:alice", "can_edit", "project:p1")
        assert result is False

    @pytest.mark.asyncio
    async def test_fallback_check_empty_tuples(self, client):
        result = await client._fallback_check("user:alice", "can_view", "project:p1")
        assert result is False


class TestOpenFGAFallbackWrite:
    @pytest.fixture
    def client(self):
        c = OpenFGAClient()
        c._available = False
        c._local_tuples = []
        return c

    @pytest.mark.asyncio
    async def test_write_adds_tuples(self, client):
        t = AuthorizationTuple(user="user:alice", relation="member", object="organization:o1")
        result = await client._fallback_write(writes=[t], deletes=None)
        assert result is True
        assert len(client._local_tuples) == 1
        assert client._local_tuples[0].user == "user:alice"

    @pytest.mark.asyncio
    async def test_write_deletes_tuples(self, client):
        t = AuthorizationTuple(user="user:alice", relation="member", object="organization:o1")
        client._local_tuples = [t]
        result = await client._fallback_write(
            writes=None,
            deletes=[AuthorizationTuple(user="user:alice", relation="member", object="organization:o1")],
        )
        assert result is True
        assert len(client._local_tuples) == 0

    @pytest.mark.asyncio
    async def test_write_and_delete_same_call(self, client):
        old = AuthorizationTuple(user="user:alice", relation="viewer", object="project:p1")
        client._local_tuples = [old]
        new = AuthorizationTuple(user="user:alice", relation="admin", object="project:p1")
        result = await client._fallback_write(writes=[new], deletes=[old])
        assert result is True
        assert len(client._local_tuples) == 1
        assert client._local_tuples[0].relation == "admin"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tuple(self, client):
        t = AuthorizationTuple(user="user:nobody", relation="admin", object="project:p1")
        result = await client._fallback_write(writes=None, deletes=[t])
        assert result is True
        assert len(client._local_tuples) == 0


class TestOpenFGAFallbackListObjects:
    @pytest.fixture
    def client(self):
        c = OpenFGAClient()
        c._available = False
        c._local_tuples = [
            AuthorizationTuple(user="user:alice", relation="can_view", object="project:p1"),
            AuthorizationTuple(user="user:alice", relation="can_view", object="project:p2"),
            AuthorizationTuple(user="user:alice", relation="can_edit", object="project:p3"),
            AuthorizationTuple(user="user:bob", relation="can_view", object="project:p1"),
            AuthorizationTuple(user="user:alice", relation="member", object="organization:o1"),
        ]
        return c

    @pytest.mark.asyncio
    async def test_list_objects_filters_by_user_and_relation(self, client):
        result = await client._fallback_list_objects("user:alice", "can_view", "project")
        assert set(result) == {"project:p1", "project:p2"}

    @pytest.mark.asyncio
    async def test_list_objects_filters_by_type(self, client):
        result = await client._fallback_list_objects("user:alice", "member", "organization")
        assert result == ["organization:o1"]

    @pytest.mark.asyncio
    async def test_list_objects_empty_result(self, client):
        result = await client._fallback_list_objects("user:charlie", "can_view", "project")
        assert result == []


class TestOpenFGAFallbackListUsers:
    @pytest.fixture
    def client(self):
        c = OpenFGAClient()
        c._available = False
        c._local_tuples = [
            AuthorizationTuple(user="user:alice", relation="member", object="organization:o1"),
            AuthorizationTuple(user="user:bob", relation="member", object="organization:o1"),
            AuthorizationTuple(user="user:charlie", relation="admin", object="organization:o1"),
        ]
        return c

    @pytest.mark.asyncio
    async def test_list_users_filters_correctly(self, client):
        result = await client._fallback_list_users("member", "organization:o1", "user")
        assert set(result) == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_list_users_wrong_relation(self, client):
        result = await client._fallback_list_users("owner", "organization:o1", "user")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_users_wrong_type(self, client):
        result = await client._fallback_list_users("member", "organization:o1", "service")
        assert result == []


class TestOpenFGAIsAvailable:
    @pytest.mark.asyncio
    async def test_not_available_without_url(self):
        c = OpenFGAClient()
        c.base_url = ""
        c.store_id = "some-id"
        c._available = None
        result = await c.is_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_not_available_without_store_id(self):
        c = OpenFGAClient()
        c.base_url = "http://localhost:8080"
        c.store_id = ""
        c._available = None
        result = await c.is_available()
        assert result is False

    @pytest.mark.asyncio
    async def test_cached_availability(self):
        c = OpenFGAClient()
        c._available = True
        result = await c.is_available()
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_failure_returns_false(self):
        c = OpenFGAClient()
        c.base_url = "http://localhost:99999"
        c.store_id = "some-store"
        c._available = None
        result = await c.is_available()
        assert result is False


class TestRelationEnum:
    def test_relation_values(self):
        assert Relation.ORG_OWNER == "owner"
        assert Relation.CAN_VIEW == "can_view"
        assert Relation.CAN_MANAGE == "can_manage"

    def test_relation_is_string_enum(self):
        assert isinstance(Relation.ORG_OWNER, str)
