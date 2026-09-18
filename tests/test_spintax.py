from workers.spintax import render_spintax


def test_no_spintax_returns_text_unchanged():
    assert render_spintax("hello world") == "hello world"


def test_resolves_single_group_to_one_of_the_options():
    result = render_spintax("{a|b|c}")
    assert result in {"a", "b", "c"}


def test_resolves_multiple_and_nested_groups():
    result = render_spintax("{Привет|Здравствуйте}, {как|{как же}} дела?")
    assert "{" not in result and "}" not in result
