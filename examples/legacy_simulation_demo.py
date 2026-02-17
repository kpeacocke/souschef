"""
Demonstration: Legacy Migration Simulation

Shows a Chef 12.19.36 → Tower 3.8.5 migration simulation - legacy virtualenv model.
Compare this with the AAP 2.4 demo to see the functional differences.
"""

import json

from souschef.migration_simulation import create_simulation_config


def demo_legacy_simulation():
    """Run legacy migration simulation demonstration."""

    print("\n" + "=" * 80)
    print("LEGACY MIGRATION SIMULATION DEMO: Chef 12.19.36 → Tower 3.8.5")
    print("=" * 80)

    config = create_simulation_config(
        chef_version="12.19.36",
        target_platform="tower",
        target_version="3.8.5",
        chef_auth_protocol="1.0",  # SHA-1 for legacy
        inventory_id=1,
        project_id=2,
    )

    print("\n[Configuration]")
    print(f"  Source: Chef {config.chef_version}")
    print(f"    • Auth Protocol: {config.chef_auth_protocol} (SHA-1)")
    print("    • Hash Algorithm: SHA1")
    print(f"  Target: Tower {config.target_version}")
    print(f"    • Execution Model: {config.execution_model}")
    print(f"    • Ansible Version: {config.ansible_version}")
    print(f"    • Available Endpoints: {len(config.available_endpoints)}")

    # Show job template structure - virtualenv model
    jt = config.get_job_template_structure()
    print("\n[Job Template Structure]")
    print("  Execution Model: VIRTUALENV (NOT execution_environment)")
    print(f"  Custom Virtualenv: {jt.get('custom_virtualenv', 'Not set')}")
    print(json.dumps(jt, indent=2))

    print("\n[Key Differences from AAP 2.4]")
    print("  ✗ No execution environments (virtualenv only)")
    print("  ✗ No content signing")
    print("  ✗ No FIPS compliance")
    print("  ✗ No mesh capabilities")
    print("  ✓ Simpler authentication (SHA-1 or SHA-256)")
    print(f"  ✓ Fewer API endpoints: {len(config.available_endpoints)}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    demo_legacy_simulation()
