
from app.common.text_utils import remove_html_tags, sanitize_and_normalize_text, sanitize_name


def test_remove_html_tags_simple():
    assert remove_html_tags("Hello <b>World</b>!") == "Hello World!"


def test_sanitize_and_normalize_text_spaces_and_newlines():
    raw = "  Hello\u00A0\tWorld\n\r\nThis   is  “quoted”  text  "
    out = sanitize_and_normalize_text(raw)
    assert out == 'Hello World This is "quoted" text'


def test_sanitize_and_normalize_text_strips_html_and_fancy_quotes():
    raw = "<p>‘Ala’ i “kot”</p>"
    out = sanitize_and_normalize_text(raw)
    assert out == "'Ala' i \"kot\""


def test_sanitize_name_transliteration_and_cleanup():
    # Accents should be removed and spaces/punctuation normalized to hyphens
    name = "Zażółć gęślą jaźń!  Foo — Bar  & Baz"
    out = sanitize_name(name)
    assert out == "zazolc-gesla-jazn-foo-bar-baz"


def test_sanitize_name_collapse_and_trim_hyphens():
    assert sanitize_name("  ---Hello   World---  ") == "hello-world"
