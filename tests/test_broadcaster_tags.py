from dataclasses import dataclass

from workers.broadcaster import TAG_PLACEHOLDER, _append_random_tags


@dataclass
class _FakeUser:
    id: int
    first_name: str | None
    username: str | None = None
    is_bot: bool = False
    is_deleted: bool = False


@dataclass
class _FakeMember:
    user: _FakeUser | None


class _FakeClient:
    def __init__(self, members):
        self._members = members

    async def get_chat_members(self, chat_id):
        for member in self._members:
            yield member


async def test_nothing_appended_when_tag_random_users_is_off():
    client = _FakeClient([_FakeMember(_FakeUser(id=1, first_name="A"))])
    text = "hello"
    result = await _append_random_tags(client, chat_id=1, text=text, tag_random_users=False)
    assert result == "hello"


async def test_nothing_appended_when_chat_has_no_taggable_members():
    client = _FakeClient([_FakeMember(_FakeUser(id=2, first_name="Bot", is_bot=True))])
    text = "hello"
    result = await _append_random_tags(client, chat_id=1, text=text, tag_random_users=True)
    assert result == "hello"


async def test_mentions_of_real_members_appended_at_the_end():
    client = _FakeClient(
        [
            _FakeMember(_FakeUser(id=1, first_name="Alice")),
            _FakeMember(_FakeUser(id=2, first_name="Bot", is_bot=True)),
            _FakeMember(None),
        ]
    )
    text = "hi"
    result = await _append_random_tags(client, chat_id=1, text=text, tag_random_users=True)
    assert result == f'hi<a href="tg://user?id=1">{TAG_PLACEHOLDER}</a>'
    assert "tg://user?id=2" not in result


async def test_mentions_stay_invisible_no_names_leak_into_the_message():
    client = _FakeClient(
        [_FakeMember(_FakeUser(id=1, first_name="Alice", username="alice_handle"))]
    )
    result = await _append_random_tags(client, chat_id=1, text="hi", tag_random_users=True)
    assert "Alice" not in result
    assert "alice_handle" not in result
