from pyrogram import types

from workers.sending import CAPTION_LIMIT, SendOptions, send_content


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def send_photo(self, chat_id, photo, **kwargs):
        self.calls.append(("photo", {"photo": photo, **kwargs}))

    async def send_media_group(self, chat_id, media, **kwargs):
        self.calls.append(("album", {"media": media, **kwargs}))

    async def send_message(self, chat_id, text, **kwargs):
        self.calls.append(("text", {"text": text, **kwargs}))


async def test_text_only():
    client = _Recorder()
    await send_content(client, 1, "hi", [], SendOptions(disable_link_preview=True))
    kind, kwargs = client.calls[0]
    assert kind == "text"
    assert kwargs["link_preview_options"].is_disabled


async def test_single_photo_carries_caption():
    client = _Recorder()
    await send_content(client, 1, "hi", ["/a.jpg"])
    assert [c[0] for c in client.calls] == ["photo"]
    assert client.calls[0][1]["caption"] == "hi"


async def test_album_has_caption_on_first_item_only_and_options_applied():
    client = _Recorder()
    await send_content(
        client,
        1,
        "hi",
        ["/a.jpg", "/b.jpg"],
        SendOptions(disable_notification=True, protect_content=True),
    )
    kind, kwargs = client.calls[0]
    assert kind == "album"
    media = kwargs["media"]
    assert all(isinstance(m, types.InputMediaPhoto) for m in media)
    assert [m.caption for m in media] == ["hi", ""]
    assert kwargs["disable_notification"] and kwargs["protect_content"]


async def test_long_text_goes_after_photos_as_separate_message():
    client = _Recorder()
    text = "x" * (CAPTION_LIMIT + 1)
    await send_content(client, 1, text, ["/a.jpg"])
    assert [c[0] for c in client.calls] == ["photo", "text"]
    assert client.calls[0][1]["caption"] == ""
    assert client.calls[1][1]["text"] == text


async def test_formatting_tags_do_not_count_towards_caption_limit():
    client = _Recorder()
    text = "<b>" + "x" * CAPTION_LIMIT + "</b>"
    await send_content(client, 1, text, ["/a.jpg"])
    assert [c[0] for c in client.calls] == ["photo"]


async def test_reply_goes_to_the_first_message():
    client = _Recorder()
    await send_content(client, 1, "hi", [], SendOptions(reply_to_message_id=9))
    assert client.calls[0][1]["reply_parameters"].message_id == 9
