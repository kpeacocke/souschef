"""Validation Reports Page for SousChef UI."""

import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st


def _run_ansible_lint(playbook_path: str) -> tuple[bool, str]:
    """
    Run ansible-lint on a playbook and return results.

    Args:
        playbook_path: Path to the playbook file.

    Returns:
        Tuple of (success: bool, output: str).

    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ansible_lint", str(playbook_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Validation timeout after 30 seconds"
    except Exception as e:
        return False, f"Error running ansible-lint: {e}"


def _validate_playbooks_in_directory(
    directory: str,
) -> dict[str, tuple[bool, str]]:
    """
    Validate all playbooks in a directory.

    Args:
        directory: Path to directory containing playbook files.

    Returns:
        Dictionary mapping playbook names to (success, output) tuples.

    """
    playbook_dir = Path(directory)
    results = {}

    if not playbook_dir.exists():
        return {"error": (False, f"Directory not found: {directory}")}

    # Find all YAML files
    playbook_files = list(playbook_dir.glob("*.yml")) + list(
        playbook_dir.glob("*.yaml")
    )

    if not playbook_files:
        return {"no_playbooks": (False, "No playbook files found in directory")}

    for playbook_file in playbook_files:
        success, output = _run_ansible_lint(str(playbook_file))
        results[playbook_file.name] = (success, output)

    return results


def _parse_ansible_lint_output(output: str) -> dict[str, Any]:
    """
    Parse ansible-lint output into structured format.

    Args:
        output: Raw ansible-lint output.

    Returns:
        Dictionary with parsed results (warnings, errors, etc.).

    """
    lines = output.strip().split("\n")
    parsed: dict[str, Any] = {
        "warnings": 0,
        "errors": 0,
        "info": 0,
        "details": [],
    }

    for line in lines:
        if "warning" in line.lower():
            parsed["warnings"] = int(parsed["warnings"]) + 1
        elif "error" in line.lower():
            parsed["errors"] = int(parsed["errors"]) + 1
        elif "info" in line.lower():
            parsed["info"] = int(parsed["info"]) + 1

        if line.strip():
            parsed["details"].append(line)

    return parsed


def show_validation_reports_page():
    """Show the validation reports page."""
    # Add back to dashboard button
    col1, _ = st.columns([1, 4])
    with col1:
        if st.button(
            "← Back to Dashboard",
            help="Return to main dashboard",
            key="back_to_dashboard_from_validation",
        ):
            st.session_state.current_page = "Dashboard"
            st.rerun()

    st.header("✅ Validation Reports")

    # Check if we have converted playbooks to validate
    if not hasattr(st.session_state, "converted_playbooks_path"):
        st.info(
            "No converted playbooks available for validation. "
            "Please run a cookbook analysis first to generate Ansible playbooks."
        )
        return

    converted_path = st.session_state.converted_playbooks_path
    playbook_path = Path(converted_path)

    if not playbook_path.exists():
        st.warning(f"Converted playbooks directory not found: {converted_path}")
        return

    st.subheader("Running Ansible Validation")
    st.markdown("Validating converted Ansible playbooks using ansible-lint...")

    # Run validation
    with st.spinner("Validating playbooks..."):
        results = _validate_playbooks_in_directory(converted_path)

    if not results:
        st.warning("No playbooks found to validate")
        return

    # Display summary
    total_playbooks = len(results)
    passed_count = sum(1 for success, _ in results.values() if success)
    failed_count = total_playbooks - passed_count

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Playbooks", total_playbooks)
    with col2:
        st.metric("Passed Validation", passed_count, delta=f"✓ {passed_count}")
    with col3:
        st.metric(
            "Failed Validation",
            failed_count,
            delta=f"✗ {failed_count}" if failed_count > 0 else "✓ None",
        )

    # Display detailed results
    st.subheader("Detailed Validation Results")

    if passed_count == total_playbooks:
        st.success("✅ All playbooks passed validation!")
    else:
        st.warning(f"⚠️ {failed_count} playbook(s) have validation issues")

    # Create tabs for each playbook
    if len(results) > 1:
        tabs = st.tabs(list(results.keys()))
        for tab, (playbook_name, (success, output)) in zip(
            tabs, results.items(), strict=True
        ):
            with tab:
                _display_validation_result(playbook_name, success, output)
    else:
        # Single playbook, no tabs needed
        for playbook_name, (success, output) in results.items():
            _display_validation_result(playbook_name, success, output)

    # Export validation report
    st.subheader("Export Report")
    if st.button("📥 Download Validation Report"):
        report = _generate_validation_report(results)
        st.download_button(
            label="Download as Text",
            data=report,
            file_name="validation_report.txt",
            mime="text/plain",
        )


def _display_validation_result(playbook_name: str, success: bool, output: str) -> None:
    """
    Display validation result for a single playbook.

    Args:
        playbook_name: Name of the playbook.
        success: Whether validation passed.
        output: Validation output/errors.

    """
    if success:
        st.success(f"✅ {playbook_name} passed validation")
    else:
        st.error(f"❌ {playbook_name} failed validation")

    with st.expander("View Details"):
        if output:
            st.code(output, language="text")
        else:
            st.info("No detailed output available")


def _generate_validation_report(results: dict[str, tuple[bool, str]]) -> str:
    """
    Generate a text validation report.

    Args:
        results: Dictionary of validation results.

    Returns:
        Formatted validation report as string.

    """
    report_lines = [
        "=" * 80,
        "ANSIBLE PLAYBOOK VALIDATION REPORT",
        "=" * 80,
        "",
    ]

    # Summary
    total = len(results)
    passed = sum(1 for success, _ in results.values() if success)
    failed = total - passed

    report_lines.extend(
        [
            "SUMMARY",
            "-" * 80,
            f"Total Playbooks: {total}",
            f"Passed: {passed}",
            f"Failed: {failed}",
            "",
        ]
    )

    # Detailed results
    report_lines.extend(
        [
            "DETAILED RESULTS",
            "-" * 80,
            "",
        ]
    )

    for playbook_name, (success, output) in results.items():
        status = "PASSED" if success else "FAILED"
        report_lines.extend(
            [
                f"Playbook: {playbook_name}",
                f"Status: {status}",
                "",
                "Output:",
                output if output else "(No output)",
                "",
                "-" * 80,
                "",
            ]
        )

    return "\n".join(report_lines)
