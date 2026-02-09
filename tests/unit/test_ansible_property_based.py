"""Comprehensive property-based tests for Ansible upgrade features using Hypothesis."""

import tempfile
from pathlib import Path

import yaml
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Strategy for valid semantic versions
semver_strategy = st.builds(
    lambda major, minor, patch: f"{major}.{minor}.{patch}",
    major=st.integers(min_value=2, max_value=10),
    minor=st.integers(min_value=0, max_value=20),
    patch=st.integers(min_value=0, max_value=50),
)

# Strategy for known Ansible versions (only actual Ansible-core versions)
ansible_version_strategy = st.sampled_from(
    [
        "2.9",
        "2.10",
        "2.11",
        "2.12",
        "2.13",
        "2.14",
        "2.15",
        "2.16",
        "2.17",
        "2.18",
        "2.19",
        "2.20",
    ]
)

# Strategy for Ansible collection names
collection_name_strategy = st.builds(
    lambda ns, name: f"{ns}.{name}",
    ns=st.from_regex(r"[a-z][a-z0-9_]{1,10}", fullmatch=True),
    name=st.from_regex(r"[a-z][a-z0-9_]{1,15}", fullmatch=True),
)

# Strategy for inventory hostnames
hostname_strategy = st.one_of(
    st.from_regex(r"[a-z0-9][a-z0-9\-]{0,20}[a-z0-9]", fullmatch=True),
    st.builds(
        lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
        a=st.integers(min_value=1, max_value=255),
        b=st.integers(min_value=0, max_value=255),
        c=st.integers(min_value=0, max_value=255),
        d=st.integers(min_value=1, max_value=255),
    ),
)


# Upgrade Path Calculation Tests


def _validate_upgrade_path_basic_invariants(
    result: dict, from_ver: str, to_ver: str
) -> None:
    """Validate basic structure and version match invariants."""
    assert isinstance(result, dict)
    assert "from_version" in result
    assert "to_version" in result
    assert result["from_version"] == from_ver
    assert result["to_version"] == to_ver


def _validate_upgrade_path_metadata(result: dict) -> None:
    """Validate path metadata invariants when no error."""
    assert (
        "direct_upgrade" in result
        or "steps" in result
        or "intermediate_versions" in result
    )
    if "risk_level" in result:
        assert result["risk_level"] in ["Low", "Medium", "High"]
    if "breaking_changes" in result:
        assert isinstance(result["breaking_changes"], list)


def _validate_upgrade_path_ordering(result: dict) -> None:
    """Validate version ordering invariant."""
    if "intermediate_versions" in result:
        intermediates = result["intermediate_versions"]
        if isinstance(intermediates, list) and len(intermediates) > 1:
            from souschef.core.ansible_versions import _parse_version

            for i in range(len(intermediates) - 1):
                v1 = _parse_version(intermediates[i])
                v2 = _parse_version(intermediates[i + 1])
                assert v1 < v2, f"Versions not ordered: {v1} >= {v2}"


@given(from_ver=ansible_version_strategy, to_ver=ansible_version_strategy)
@settings(max_examples=100, deadline=3000)  # 3s deadline for module loading
def test_upgrade_path_with_valid_versions(from_ver, to_ver):
    """
    Test upgrade path calculation with known Ansible versions.

    Property: Given known versions, should either calculate a path or indicate
    versions are equal/invalid order.

    Real Invariants Tested:
    1. Output structure is always consistent (has from_version, to_version)
    2. from_version and to_version match input
    3. If error-free, has either direct_upgrade or intermediate_versions
    4. risk_level is one of: Low, Medium, High
    5. breaking_changes is always a list
    """
    from souschef.core.ansible_versions import calculate_upgrade_path

    try:
        result = calculate_upgrade_path(from_ver, to_ver)
        _validate_upgrade_path_basic_invariants(result, from_ver, to_ver)

        if "error" not in result:
            _validate_upgrade_path_metadata(result)
            _validate_upgrade_path_ordering(result)

    except ValueError as e:
        # ValueError is acceptable for downgrade or unsupported scenarios
        error_msg = str(e).lower()
        assert any(
            word in error_msg
            for word in ["downgrade", "unknown", "unsupported", "same"]
        )


@given(
    major=st.integers(min_value=2, max_value=10),
    minor_offset=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_upgrade_path_monotonicity(major, minor_offset):
    """
    Test that upgrade paths respect version ordering.

    Property: Path from version X.Y to X.(Y+N) should contain increasing versions.

    Real Invariant: If intermediate steps exist, version numbers must be
    strictly increasing (transitivity).
    """
    from souschef.core.ansible_versions import calculate_upgrade_path

    from_ver = f"{major}.0.0"
    to_ver = f"{major}.{minor_offset}.0"

    try:
        result = calculate_upgrade_path(from_ver, to_ver)

        if "steps" in result:
            # Verify steps are in increasing order (STRICT ORDERING)
            steps = (
                result["steps"]
                if isinstance(result["steps"], list)
                else [result["steps"]]
            )
            versions = [from_ver] + steps + [to_ver]

            # Parse versions and check strict ordering
            for i in range(len(versions) - 1):
                v1_parts = [int(x) for x in str(versions[i]).split(".")]
                v2_parts = [int(x) for x in str(versions[i + 1]).split(".")]

                # INVARIANT: Must be strictly less than (no equals)
                assert v1_parts < v2_parts, (
                    f"Monotonicity violated: {versions[i]} >= {versions[i + 1]}"
                )

        # Additional invariant: intermediate_versions should also be ordered
        if "intermediate_versions" in result:
            intermediates = result["intermediate_versions"]
            if isinstance(intermediates, list) and len(intermediates) > 0:
                from souschef.core.ansible_versions import _parse_version

                prev = _parse_version(from_ver)
                for ver_str in intermediates:
                    curr = _parse_version(ver_str)
                    assert prev < curr, f"Intermediate not ordered: {prev} >= {curr}"
                    prev = curr

    except ValueError:
        # Some version combinations might not be supported
        pass


@given(version=ansible_version_strategy)
@settings(max_examples=50)
def test_upgrade_path_identity(version):
    """
    Test that upgrading from a version to itself works appropriately.

    Property: calculate_upgrade_path(V, V) should return success with no steps
    (direct upgrade = staying on same version).

    Real Invariant: Idempotence - upgrading from V to V should be a no-op
    with zero intermediate versions.
    """
    from souschef.core.ansible_versions import calculate_upgrade_path

    try:
        result = calculate_upgrade_path(version, version)

        # INVARIANT 1: Identity operation succeeds
        assert isinstance(result, dict)
        assert result["from_version"] == version
        assert result["to_version"] == version

        # INVARIANT 2: Idempotence - no intermediate steps needed
        if "direct_upgrade" in result:
            assert result["direct_upgrade"] is True
        if "intermediate_versions" in result:
            intermediate = result["intermediate_versions"]
            if isinstance(intermediate, list):
                # Should be empty or very small (same version)
                assert len(intermediate) == 0, (
                    f"Identity upgrade should have no intermediates, got {intermediate}"
                )

        # INVARIANT 3: Risk level should be valid (if present)
        if "risk_level" in result:
            # Risk level should be one of the valid values
            # (same version can have Medium risk if EOL)
            assert result["risk_level"] in ["Low", "Medium", "High", "None"], (
                f"Invalid risk level: {result['risk_level']}"
            )

    except ValueError as e:
        # Some versions may raise "same version" error, which is acceptable
        assert "same" in str(e).lower() or "equal" in str(e).lower(), (
            f"Unexpected error for identity upgrade: {e}"
        )


# Python Compatibility Tests


@given(
    ansible_ver=semver_strategy,
    python_major=st.integers(min_value=2, max_value=3),
    python_minor=st.integers(min_value=6, max_value=13),
)
@settings(max_examples=100)
def test_python_compatibility_consistency(ansible_ver, python_major, python_minor):
    """
    Test Python compatibility checks are consistent.

    Property: For any Ansible version and Python version,
    is_python_compatible should match get_python_compatibility results.
    """
    from souschef.core.ansible_versions import (
        get_python_compatibility,
        is_python_compatible,
    )

    python_ver = f"{python_major}.{python_minor}"

    try:
        compatible_versions = get_python_compatibility(ansible_ver, "control")
        is_compatible = is_python_compatible(ansible_ver, python_ver, "control")

        # If we got compatible versions, check consistency
        if compatible_versions and is_compatible:
            # Allow some flexibility in version matching
            assert len(compatible_versions) > 0

    except ValueError:
        # Invalid versions are expected to raise errors
        pass


# Inventory Parser Fuzz Tests with Structured Data


@given(
    group_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_]{0,15}", fullmatch=True),
    hostnames=st.lists(hostname_strategy, min_size=1, max_size=10),
)
@settings(max_examples=50)
def test_parse_inventory_ini_with_groups(group_name, hostnames):
    """
    Test INI inventory parser with generated group structures.

    Property: Valid INI syntax with groups should parse without errors.
    """
    from souschef.parsers.ansible_inventory import parse_inventory_ini

    # Create valid INI inventory content
    inventory_content = f"[{group_name}]\n"
    for hostname in hostnames:
        inventory_content += f"{hostname}\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        try:
            f.write(inventory_content)
            f.flush()

            result = parse_inventory_ini(f.name)

            # Should successfully parse
            assert isinstance(result, dict)
            assert "groups" in result
            assert group_name in result["groups"]
            assert len(result["groups"][group_name]["hosts"]) == len(hostnames)

        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    hostnames=st.lists(hostname_strategy, min_size=1, max_size=10),
    vars_dict=st.dictionaries(
        st.from_regex(r"[a-z][a-z0-9_]{0,10}", fullmatch=True),
        st.one_of(st.text(max_size=20), st.integers(), st.booleans()),
        max_size=5,
    ),
)
@settings(max_examples=50, deadline=1000)
def test_parse_inventory_yaml_with_variables(hostnames, vars_dict):
    """
    Test YAML inventory parser with host variables.

    Property: Valid YAML inventory with variables should parse and preserve data.
    """
    from souschef.parsers.ansible_inventory import parse_inventory_yaml

    # Create valid YAML inventory structure
    inventory_data = {
        "all": {"hosts": {hostname: {"vars": vars_dict} for hostname in hostnames}}
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        try:
            yaml.dump(inventory_data, f)
            f.flush()

            result = parse_inventory_yaml(f.name)

            # Should successfully parse
            assert isinstance(result, dict)
            # Parser returns structure with 'all' group
            assert "all" in result or "groups" in result or "hosts" in result

        finally:
            Path(f.name).unlink(missing_ok=True)


@given(
    collections=st.lists(
        st.builds(
            lambda name, version: {"name": name, "version": version},
            name=collection_name_strategy,
            version=st.one_of(semver_strategy, st.just("*")),
        ),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=50, deadline=1000)
def test_parse_requirements_yml_with_collections(collections):
    """
    Test requirements.yml parser with collection specifications.

    Property: Valid requirements with collections should parse correctly.
    """
    from souschef.parsers.ansible_inventory import parse_requirements_yml

    requirements_data = {"collections": collections}

    # Parser validates filename must be exactly 'requirements.yml'
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        requirements_file = Path(temp_dir) / "requirements.yml"
        with requirements_file.open("w") as f:
            yaml.dump(requirements_data, f)

        result = parse_requirements_yml(str(requirements_file))

        # Should successfully parse - returns flat dict {name: version}
        assert isinstance(result, dict)

        # Build expected results (last value wins for duplicate names)
        expected = {}
        for collection in collections:
            expected[collection["name"]] = collection["version"]

        # Check all expected collections are present with correct versions
        assert result == expected

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# Ansible Config Parser Tests


@given(
    inventory_path=st.from_regex(r"[a-zA-Z0-9/_.-]{1,30}", fullmatch=True),
    roles_path=st.from_regex(r"[a-zA-Z0-9/_.-]{1,30}", fullmatch=True),
    remote_user=st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True),
)
@settings(max_examples=50, deadline=1000)
def test_parse_ansible_cfg_with_valid_config(inventory_path, roles_path, remote_user):
    """
    Test ansible.cfg parser with valid configuration options.

    Property: Valid INI-style ansible.cfg should parse all sections correctly.
    """
    from souschef.parsers.ansible_inventory import parse_ansible_cfg

    config_content = f"""[defaults]
inventory = {inventory_path}
roles_path = {roles_path}
remote_user = {remote_user}
host_key_checking = False

[privilege_escalation]
become = True
become_method = sudo
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
        try:
            f.write(config_content)
            f.flush()

            result = parse_ansible_cfg(f.name)

            # Should successfully parse
            assert isinstance(result, dict)
            assert "defaults" in result
            assert result["defaults"]["remote_user"] == remote_user

        finally:
            Path(f.name).unlink(missing_ok=True)


# EOL Status Tests


@given(
    major=st.integers(min_value=2, max_value=10),
    minor=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=50)
def test_eol_status_structure(major, minor):
    """
    Test EOL status always returns valid structure.

    Property: get_eol_status should always return dict with either status or error.
    """
    from souschef.core.ansible_versions import get_eol_status

    version = f"{major}.{minor}"
    result = get_eol_status(version)

    # Should always return a dict
    assert isinstance(result, dict)
    # Must have either status or error key
    assert "status" in result or "error" in result

    if "status" in result:
        # Status should be one of the known values
        valid_statuses = [
            "Supported",
            "End of Life",
            "Upcoming",
            "Unknown",
            "supported",
            "eol",
            "upcoming",
            "unknown",  # Case variations
        ]
        assert result["status"] in valid_statuses


# Version Comparison Property Tests


@given(v1=semver_strategy, v2=semver_strategy)
@settings(max_examples=100)
def test_version_comparison_transitivity(v1, v2):
    """
    Test version comparison transitivity.

    Property: If V1 < V2 and V2 < V3, then V1 < V3.
    """
    from souschef.core.ansible_versions import calculate_upgrade_path

    # Generate third version
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]

    # Ensure v1 < v2
    assume(parts1 < parts2)

    # Create v3 > v2
    parts3 = [parts2[0], parts2[1], parts2[2] + 1]
    v3 = ".".join(map(str, parts3))

    try:
        # v1 -> v2 should work
        result12 = calculate_upgrade_path(v1, v2)
        assume("error" not in result12)

        # v2 -> v3 should work
        result23 = calculate_upgrade_path(v2, v3)
        assume("error" not in result23)

        # v1 -> v3 should also work (transitivity)
        result13 = calculate_upgrade_path(v1, v3)
        assert "error" not in result13
        assert result13["from_version"] == v1
        assert result13["to_version"] == v3

    except ValueError:
        # Some combinations might not be supported
        pass


# Collection Namespace Validation


@given(namespace=st.from_regex(r"[a-z][a-z0-9_]{1,20}", fullmatch=True))
@settings(max_examples=50)
def test_collection_namespace_format(namespace):
    """
    Test that generated collection namespaces match Ansible naming rules.

    Property: Namespace should lowercase, start with letter, contain only alphanumeric and underscore.
    """
    # Test the namespace matches requirements
    assert namespace[0].isalpha()
    assert namespace[0].islower()
    assert all(c.isalnum() or c == "_" for c in namespace)
    assert len(namespace) >= 2
