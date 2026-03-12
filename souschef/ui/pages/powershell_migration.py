"""
PowerShell Migration Page for SousChef UI.

Provides a Streamlit interface for converting PowerShell scripts and
directories to Ansible playbooks targeting Windows hosts via AAP/AWX.
Supports:
- Single script file path input
- Directory of scripts
- Resource listing with unsupported construct warnings
- Playbook download
- AI-assisted conversion for unsupported constructs (.NET, WMI, COM, DSC)
- Enterprise artefact generation (Execution Environment, inventory, credentials)
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # type: ignore[assignment]  # pragma: no cover

from souschef.converters.powershell_to_ansible import (
    convert_powershell_directory_to_ansible,
    convert_powershell_directory_to_ansible_with_ai,
    convert_powershell_script_to_ansible,
    convert_powershell_script_to_ansible_with_ai,
    generate_aap_windows_credential_vars,
    generate_windows_ee_definition,
    generate_windows_inventory_template,
    get_powershell_ansible_module_map,
)
from souschef.parsers.powershell import (
    parse_powershell_directory,
    parse_powershell_script,
)

INPUT_METHOD_FILE_PATH = "Script File Path"
INPUT_METHOD_DIR_PATH = "Script Directory Path"
INPUT_METHODS = [INPUT_METHOD_FILE_PATH, INPUT_METHOD_DIR_PATH]

MIME_TEXT_YAML = "text/yaml"
MIME_TEXT_PLAIN = "text/plain"

_AI_PROVIDERS = ["anthropic", "openai", "watson", "lightspeed"]
_DEFAULT_PROVIDER = "anthropic"
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

_WINRM_TRANSPORTS = ["ntlm", "kerberos", "certificate", "basic", "credssp"]


def show_powershell_migration_page() -> None:
    """Render the PowerShell Migration page in the Streamlit UI."""
    if st is None:
        return  # pragma: no cover

    st.header("PowerShell Migration")
    st.markdown(
        "Convert PowerShell scripts to Ansible playbooks for Windows hosts "
        "managed by Ansible Automation Platform (AAP). "
        "Supports ``Install-WindowsFeature``, ``Set-Service``, registry, "
        "firewall, scheduled tasks, IIS, users, and more. "
        "Use **Convert with AI** to handle advanced constructs such as "
        ".NET P/Invoke, WMI queries, COM objects, and DSC Configuration blocks."
    )

    input_method = st.radio(
        "Input method",
        INPUT_METHODS,
        horizontal=True,
        key="ps_input_method",
    )

    if input_method == INPUT_METHOD_FILE_PATH:
        _show_script_file_section()
    else:
        _show_directory_section()

    st.divider()
    _show_enterprise_artefacts_section()
    st.divider()
    _show_cmdlet_reference()


def _get_ai_settings() -> dict[str, str | float | int]:
    """
    Retrieve AI settings from the inline expander controls.

    Returns:
        Dictionary with ``provider``, ``api_key``, ``model``, ``temperature``,
        ``max_tokens``, ``project_id``, and ``base_url`` keys.

    """
    if st is None:  # pragma: no cover
        return {}  # pragma: no cover

    with st.expander("AI Settings (required for Convert with AI)"):
        provider = st.selectbox(
            "AI Provider",
            _AI_PROVIDERS,
            key="ps_ai_provider",
        )
        api_key = st.text_input(
            "API Key",
            type="password",
            key="ps_ai_api_key",
            help="API key for the selected AI provider.",
        )
        model = st.text_input(
            "Model",
            value=_DEFAULT_MODEL,
            key="ps_ai_model",
            help="Model identifier (e.g. claude-3-5-sonnet-20241022, gpt-4o).",
        )
        col_t, col_m = st.columns(2)
        with col_t:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.05,
                key="ps_ai_temperature",
            )
        with col_m:
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=500,
                max_value=8000,
                value=4000,
                step=500,
                key="ps_ai_max_tokens",
            )
        project_id = st.text_input(
            "Project ID (IBM Watsonx only)",
            key="ps_ai_project_id",
        )
        base_url = st.text_input(
            "Base URL (optional override)",
            key="ps_ai_base_url",
        )

    return {
        "provider": provider or _DEFAULT_PROVIDER,
        "api_key": api_key or "",
        "model": model or _DEFAULT_MODEL,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "project_id": project_id or "",
        "base_url": base_url or "",
    }


def _show_script_file_section() -> None:
    """Render the script file input and analysis section."""
    if st is None:
        return  # pragma: no cover

    st.subheader("Analyse PowerShell Script")
    script_path = st.text_input(
        "Script path (.ps1 / .psm1)",
        key="ps_script_path",
        placeholder="/path/to/script.ps1",
        help="Enter the path to a PowerShell script file (.ps1 or .psm1)",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        analyse_clicked = st.button(
            "Analyse Script",
            key="ps_analyse_script",
            type="secondary",
        )
    with col2:
        convert_clicked = st.button(
            "Convert to Ansible",
            key="ps_convert_script",
            type="primary",
        )
    with col3:
        ai_clicked = st.button(
            "Convert with AI",
            key="ps_ai_script",
            type="primary",
            help=(
                "Use an LLM to convert unsupported constructs "
                "(.NET, WMI, COM, DSC Configuration, etc.)"
            ),
        )

    if not script_path:
        if analyse_clicked or convert_clicked or ai_clicked:
            st.warning("Please enter a script path.")
        return

    ai_cfg = _get_ai_settings() if ai_clicked else {}

    if analyse_clicked:
        _run_script_analysis(script_path)
    if convert_clicked:
        _run_script_conversion(script_path)
    if ai_clicked:
        _run_script_ai_conversion(script_path, ai_cfg)


def _show_directory_section() -> None:
    """Render the directory input and analysis section."""
    if st is None:
        return  # pragma: no cover

    st.subheader("Analyse PowerShell Directory")
    dir_path = st.text_input(
        "Directory path",
        key="ps_dir_path",
        placeholder="/path/to/scripts",
        help="Enter the path to a directory of PowerShell scripts",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        analyse_clicked = st.button(
            "Analyse Directory",
            key="ps_analyse_dir",
            type="secondary",
        )
    with col2:
        convert_clicked = st.button(
            "Convert to Ansible",
            key="ps_convert_dir",
            type="primary",
        )
    with col3:
        ai_clicked = st.button(
            "Convert with AI",
            key="ps_ai_dir",
            type="primary",
            help=(
                "Use an LLM to convert unsupported constructs "
                "(.NET, WMI, COM, DSC Configuration, etc.)"
            ),
        )

    if not dir_path:
        if analyse_clicked or convert_clicked or ai_clicked:
            st.warning("Please enter a directory path.")
        return

    ai_cfg = _get_ai_settings() if ai_clicked else {}

    if analyse_clicked:
        _run_dir_analysis(dir_path)
    if convert_clicked:
        _run_dir_conversion(dir_path)
    if ai_clicked:
        _run_dir_ai_conversion(dir_path, ai_cfg)


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------


def _run_script_analysis(script_path: str) -> None:
    """Execute script analysis and display results."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Analysing PowerShell script..."):
        result = parse_powershell_script(script_path)

    _display_analysis_result(result, "script")


def _run_dir_analysis(dir_path: str) -> None:
    """Execute directory analysis and display results."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Analysing PowerShell directory..."):
        result = parse_powershell_directory(dir_path)

    _display_analysis_result(result, "directory")


def _run_script_conversion(script_path: str) -> None:
    """Execute script conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Converting PowerShell script to Ansible..."):
        playbook = convert_powershell_script_to_ansible(script_path)

    _display_conversion_result(playbook, script_path)


def _run_dir_conversion(dir_path: str) -> None:
    """Execute directory conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Converting PowerShell directory to Ansible..."):
        playbook = convert_powershell_directory_to_ansible(dir_path)

    _display_conversion_result(playbook, dir_path)


def _run_script_ai_conversion(
    script_path: str, ai_cfg: dict[str, str | float | int]
) -> None:
    """Execute AI-assisted script conversion and display the playbook."""
    if st is None:
        return  # pragma: no cover

    if not ai_cfg.get("api_key"):
        st.warning(
            "An API key is required for AI-assisted conversion. "
            "Expand the AI Settings panel above and enter your key."
        )
        return

    with st.spinner("Converting PowerShell script to Ansible with AI..."):
        playbook = convert_powershell_script_to_ansible_with_ai(
            script_path,
            ai_provider=str(ai_cfg.get("provider", _DEFAULT_PROVIDER)),
            api_key=str(ai_cfg.get("api_key", "")),
            model=str(ai_cfg.get("model", _DEFAULT_MODEL)),
            temperature=float(ai_cfg.get("temperature", 0.3)),
            max_tokens=int(ai_cfg.get("max_tokens", 4000)),
            project_id=str(ai_cfg.get("project_id", "")),
            base_url=str(ai_cfg.get("base_url", "")),
        )

    _display_conversion_result(playbook, script_path, ai_enhanced=True)


def _run_dir_ai_conversion(
    dir_path: str, ai_cfg: dict[str, str | float | int]
) -> None:
    """Execute AI-assisted directory conversion and display the playbook."""
    if st is None:
        return  # pragma: no cover

    if not ai_cfg.get("api_key"):
        st.warning(
            "An API key is required for AI-assisted conversion. "
            "Expand the AI Settings panel above and enter your key."
        )
        return

    with st.spinner("Converting PowerShell directory to Ansible with AI..."):
        playbook = convert_powershell_directory_to_ansible_with_ai(
            dir_path,
            ai_provider=str(ai_cfg.get("provider", _DEFAULT_PROVIDER)),
            api_key=str(ai_cfg.get("api_key", "")),
            model=str(ai_cfg.get("model", _DEFAULT_MODEL)),
            temperature=float(ai_cfg.get("temperature", 0.3)),
            max_tokens=int(ai_cfg.get("max_tokens", 4000)),
            project_id=str(ai_cfg.get("project_id", "")),
            base_url=str(ai_cfg.get("base_url", "")),
        )

    _display_conversion_result(playbook, dir_path, ai_enhanced=True)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _display_analysis_result(result: str, source_type: str) -> None:
    """Display analysis results with appropriate formatting."""
    if st is None:
        return  # pragma: no cover

    if result.startswith("Error:") or result.startswith("An error occurred:"):
        st.error(result)
        return

    if result.startswith("Warning:"):
        st.warning(result)
        return

    st.success(f"PowerShell {source_type} analysis complete.")

    if "Unsupported Constructs" in result and "none detected" not in result:
        st.warning(
            "Unsupported constructs detected. Use **Convert with AI** to "
            "attempt automatic conversion."
        )

    st.text_area(
        "Analysis Report",
        value=result,
        height=400,
        key=f"ps_analysis_result_{source_type}",
    )

    st.download_button(
        "Download Analysis Report",
        data=result,
        file_name=f"powershell_{source_type}_analysis.txt",
        mime=MIME_TEXT_PLAIN,
        key=f"ps_download_analysis_{source_type}",
    )


def _display_conversion_result(
    playbook: str, source_path: str, *, ai_enhanced: bool = False
) -> None:
    """Display converted Ansible playbook with download option."""
    if st is None:
        return  # pragma: no cover

    if playbook.startswith("Error:") or playbook.startswith("An error occurred:"):
        st.error(playbook)
        return

    if playbook.startswith("Warning:"):
        st.warning(playbook)
        return

    if ai_enhanced:
        st.success(
            "PowerShell script converted to Ansible playbook with AI assistance."
        )
        st.info(
            "The AI-generated playbook may include best-effort conversions for "
            "unsupported constructs. Review carefully before use in production."
        )
    else:
        st.success("PowerShell script converted to Ansible playbook successfully.")

    if not ai_enhanced and (
        "WARNING:" in playbook or "manual review" in playbook.lower()
    ):
        st.warning(
            "Some cmdlets require manual review. Check tasks labelled WARNING "
            "in the playbook. Use **Convert with AI** to attempt automatic "
            "conversion of these constructs."
        )

    st.code(playbook, language="yaml")

    safe_name = Path(source_path).stem.replace(" ", "_")
    suffix = "_ai" if ai_enhanced else ""
    filename = f"{safe_name}{suffix}_ansible_playbook.yml"

    st.download_button(
        "Download Ansible Playbook",
        data=playbook,
        file_name=filename,
        mime=MIME_TEXT_YAML,
        key=f"ps_download_playbook{'_ai' if ai_enhanced else ''}",
    )


# ---------------------------------------------------------------------------
# Enterprise artefacts section
# ---------------------------------------------------------------------------


def _show_enterprise_artefacts_section() -> None:
    """Render the enterprise artefact generation section."""
    if st is None:
        return  # pragma: no cover

    st.subheader("Enterprise AAP Artefacts")
    st.markdown(
        "Generate ancillary files required for an enterprise Windows deployment "
        "on Ansible Automation Platform."
    )

    col_ee, col_inv, col_cred = st.columns(3)

    with col_ee:
        _show_ee_generator()

    with col_inv:
        _show_inventory_generator()

    with col_cred:
        _show_credential_generator()


def _show_ee_generator() -> None:
    """Render the Execution Environment definition generator."""
    if st is None:
        return  # pragma: no cover

    st.markdown("**Execution Environment**")
    ee_name = st.text_input(
        "EE name",
        value="windows-ee",
        key="ps_ee_name",
    )
    base_image = st.text_input(
        "Base image",
        value=(
            "registry.redhat.io/ansible-automation-platform-25/"
            "ee-supported-rhel9:latest"
        ),
        key="ps_ee_base_image",
    )
    extra_py = st.text_input(
        "Extra Python packages (comma-separated)",
        key="ps_ee_extra_py",
    )
    extra_cols = st.text_input(
        "Extra Galaxy collections (comma-separated)",
        key="ps_ee_extra_cols",
    )
    if st.button("Generate EE Definition", key="ps_gen_ee"):
        py_pkgs = [p.strip() for p in extra_py.split(",") if p.strip()]
        cols = [c.strip() for c in extra_cols.split(",") if c.strip()]
        _default_ee_image = (
            "registry.redhat.io/ansible-automation-platform-25/"
            "ee-supported-rhel9:latest"
        )
        result = generate_windows_ee_definition(
            ee_name=ee_name or "windows-ee",
            base_image=base_image or _default_ee_image,
            python_packages=py_pkgs or None,
            galaxy_collections=cols or None,
        )
        st.code(result, language="yaml")
        st.download_button(
            "Download execution-environment.yml",
            data=result,
            file_name="execution-environment.yml",
            mime=MIME_TEXT_YAML,
            key="ps_download_ee",
        )


def _show_inventory_generator() -> None:
    """Render the Windows inventory template generator."""
    if st is None:
        return  # pragma: no cover

    st.markdown("**Windows Inventory**")
    hosts_raw = st.text_input(
        "Hosts (comma-separated)",
        value="win-server-01,win-server-02",
        key="ps_inv_hosts",
    )
    group_name = st.text_input(
        "Group name",
        value="windows",
        key="ps_inv_group",
    )
    transport = st.selectbox(
        "WinRM transport",
        _WINRM_TRANSPORTS,
        key="ps_inv_transport",
    )
    if st.button("Generate Inventory", key="ps_gen_inv"):
        host_list = [h.strip() for h in hosts_raw.split(",") if h.strip()]
        result = generate_windows_inventory_template(
            hosts=host_list or None,
            group_name=group_name or "windows",
            transport=str(transport) if transport else "ntlm",
        )
        st.code(result, language="yaml")
        st.download_button(
            "Download inventory.yml",
            data=result,
            file_name="inventory.yml",
            mime=MIME_TEXT_YAML,
            key="ps_download_inv",
        )


def _show_credential_generator() -> None:
    """Render the Windows credential variable generator."""
    if st is None:
        return  # pragma: no cover

    st.markdown("**Credential Variables**")
    transport = st.selectbox(
        "WinRM transport",
        _WINRM_TRANSPORTS,
        key="ps_cred_transport",
    )
    port = st.number_input(
        "WinRM port",
        min_value=1,
        max_value=65535,
        value=5985,
        step=1,
        key="ps_cred_port",
    )
    validate_certs = st.checkbox(
        "Validate SSL certs",
        value=True,
        key="ps_cred_validate",
    )
    if st.button("Generate Credential Vars", key="ps_gen_cred"):
        result = generate_aap_windows_credential_vars(
            transport=str(transport) if transport else "ntlm",
            port=int(port),
            validate_certs=bool(validate_certs),
        )
        st.code(result, language="yaml")
        st.download_button(
            "Download group_vars/windows.yml",
            data=result,
            file_name="windows.yml",
            mime=MIME_TEXT_YAML,
            key="ps_download_cred",
        )


# ---------------------------------------------------------------------------
# Cmdlet reference table
# ---------------------------------------------------------------------------


def _show_cmdlet_reference() -> None:
    """Display a reference table of supported PowerShell cmdlets."""
    if st is None:
        return  # pragma: no cover

    with st.expander("Supported PowerShell Cmdlets"):
        module_map = get_powershell_ansible_module_map()
        st.markdown("| PowerShell Cmdlet | Ansible Module |")
        st.markdown("|---|---|")
        for cmdlet, module in sorted(module_map.items()):
            st.markdown(f"| `{cmdlet}` | `{module}` |")

        st.markdown("")
        st.markdown(
            "Cmdlets not listed above will generate an ``ansible.windows.win_shell`` "
            "stub task requiring manual review. Use **Convert with AI** to attempt "
            "automatic conversion."
        )
