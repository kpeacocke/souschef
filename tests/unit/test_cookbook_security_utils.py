"""Tests for cookbook analysis security and utility helper modules."""

from __future__ import annotations

import tarfile
import zipfile
from unittest.mock import MagicMock, patch


def test_path_traversal_detection():
    from souschef.ui.pages.cookbook_analysis_security import _has_path_traversal

    assert _has_path_traversal("../etc/passwd")
    assert not _has_path_traversal("roles/nginx/tasks/main.yml")


def test_depth_limit_detection():
    from souschef.ui.pages.cookbook_analysis_security import _exceeds_depth_limit

    deep = "/".join(["a"] * 20)
    assert _exceeds_depth_limit(deep)
    assert not _exceeds_depth_limit("a/b/c")


def test_blocked_extension_detection():
    from souschef.ui.pages.cookbook_analysis_security import _is_blocked_extension

    assert _is_blocked_extension("payload.exe")
    assert _is_blocked_extension("archive.jar")
    assert not _is_blocked_extension("main.yml")


def test_symlink_detection_zipinfo():
    from souschef.ui.pages.cookbook_analysis_security import _is_symlink

    info = zipfile.ZipInfo("file.txt")
    info.external_attr = 0xA000
    assert _is_symlink(info)

    info.external_attr = 0x8000
    assert not _is_symlink(info)


def test_get_safe_extraction_path_ok(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _get_safe_extraction_path

    path = _get_safe_extraction_path("roles/nginx/tasks/main.yml", tmp_path)
    assert str(path).startswith(str(tmp_path.resolve()))


def test_get_safe_extraction_path_rejects_bad_paths(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _get_safe_extraction_path

    bad_paths = ["../evil", "/abs/path", "C:evil", "..\\evil"]
    for p in bad_paths:
        try:
            _get_safe_extraction_path(p, tmp_path)
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass


def test_validate_zip_file_security_rejects_large_file(monkeypatch):
    from souschef.ui.pages.cookbook_analysis_security import _validate_zip_file_security

    info = zipfile.ZipInfo("large.bin")
    info.file_size = 10
    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILE_SIZE", 1)

    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "File too large" in str(exc)


def test_validate_zip_file_security_rejects_blocked_extension():
    from souschef.ui.pages.cookbook_analysis_security import _validate_zip_file_security

    info = zipfile.ZipInfo("payload.exe")
    info.file_size = 1
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Blocked file type" in str(exc)


def test_validate_tar_file_security_rejects_symlink():
    from souschef.ui.pages.cookbook_analysis_security import _validate_tar_file_security

    member = MagicMock(spec=tarfile.TarInfo)
    member.name = "link"
    member.size = 1
    member.issym.return_value = True
    member.islnk.return_value = False
    member.isfile.return_value = False
    member.isdir.return_value = False
    member.type = b"2"

    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Symlinks not allowed" in str(exc)


def test_validate_tar_file_security_rejects_unsupported_type():
    from souschef.ui.pages.cookbook_analysis_security import _validate_tar_file_security

    member = MagicMock(spec=tarfile.TarInfo)
    member.name = "devnode"
    member.size = 1
    member.issym.return_value = False
    member.islnk.return_value = False
    member.isfile.return_value = False
    member.isdir.return_value = False
    member.type = b"3"

    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Unsupported file type" in str(exc)


def test_pre_scan_tar_members_calls_validator(monkeypatch):
    from souschef.ui.pages.cookbook_analysis_security import _pre_scan_tar_members

    m1 = MagicMock(spec=tarfile.TarInfo)
    m1.size = 10
    m2 = MagicMock(spec=tarfile.TarInfo)
    m2.size = 20

    called = {"count": 0}

    def fake_validate(member, file_count, total_size):
        called["count"] += 1

    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security._validate_tar_file_security",
        fake_validate,
    )

    _pre_scan_tar_members([m1, m2])
    assert called["count"] == 2


def test_extract_tar_members_sanitises_paths(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_members

    tar_ref = MagicMock()
    member = MagicMock(spec=tarfile.TarInfo)
    member.name = "roles/nginx/tasks/main.yml"

    _extract_tar_members(tar_ref, [member], tmp_path)

    tar_ref.extractall.assert_called_once()


def test_extract_zip_securely(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_zip_securely

    archive = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("roles/nginx/tasks/main.yml", "- name: task\n")

    out = tmp_path / "out"
    out.mkdir()

    _extract_zip_securely(archive, out)
    assert (out / "roles" / "nginx" / "tasks" / "main.yml").exists()


def test_extract_tar_securely_invalid_path(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_securely

    not_file = tmp_path / "missing.tar"
    try:
        _extract_tar_securely(not_file, tmp_path, gzipped=False)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "not a file" in str(exc)


def test_sanitize_filename():
    from souschef.ui.pages.cookbook_analysis_utilities import _sanitize_filename

    assert _sanitize_filename("../bad\\name\x00") == "__bad_name_"
    assert _sanitize_filename("   ") == "unnamed"


def test_get_secure_ai_config_path(tmp_path):
    from souschef.ui.pages.cookbook_analysis_utilities import _get_secure_ai_config_path

    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        config_path = _get_secure_ai_config_path()

    assert config_path.name == "ai_config.json"
    assert config_path.parent.exists()


def test_is_within_base(tmp_path):
    from souschef.ui.pages.cookbook_analysis_utilities import _is_within_base

    base = tmp_path / "base"
    base.mkdir()
    inside = base / "a" / "b"
    inside.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()

    assert _is_within_base(base, inside)
    assert not _is_within_base(base, outside)
