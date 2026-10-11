from __future__ import annotations

from mini_codex.safety.secrets import is_probably_binary, is_secret_path


def test_common_secret_files_are_detected():
    assert is_secret_path(".env")
    assert is_secret_path("config/.env.local")
    assert is_secret_path("keys/id_rsa")
    assert is_secret_path("certs/server.pem")
    assert is_secret_path("credentials.json")


def test_normal_source_files_are_not_secret():
    assert not is_secret_path("src/app.py")
    assert not is_secret_path("README.md")
    assert not is_secret_path("environment.py")


def test_binary_detection():
    assert is_probably_binary(b"\x00\x01\x02binary")
    assert not is_probably_binary(b"def foo():\n    return 1\n")
    assert not is_probably_binary(b"")
