"""Round-trip and safety tests for the config store.

These cover the data-corruption class of bugs: value escaping, atomic writes,
and add/edit/remove correctness. No network or litellm needed.
"""
import os
import stat

import pytest

from llmcheck import config


@pytest.fixture(autouse=True)
def temp_config(tmp_path, monkeypatch):
    cfg = tmp_path / "llmcheck_env"
    lock = tmp_path / "llmcheck_env.lock"
    monkeypatch.setattr(config, "CONFIG_FILE", cfg)
    monkeypatch.setattr(config, "LOCK_FILE", lock)
    return cfg


def test_load_empty():
    assert config.load_models() == []


def test_add_and_load():
    config.add_model("GPT-4o", "openai", "gpt-4o", "sk-abcd1234", tags="coding,general")
    models = config.load_models()
    assert len(models) == 1
    m = models[0]
    assert m["name"] == "GPT-4o"
    assert m["provider"] == "openai"
    assert m["model"] == "gpt-4o"
    assert m["api_key"] == "sk-abcd1234"
    assert m["tags"] == "coding,general"
    assert m["_id"] == "1"


def test_ids_increment_and_no_reuse():
    config.add_model("A", "openai", "a", "k1")
    config.add_model("B", "openai", "b", "k2")
    config.remove_model("1")
    config.add_model("C", "openai", "c", "k3")
    ids = [m["_id"] for m in config.load_models()]
    # 1 removed, next id is 3 (max+1), never reuses 1
    assert ids == ["2", "3"]


def test_quote_in_value_does_not_corrupt_file():
    # The original bug: a value containing a double-quote broke the dotenv line
    # and corrupted parsing of every following model.
    config.add_model('Weird "Name"', "openai", "gpt-4o", 'sk-has"quote', tags="x")
    config.add_model("Second", "anthropic", "claude", "sk-ant-2")
    models = config.load_models()
    assert len(models) == 2
    assert models[0]["name"] == 'Weird "Name"'
    assert models[0]["api_key"] == 'sk-has"quote'
    assert models[1]["name"] == "Second"
    assert models[1]["provider"] == "anthropic"


def test_backslash_in_value():
    config.add_model("B", "openai", "m", r"sk-a\b\c")
    assert config.load_models()[0]["api_key"] == r"sk-a\b\c"


def test_newline_collapsed():
    config.add_model("N", "openai", "m", "sk-line1\nline2")
    # Newlines are collapsed to spaces so they can't split the dotenv line.
    assert "\n" not in config.load_models()[0]["api_key"]


def test_edit_model():
    config.add_model("A", "openai", "a", "k1", tags="old")
    assert config.edit_model("1", {"name": "A2", "tags": "new"})
    m = config.load_models()[0]
    assert m["name"] == "A2"
    assert m["tags"] == "new"
    assert m["api_key"] == "k1"  # untouched fields preserved


def test_edit_clear_optional_field():
    config.add_model("A", "openai", "a", "k1", tags="x")
    config.edit_model("1", {"tags": ""})
    assert config.load_models()[0].get("tags", "") == ""


def test_edit_missing_returns_false():
    assert config.edit_model("99", {"name": "x"}) is False


def test_remove_missing_returns_false():
    assert config.remove_model("99") is False


def test_remove_prefix_not_greedy():
    # MODEL_1_ must not match MODEL_10_, MODEL_11_, etc.
    for i in range(12):
        config.add_model(f"M{i}", "openai", f"m{i}", f"k{i}")
    config.remove_model("1")
    remaining = [m["_id"] for m in config.load_models()]
    assert "1" not in remaining
    assert "10" in remaining and "11" in remaining and "12" in remaining


def test_file_permissions_are_owner_only(temp_config):
    config.add_model("A", "openai", "a", "k1")
    mode = stat.S_IMODE(os.stat(temp_config).st_mode)
    assert mode == 0o600
