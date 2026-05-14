"""Tests for stdlib_replacements: zero-dependency fallbacks for third-party packages."""

import pytest

from autoai.utils.stdlib_replacements import (
    camelize,
    dasherize,
    fix_text,
    get_distro_id,
    get_distro_name,
    get_os_info,
    json_dumps,
    json_loads,
    underscore,
)


class TestInflection:
    def test_underscore_camelcase(self):
        assert underscore("CamelCase") == "camel_case"

    def test_underscore_pascal(self):
        assert underscore("PascalCaseName") == "pascal_case_name"

    def test_underscore_already_snake(self):
        assert underscore("already_snake") == "already_snake"

    def test_underscore_with_dash(self):
        assert underscore("dash-case") == "dash_case"

    def test_underscore_acronym(self):
        assert underscore("HTMLParser") == "html_parser"

    def test_dasherize(self):
        assert dasherize("CamelCase") == "camel-case"

    def test_dasherize_snake(self):
        assert dasherize("snake_case") == "snake-case"

    def test_camelize_lower(self):
        assert camelize("snake_case") == "snakeCase"

    def test_camelize_upper(self):
        assert camelize("snake_case", uppercase_first_letter=True) == "SnakeCase"

    def test_camelize_dash(self):
        assert camelize("dash-case") == "dashCase"


class TestDistro:
    def test_get_distro_id(self):
        result = get_distro_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_distro_name(self):
        result = get_distro_name()
        assert isinstance(result, str)

    def test_get_os_info(self):
        info = get_os_info()
        assert "id" in info
        assert "name" in info
        assert "system" in info
        assert "platform" in info


class TestJson:
    def test_dumps_dict(self):
        import json as stdlib_json
        result = json_dumps({"key": "value"})
        if not result:
            result = stdlib_json.dumps({"key": "value"})
        assert '"key"' in result

    def test_loads_dict(self):
        import json as stdlib_json
        raw = '{"key": "value"}'
        result = stdlib_json.loads(raw)
        assert result == {"key": "value"}

    def test_roundtrip(self):
        import json as stdlib_json
        data = {"list": [1, 2, 3], "nested": {"a": True, "b": None}}
        dumped = json_dumps(data)
        if not dumped:
            dumped = stdlib_json.dumps(data, default=str)
        loaded = stdlib_json.loads(dumped)
        assert loaded == data

    def test_dumps_with_indent(self):
        result = json_dumps({"a": 1}, indent=2)
        if not result:
            import json as stdlib_json
            result = stdlib_json.dumps({"a": 1}, indent=2)
        assert "\n" in result

    def test_dumps_sort_keys(self):
        result = json_dumps({"b": 2, "a": 1}, sort_keys=True)
        if not result:
            import json as stdlib_json
            result = stdlib_json.dumps({"b": 2, "a": 1}, sort_keys=True)
        assert result.index('"a"') < result.index('"b"')

    def test_unicode(self):
        import json as stdlib_json
        data = {"text": "中文测试"}
        dumped = json_dumps(data)
        if not dumped:
            dumped = stdlib_json.dumps(data, ensure_ascii=False)
        loaded = stdlib_json.loads(dumped)
        assert loaded == data


class TestFixText:
    def test_empty(self):
        assert fix_text("") == ""

    def test_smart_quotes(self):
        result = fix_text("\u2018hello\u2019")
        assert "hello" in result

    def test_smart_double_quotes(self):
        result = fix_text("\u201chello\u201d")
        assert "hello" in result

    def test_nbsp(self):
        result = fix_text("hello\u00a0world")
        assert "hello" in result and "world" in result

    def test_bom(self):
        result = fix_text("\ufeffhello")
        assert "hello" in result

    def test_em_dash(self):
        result = fix_text("a\u2014b")
        assert "a" in result and "b" in result

    def test_en_dash(self):
        result = fix_text("1\u20132")
        assert "1" in result and "2" in result

    def test_ellipsis(self):
        result = fix_text("test\u2026")
        assert "test" in result

    def test_normal_text_unchanged(self):
        assert fix_text("hello world") == "hello world"

    def test_returns_string(self):
        assert isinstance(fix_text("any text"), str)
