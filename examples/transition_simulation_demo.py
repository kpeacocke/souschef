"""
Demonstration: Transition Migration Simulation

Shows a Chef 14.15.6 → AWX 22.0.0 migration simulation - the transition period
where both virtualenv and execution environments were supported.
"""

import json

from souschef.migration_simulation import create_simulation_config


def demo_transition_simulation():
    """Run transition period migration simulation."""

    print("\n" + "=" * 80)
    print("TRANSITION MIGRATION SIMULATION DEMO: Chef 14.15.6 → AWX 22.0.0")
    print("=" * 80)

    config = create_simulation_config(
        chef_version="14.15.6",
        target_platform="awx",
        target_version="22.0.0",
        inventory_id=1,
        project_id=2,
        execution_environment_id=15,
    )

    print("\n[Configuration]")
    print(f"  Source: Chef {config.chef_version}")
    print(f"    • Auth Protocol: {config.chef_auth_protocol} (SHA-256)")
    print("    • Hash Algorithm: SHA256")
    print(f"  Target: AWX {config.target_version}")
    print(f"    • Execution Model: {config.execution_model}")
    print(f"    • Ansible Version: {config.ansible_version}")
    print(f"    • Available Endpoints: {len(config.available_endpoints)}")

    jt = config.get_job_template_structure()
    print("\n[Job Template Structure]")
    print("  Execution Model: EXECUTION_ENVIRONMENT (preferred)")
    print(f"  Has execution_environment: {jt.get('execution_environment') is not None}")
    print(f"  Value: {jt.get('execution_environment')}")
    print(json.dumps(jt, indent=2))

    print("\n[Version Comparison]")
    print(f"""
╔════════════════════╦════════════════════╦════════════════════╗
║ Feature            ║ Tower 3.8 (Legacy) ║ AWX 22 (Modern)    ║
╠════════════════════╬════════════════════╬════════════════════╣
║ Execution Model    ║ virtualenv only    ║ EE (preferred)     ║
║ Auth Protocol      ║ SHA-1/SHA-256      ║ SHA-256 preferred  ║
║ EE Support         ║ No                 ║ Yes                ║
║ Virtualenv Support ║ Yes (required)     ║ Yes (legacy)       ║
║ Content Signing    ║ No                 ║ No                 ║
║ FIPS              ║ No                 ║ No                 ║
║ API Endpoints      ║ 6                  ║ {len(config.available_endpoints)}                  ║
║ Ansible Min        ║ 2.9.0              ║ {config.ansible_version}              ║
╚════════════════════╩════════════════════╩════════════════════╝
""")

    print("[Endpoints Available in AWX 22.0.0]")
    for i, endpoint in enumerate(config.available_endpoints, 1):
        marker = " ← NEW" if "execution" in endpoint else ""
        print(f"  {i:2}. {endpoint}{marker}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    demo_transition_simulation()
