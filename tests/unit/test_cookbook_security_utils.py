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


def test_extract_zip_securely_handles_directory_entries(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_zip_securely

    archive = tmp_path / "dir.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("roles/", "")
        zf.writestr("roles/nginx/tasks/main.yml", "- name: task\n")

    out = tmp_path / "outdir"
    out.mkdir()
    _extract_zip_securely(archive, out)
    assert (out / "roles").exists()


def test_validate_zip_file_security_branch_errors(monkeypatch):
    from souschef.ui.pages.cookbook_analysis_security import _validate_zip_file_security

    info = zipfile.ZipInfo("ok.txt")
    info.file_size = 1

    # too many files
    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILES", 0)
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Too many files" in str(exc)

    # total size too large
    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILES", 1000)
    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security.MAX_ARCHIVE_SIZE", 0
    )
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Total archive size too large" in str(exc)

    # path traversal
    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security.MAX_ARCHIVE_SIZE", 10**9
    )
    info.filename = "../evil"
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Path traversal detected" in str(exc)

    # depth
    info.filename = "/".join(["d"] * 20)
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Directory depth too deep" in str(exc)

    # symlink branch
    info.filename = "ok.txt"
    info.external_attr = 0xA000
    try:
        _validate_zip_file_security(info, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Symlinks not allowed" in str(exc)


def test_extract_tar_securely_invalid_tarfile(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_securely

    f = tmp_path / "fake.tar"
    f.write_text("not tar")
    try:
        _extract_tar_securely(f, tmp_path, gzipped=False)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Invalid or corrupted TAR archive" in str(exc)


def test_extract_tar_securely_tarerror_and_generic(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_securely

    f = tmp_path / "good.tar"
    f.write_bytes(b"x")

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("tarfile.is_tarfile", return_value=True),
        patch("tarfile.open", side_effect=tarfile.TarError("bad")),
    ):
        try:
            _extract_tar_securely(f, tmp_path, gzipped=False)
            raise AssertionError("Expected ValueError")
        except ValueError as exc:
            assert "Invalid or corrupted TAR archive" in str(exc)

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("tarfile.is_tarfile", return_value=True),
        patch("tarfile.open", side_effect=RuntimeError("boom")),
    ):
        try:
            _extract_tar_securely(f, tmp_path, gzipped=False)
            raise AssertionError("Expected ValueError")
        except ValueError as exc:
            assert "Failed to process TAR archive" in str(exc)


def test_extract_tar_securely_success_filter_branch(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_securely

    f = tmp_path / "ok.tar"
    f.write_bytes(b"x")
    tar_ref = MagicMock()
    tar_ref.__enter__.return_value = tar_ref
    tar_ref.__exit__.return_value = None
    tar_ref.getmembers.return_value = []

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("tarfile.is_tarfile", return_value=True),
        patch("tarfile.open", return_value=tar_ref),
        patch(
            "souschef.ui.pages.cookbook_analysis_security._pre_scan_tar_members"
        ) as pre,
        patch(
            "souschef.ui.pages.cookbook_analysis_security._extract_tar_members"
        ) as ext,
    ):
        _extract_tar_securely(f, tmp_path, gzipped=False)

    pre.assert_called_once()
    ext.assert_called_once()


def test_extract_tar_securely_sets_filter_open_kwarg(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_securely

    f = tmp_path / "ok2.tar"
    f.write_bytes(b"x")
    tar_ref = MagicMock()
    tar_ref.__enter__.return_value = tar_ref
    tar_ref.__exit__.return_value = None
    tar_ref.getmembers.return_value = []

    # Force branch where inspect.signature reports a 'filter' parameter.
    fake_signature = MagicMock()
    fake_signature.parameters = {"name": object(), "mode": object(), "filter": object()}

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("tarfile.is_tarfile", return_value=True),
        patch("inspect.signature", return_value=fake_signature),
        patch("tarfile.open", return_value=tar_ref) as open_mock,
        patch("souschef.ui.pages.cookbook_analysis_security._pre_scan_tar_members"),
        patch("souschef.ui.pages.cookbook_analysis_security._extract_tar_members"),
    ):
        _extract_tar_securely(f, tmp_path, gzipped=False)

    assert open_mock.call_args.kwargs.get("filter") == "data"


def test_extract_tar_members_data_filter_none_skips(tmp_path):
    from souschef.ui.pages.cookbook_analysis_security import _extract_tar_members

    tar_ref = MagicMock()
    member = MagicMock(spec=tarfile.TarInfo)
    member.name = "roles/nginx/tasks/main.yml"

    with patch("tarfile.data_filter", return_value=None):
        _extract_tar_members(tar_ref, [member], tmp_path)

    tar_ref.extractall.assert_not_called()


def test_validate_tar_file_security_branch_errors(monkeypatch):
    from souschef.ui.pages.cookbook_analysis_security import _validate_tar_file_security

    member = MagicMock(spec=tarfile.TarInfo)
    member.name = "ok.txt"
    member.size = 1
    member.issym.return_value = False
    member.islnk.return_value = False
    member.isfile.return_value = True
    member.isdir.return_value = False
    member.type = b"0"

    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILES", 0)
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Too many files" in str(exc)

    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILES", 1000)
    monkeypatch.setattr("souschef.ui.pages.cookbook_analysis_security.MAX_FILE_SIZE", 0)
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "File too large" in str(exc)

    member.size = 1
    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security.MAX_FILE_SIZE", 100
    )
    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security.MAX_ARCHIVE_SIZE", 0
    )
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Total archive size too large" in str(exc)

    monkeypatch.setattr(
        "souschef.ui.pages.cookbook_analysis_security.MAX_ARCHIVE_SIZE", 10**9
    )
    member.name = "../evil"
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Path traversal detected" in str(exc)

    member.name = "/".join(["d"] * 20)
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Directory depth too deep" in str(exc)

    member.name = "bad.exe"
    try:
        _validate_tar_file_security(member, 0, 0)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Blocked file type" in str(exc)
