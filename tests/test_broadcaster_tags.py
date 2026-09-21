from dataclasses import dataclass

from workers.broadcaster import TAG_PLACEHOLDER, _resolve_tag_placeholder


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


async def test_placeholder_stripped_when_tag_random_users_is_off():
    client = _FakeClient([_FakeMember(_FakeUser(id=1, first_name="A"))])
    text = f"hello{TAG_PLACEHOLDER}world"
    result = await _resolve_tag_placeholder(client, chat_id=1, text=text, tag_random_users=False)
    assert result == "helloworld"


async def test_placeholder_untouched_when_absent():
    client = _FakeClient([])
    text = "no placeholder here"
    result = await _resolve_tag_placeholder(client, chat_id=1, text=text, tag_random_users=True)
    assert result == text


async def test_placeholder_replaced_with_mentions_of_real_members_only():
    client = _FakeClient(
        [
            _FakeMember(_FakeUser(id=1, first_name="Alice")),
            _FakeMember(_FakeUser(id=2, first_name="Bot", is_bot=True)),
            _FakeMember(None),
        ]
    )
    text = f"hi{TAG_PLACEHOLDER}"
    result = await _resolve_tag_placeholder(client, chat_id=1, text=text, tag_random_users=True)
    assert "tg://user?id=1" in result
    assert "tg://user?id=2" not in result
    assert TAG_PLACEHOLDER not in result
