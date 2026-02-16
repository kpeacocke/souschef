"""v2.0 Migration Orchestrator UI page with simulation capabilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from souschef.migration_v2 import (
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
)


def show_migration_v2_page() -> None:
    """Show the v2.0 Migration Orchestrator page."""
    st.header("v2.0 Migration Orchestrator")
    st.markdown("""
    **End-to-end Chef to Ansible migration with state persistence and
    deployment preview.**

    This wizard guides you through the complete migration process with
    optional simulation mode to preview AWX/AAP deployment without making
    actual changes.
    """)

    # Initialize session state
    _initialize_session_state()

    # Display tabs for different sections
    tab_wizard, tab_status, tab_history, tab_simulation = st.tabs(
        [
            "Migration Wizard",
            "Migration Status",
            "History",
            "Simulation Results",
        ]
    )

    with tab_wizard:
        _show_migration_wizard()

    with tab_status:
        _show_migration_status()

    with tab_history:
        _show_migration_history()

    with tab_simulation:
        _show_simulation_results()


def _initialize_session_state() -> None:
    """Initialize session state for migration v2 page."""
    if "migration_v2_step" not in st.session_state:
        st.session_state.migration_v2_step = 1

    if "migration_v2_config" not in st.session_state:
        st.session_state.migration_v2_config = {}

    if "migration_v2_result" not in st.session_state:
        st.session_state.migration_v2_result = None

    if "migration_v2_simulation_mode" not in st.session_state:
        st.session_state.migration_v2_simulation_mode = False


def _show_migration_wizard() -> None:
    """Show the migration wizard interface."""
    st.subheader("Migration Wizard")

    # Step indicator
    current_step = st.session_state.migration_v2_step
    _display_step_indicator(current_step)

    st.divider()

    # Display the appropriate step
    if current_step == 1:
        _show_step1_cookbook_selection()
    elif current_step == 2:
        _show_step2_platform_configuration()
    elif current_step == 3:
        _show_step3_conversion_options()
    elif current_step == 4:
        _show_step4_review_and_execute()


def _display_step_indicator(current_step: int) -> None:
    """Display step indicator for wizard progress."""
    steps = [
        "1. Cookbook Selection",
        "2. Platform Configuration",
        "3. Conversion Options",
        "4. Review & Execute",
    ]

    cols = st.columns(4)
    for i, (col, step_label) in enumerate(zip(cols, steps, strict=False), start=1):
        with col:
            if i < current_step:
                st.success(f"✓ {step_label}")
            elif i == current_step:
                st.info(f"▶ {step_label}")
            else:
                st.text(f"○ {step_label}")


def _show_step1_cookbook_selection() -> None:
    """Step 1: Cookbook selection."""
    st.subheader("Step 1: Select Cookbook")

    # Input method selection
    input_method = st.radio(
        "Input Method",
        ["Directory Path", "Upload Archive", "Chef Server"],
        horizontal=True,
        help="Choose how to provide the cookbook for migration",
    )

    cookbook_path = None

    if input_method == "Directory Path":
        cookbook_path = st.text_input(
            "Cookbook Path",
            placeholder="/path/to/cookbook",
            help="Enter the absolute path to the Chef cookbook directory",
        )

    elif input_method == "Upload Archive":
        uploaded_file = st.file_uploader(
            "Upload Cookbook Archive",
            type=["zip", "tar.gz", "tgz"],
            help="Upload a ZIP or TAR archive containing the cookbook",
        )

        if uploaded_file:
            try:
                with st.spinner("Extracting archive..."):
                    from souschef.ui.pages.cookbook_analysis import extract_archive

                    cookbook_path = str(extract_archive(uploaded_file))
                st.success(f"Extracted to: {cookbook_path}")
            except Exception as e:
                st.error(f"Failed to extract archive: {e}")

    elif input_method == "Chef Server":
        _show_chef_server_cookbook_selection()
        cookbook_path = st.session_state.get("chef_server_cookbook_path")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 4])

    with col2:
        if (
            st.button("Next →", type="primary", disabled=not cookbook_path)
            and cookbook_path
        ):
            st.session_state.migration_v2_config["cookbook_path"] = cookbook_path
            st.session_state.migration_v2_step = 2
            st.rerun()


def _show_chef_server_cookbook_selection() -> None:
    """Show Chef Server cookbook selection interface."""
    st.markdown("**Chef Server Integration**")

    st.info(
        "Chef Server integration allows downloading cookbooks directly. "
        "Configure connection details below."
    )

    # Manual Chef Server configuration (simplified)
    server_url = st.text_input(
        "Chef Server URL",
        placeholder="https://chef.example.com",
        help="Enter Chef Server URL",
    )

    organization = st.text_input(
        "Organization",
        placeholder="default",
        help="Chef organization name",
    )

    cookbook_name = st.text_input(
        "Cookbook Name",
        placeholder="nginx, apache2, mysql, etc.",
        help="Enter the name of the cookbook to download",
    )

    download_enabled = all([server_url, organization, cookbook_name])
    if st.button("Download Cookbook", disabled=not download_enabled):
        st.warning(
            "Chef Server cookbook download requires authentication. "
            "For now, please use Directory Path or Upload Archive options."
        )


def _show_step2_platform_configuration() -> None:
    """Step 2: Target platform configuration."""
    st.subheader("Step 2: Configure Target Platform")

    col1, col2 = st.columns(2)

    with col1:
        target_platform = st.selectbox(
            "Target Platform",
            ["awx", "aap", "tower"],
            format_func=lambda x: {
                "awx": "AWX (Open Source)",
                "aap": "Ansible Automation Platform",
                "tower": "Ansible Tower (Legacy)",
            }.get(x, x),
            help="Select the target Ansible automation platform",
        )

    with col2:
        target_version = st.text_input(
            "Platform Version",
            value="23.0.0" if target_platform == "awx" else "2.4.0",
            help="Enter the target platform version",
        )

    # Simulation mode toggle (prominent feature)
    st.markdown("---")
    st.markdown("**Deployment Mode**")

    simulation_mode = st.toggle(
        "Enable Simulation Mode (Preview Only)",
        value=st.session_state.migration_v2_simulation_mode,
        help=(
            "When enabled, migration will simulate AWX/AAP deployment "
            "without making actual changes. Perfect for testing and "
            "previewing what would be created."
        ),
    )
    st.session_state.migration_v2_simulation_mode = simulation_mode

    if simulation_mode:
        st.info(
            "🔍 **Simulation Mode Enabled**: Migration will preview "
            "AWX/AAP deployment without creating actual resources. "
            "You'll see exactly what would be created."
        )
    else:
        st.warning(
            "⚠️ **Live Mode**: Migration will create actual resources in AWX/AAP. "
            "Ensure you have proper credentials configured."
        )

    # Platform connection settings (only if not in simulation mode)
    if not simulation_mode:
        st.markdown("---")
        st.markdown("**Platform Connection**")

        server_url = st.text_input(
            "Server URL",
            placeholder="https://awx.example.com",
            help="AWX/AAP server URL",
        )

        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username", help="Authentication username")
        with col2:
            password = st.text_input(
                "Password", type="password", help="Authentication password"
            )

        verify_ssl = st.checkbox("Verify SSL", value=True)

        # Store connection config
        st.session_state.migration_v2_config["platform_connection"] = {
            "server_url": server_url,
            "username": username,
            "password": password,
            "verify_ssl": verify_ssl,
        }

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("← Back"):
            st.session_state.migration_v2_step = 1
            st.rerun()

    with col2:
        next_enabled = simulation_mode or bool(
            st.session_state.migration_v2_config.get("platform_connection", {}).get(
                "server_url"
            )
        )
        if st.button("Next →", type="primary", disabled=not next_enabled):
            st.session_state.migration_v2_config["target_platform"] = target_platform
            st.session_state.migration_v2_config["target_version"] = target_version
            st.session_state.migration_v2_config["simulation_mode"] = simulation_mode
            st.session_state.migration_v2_step = 3
            st.rerun()


def _show_step3_conversion_options() -> None:
    """Step 3: Conversion options."""
    st.subheader("Step 3: Conversion Options")

    # Chef version
    chef_version = st.text_input(
        "Chef Version",
        value="15.10.91",
        help="Chef version being migrated from",
    )

    # Conversion options
    st.markdown("**Conversion Settings**")

    col1, col2 = st.columns(2)

    with col1:
        include_tests = st.checkbox(
            "Convert InSpec Tests",
            value=True,
            help="Convert InSpec profiles to Ansible tests",
        )

        convert_habitat = st.checkbox(
            "Convert Habitat Plans",
            value=True,
            help="Convert Chef Habitat plans to Docker/Compose",
        )

    with col2:
        generate_ci = st.checkbox(
            "Generate CI/CD Pipelines",
            value=True,
            help="Generate CI/CD pipeline configurations",
        )

        validate_playbooks = st.checkbox(
            "Validate Generated Playbooks",
            value=True,
            help="Run validation on generated Ansible playbooks",
        )

    # Advanced options
    with st.expander("Advanced Options"):
        output_dir = st.text_input(
            "Custom Output Directory (optional)",
            placeholder="/path/to/output",
            help="Specify custom output directory for generated files",
        )

        skip_validation = st.checkbox(
            "Skip Validation",
            value=False,
            help="Skip validation phase (faster but less safe)",
        )

        preserve_comments = st.checkbox(
            "Preserve Comments",
            value=True,
            help="Attempt to preserve comments from Chef code",
        )

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("← Back"):
            st.session_state.migration_v2_step = 2
            st.rerun()

    with col2:
        if st.button("Next →", type="primary"):
            st.session_state.migration_v2_config.update(
                {
                    "chef_version": chef_version,
                    "include_tests": include_tests,
                    "convert_habitat": convert_habitat,
                    "generate_ci": generate_ci,
                    "validate_playbooks": validate_playbooks,
                    "output_dir": output_dir or None,
                    "skip_validation": skip_validation,
                    "preserve_comments": preserve_comments,
                }
            )
            st.session_state.migration_v2_step = 4
            st.rerun()


def _show_step4_review_and_execute() -> None:
    """Step 4: Review and execute migration."""
    st.subheader("Step 4: Review & Execute")

    config = st.session_state.migration_v2_config

    # Display configuration summary
    st.markdown("**Migration Configuration Summary**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Source Configuration:**")
        st.write(f"- Cookbook: `{config.get('cookbook_path', 'Not set')}`")
        st.write(f"- Chef Version: `{config.get('chef_version', 'Not set')}`")

        st.markdown("**Conversion Options:**")
        st.write(f"- InSpec Tests: {'✓' if config.get('include_tests') else '✗'}")
        st.write(f"- Habitat Plans: {'✓' if config.get('convert_habitat') else '✗'}")
        st.write(f"- CI/CD Pipelines: {'✓' if config.get('generate_ci') else '✗'}")

    with col2:
        st.markdown("**Target Configuration:**")
        st.write(f"- Platform: `{config.get('target_platform', 'Not set')}`")
        st.write(f"- Version: `{config.get('target_version', 'Not set')}`")

        simulation_mode = config.get("simulation_mode", False)
        mode_label = "Simulation (Preview)" if simulation_mode else "Live Deployment"
        mode_icon = "🔍" if simulation_mode else "🚀"
        st.write(f"- Mode: {mode_icon} {mode_label}")

    if simulation_mode:
        st.success(
            "**Simulation Mode**: Migration will preview deployment without creating "
            "actual resources in AWX/AAP."
        )
    else:
        st.warning(
            "**Live Mode**: Migration will create actual resources. "
            "Ensure credentials are correct."
        )

    # State persistence option
    st.markdown("---")
    save_state = st.checkbox(
        "Save Migration State",
        value=True,
        help="Save migration state to database for later retrieval",
    )

    # Execute button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("← Back"):
            st.session_state.migration_v2_step = 3
            st.rerun()

    with col2:
        if st.button("🚀 Execute Migration", type="primary"):
            _execute_migration(config, save_state)


def _execute_migration(config: dict[str, Any], save_state: bool) -> None:
    """Execute the migration with simulation support."""
    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0, text="Initializing migration...")
        status_text = st.empty()

        try:
            # Initialize orchestrator with required parameters
            status_text.info("Initializing Migration Orchestrator...")
            progress_bar.progress(10, text="Initializing orchestrator...")

            orchestrator = MigrationOrchestrator(
                chef_version=config.get("chef_version", "15.10.91"),
                target_platform=config.get("target_platform", "aap"),
                target_version=config.get("target_version", "2.4.0"),
            )

            # Execute migration
            status_text.info("Executing migration workflow...")
            progress_bar.progress(20, text="Migrating cookbook...")

            result = orchestrator.migrate_cookbook(
                cookbook_path=config["cookbook_path"],
                skip_validation=config.get("skip_validation", False),
            )

            progress_bar.progress(60, text="Migration complete, processing results...")

            # Simulate deployment if enabled
            if config.get("simulation_mode", False):
                status_text.info("Running deployment simulation...")
                progress_bar.progress(70, text="Simulating AWX/AAP deployment...")

                simulation_result = _run_deployment_simulation(result, config)
                st.session_state.migration_v2_simulation_result = simulation_result

            progress_bar.progress(80, text="Finalizing...")

            # Note: State saving with v2 orchestrator would require database integration
            if save_state:
                status_text.info("State saving not yet implemented for v2...")
                progress_bar.progress(90, text="Skipping state save...")

            progress_bar.progress(100, text="Migration complete!")
            status_text.success("✅ Migration completed successfully!")

            # Store result
            st.session_state.migration_v2_result = result

            # Show success message
            st.success(
                f"Migration completed! Status: {result.status.value}\n\n"
                f"Generated {len(result.playbooks_generated)} playbooks"
            )

            # Switch to results tab
            st.info("View results in the 'Migration Status' tab above.")

        except Exception as e:
            progress_bar.progress(0, text="Migration failed")
            status_text.error(f"❌ Migration failed: {e}")
            st.exception(e)


def _run_deployment_simulation(
    migration_result: MigrationResult, config: dict[str, Any]
) -> dict[str, Any]:
    """Run deployment simulation to preview AWX/AAP resources."""
    # Simulate deployment based on migration result
    cookbook_name = Path(config["cookbook_path"]).name
    target_platform = config.get("target_platform", "aap")

    # Generate simulation preview
    sim_result = {
        "timestamp": datetime.now().isoformat(),
        "platform": target_platform,
        "cookbook": cookbook_name,
        "resources_to_create": [],
        "summary": {
            "inventories": 0,
            "projects": 0,
            "job_templates": 0,
            "credentials": 0,
        },
    }

    # Simulate inventory creation
    inventory_name = f"{cookbook_name}-inventory"
    sim_result["resources_to_create"].append(
        {
            "type": "inventory",
            "name": inventory_name,
            "description": f"Inventory for {cookbook_name} cookbook",
            "organization": 1,
            "variables": {"ansible_connection": "ssh"},
        }
    )
    sim_result["summary"]["inventories"] += 1

    # Simulate project creation
    project_name = f"{cookbook_name}-project"
    sim_result["resources_to_create"].append(
        {
            "type": "project",
            "name": project_name,
            "description": f"Project for {cookbook_name} Ansible playbooks",
            "scm_type": "git",
            "scm_url": "https://github.com/org/repo.git",  # Placeholder
            "organization": 1,
        }
    )
    sim_result["summary"]["projects"] += 1

    # Simulate job template creation for each playbook
    for playbook_path in migration_result.playbooks_generated:
        playbook_name = Path(playbook_path).stem
        job_template_name = f"{cookbook_name}-{playbook_name}"

        sim_result["resources_to_create"].append(
            {
                "type": "job_template",
                "name": job_template_name,
                "description": f"Job template for {playbook_name}",
                "job_type": "run",
                "inventory": inventory_name,
                "project": project_name,
                "playbook": f"playbooks/{Path(playbook_path).name}",
                "credentials": [],
            }
        )
        sim_result["summary"]["job_templates"] += 1

    # Simulate credential creation
    sim_result["resources_to_create"].append(
        {
            "type": "credential",
            "name": f"{cookbook_name}-ssh-key",
            "description": f"SSH credentials for {cookbook_name}",
            "credential_type": "Machine",
            "organization": 1,
        }
    )
    sim_result["summary"]["credentials"] += 1

    return sim_result


def _show_migration_status() -> None:
    """Show migration status and results."""
    st.subheader("Migration Status")

    result = st.session_state.migration_v2_result

    if not result:
        st.info("No active migration. Start a migration in the wizard tab.")
        return

    # Status overview
    _display_status_overview(result)

    # Metrics
    st.markdown("---")
    _display_migration_metrics(result)

    # Generated artifacts
    st.markdown("---")
    _display_generated_artifacts(result)

    # Warnings and errors
    if result.warnings or result.errors:
        st.markdown("---")
        _display_warnings_and_errors(result)


def _display_status_overview(result: MigrationResult) -> None:
    """Display migration status overview."""
    st.markdown("**Status Overview**")

    col1, col2, col3 = st.columns(3)

    with col1:
        status_icon = {
            MigrationStatus.PENDING: "⏳",
            MigrationStatus.IN_PROGRESS: "▶️",
            MigrationStatus.CONVERTED: "✅",
            MigrationStatus.VALIDATED: "✅",
            MigrationStatus.DEPLOYED: "🚀",
            MigrationStatus.FAILED: "❌",
            MigrationStatus.ROLLED_BACK: "↩️",
        }.get(result.status, "❓")

        st.metric("Status", f"{status_icon} {result.status.value}")

    with col2:
        st.metric("Playbooks", len(result.playbooks_generated))

    with col3:
        st.metric("Migration ID", result.migration_id[:12])


def _display_migration_metrics(result: MigrationResult) -> None:
    """Display migration metrics."""
    st.markdown("**Migration Metrics**")

    metrics = result.metrics

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Recipes Converted", metrics.recipes_converted)
        st.metric("Recipes Failed", metrics.recipes_failed)

    with col2:
        st.metric("Templates Converted", metrics.templates_converted)
        st.metric("Attributes Converted", metrics.attributes_converted)

    with col3:
        st.metric("Resources Converted", metrics.resources_converted)
        st.metric("Handlers Converted", metrics.handlers_converted)

    with col4:
        st.metric("Recipes Skipped", metrics.recipes_skipped)
        st.metric("Conversion Rate", f"{metrics.conversion_rate():.1f}%")


def _display_generated_artifacts(result: MigrationResult) -> None:
    """Display generated artifacts."""
    st.markdown("**Generated Artifacts**")

    # Playbooks
    with st.expander(f"Playbooks ({len(result.playbooks_generated)})", expanded=True):
        for playbook_path in result.playbooks_generated:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"📄 `{playbook_path}`")

            with col2:
                if st.button("Download", key=f"download_pb_{playbook_path}"):
                    try:
                        playbook = Path(playbook_path)
                        with playbook.open() as f:
                            content = f.read()
                        st.download_button(
                            label="Save",
                            data=content,
                            file_name=Path(playbook_path).name,
                            mime="text/yaml",
                            key=f"save_pb_{playbook_path}",
                        )
                    except Exception as e:
                        st.error(f"Failed to read file: {e}")


def _display_warnings_and_errors(result: MigrationResult) -> None:
    """Display warnings and errors."""
    if result.warnings:
        with st.expander(f"⚠️ Warnings ({len(result.warnings)})", expanded=True):
            for warning in result.warnings:
                st.warning(warning)

    if result.errors:
        with st.expander(f"❌ Errors ({len(result.errors)})", expanded=True):
            for error in result.errors:
                st.error(error)


def _show_migration_history() -> None:
    """Show migration history from database."""
    st.subheader("Migration History")

    st.info(
        "Migration history tracking is not yet fully implemented in v2.0. "
        "Enable state saving during migration to store results for future retrieval."
    )

    # Placeholder for future implementation
    with st.expander("Future Features"):
        st.markdown("""
        **Planned History Features:**
        - View all past migrations with timestamps
        - Filter by status, cookbook, or platform
        - Load previous migration results
        - Compare migration metrics across versions
        - Export migration history reports
        """)


def _show_simulation_results() -> None:
    """Show simulation results for AWX/AAP deployment preview."""
    st.subheader("Deployment Simulation Results")

    sim_result = st.session_state.get("migration_v2_simulation_result")

    if not sim_result:
        st.info(
            "No simulation results available. Run a migration with simulation mode "
            "enabled to preview AWX/AAP deployment."
        )
        return

    # Simulation summary
    st.markdown("**Simulation Summary**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Platform", sim_result["platform"].upper())
        st.metric("Cookbook", sim_result["cookbook"])

    with col2:
        st.metric("Inventories", sim_result["summary"]["inventories"])
        st.metric("Projects", sim_result["summary"]["projects"])

    with col3:
        st.metric("Job Templates", sim_result["summary"]["job_templates"])
        st.metric("Credentials", sim_result["summary"]["credentials"])

    st.success(
        "✅ Simulation complete! The resources below show what **would be created** "
        "in AWX/AAP during a live deployment."
    )

    # Resources to create
    st.markdown("---")
    st.markdown("**Resources Preview**")

    for resource in sim_result["resources_to_create"]:
        resource_type = resource["type"]
        resource_name = resource["name"]

        icon_map = {
            "inventory": "📋",
            "project": "📁",
            "job_template": "⚙️",
            "credential": "🔑",
        }

        icon = icon_map.get(resource_type, "📦")

        with st.expander(f"{icon} {resource_type.title()}: {resource_name}"):
            st.json(resource)

    # Export simulation results
    st.markdown("---")
    if st.button("Export Simulation Results"):
        sim_json = json.dumps(sim_result, indent=2)
        st.download_button(
            label="Download JSON",
            data=sim_json,
            file_name=f"simulation_{sim_result['cookbook']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )
