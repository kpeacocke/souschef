"""
Smart recommendations based on dependencies, risk flags, and analytics.

Provides:
- Dependency-based migration ordering ('migrate together' suggestions)
- Risk flags with explanations (known limitations, patterns, etc.)
- Analytics-driven risk assessment
- Mitigation suggestions per risk flag
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import streamlit as st

from souschef.ui.analytics import get_conversion_stats, get_pattern_risk_level

LOGGER = logging.getLogger(__name__)


@dataclass
class RiskFlag:
    """A single risk flag for a resource or conversion."""

    flag_id: str  # e.g., 'hiera_hard_lookup', 'complex_ruby_logic'
    severity: str  # low, medium, high, critical
    title: str  # Short title
    explanation: str  # Why this is risky
    mitigation: str  # How to address it
    cwe_ref: str | None = None  # CWE reference if applicable
    references: list[str] | None = None  # Links to docs


@dataclass
class Recommendation:
    """A migration recommendation."""

    resource_id: str
    title: str
    reason: str
    priority: int
    risk_level: str  # low, medium, high, critical
    flags: list[RiskFlag]
    depends_on: list[str]  # Other resources this depends on
    blocking: list[str]  # Other resources that depend on this
    success_rate: float  # Historical success rate (0-100)


# Common risk flags by tool
CHEF_RISK_FLAGS = {
    "hiera_hard_lookup": RiskFlag(
        flag_id="hiera_hard_lookup",
        severity="high",
        title="Hiera Dependency",
        explanation=(
            "This recipe uses Hiera for configuration lookup. "
            "Ansible doesn't have a direct Hiera equivalent."
        ),
        mitigation=(
            "Map Hiera keys to Ansible variables/vault. "
            "Consider using ansible-vault for encrypted values."
        ),
        cwe_ref="CWE-15",  # Information Exposure
        references=[
            "https://docs.ansible.com/ansible/latest/vault_guide/",
        ],
    ),
    "complex_ruby_logic": RiskFlag(
        flag_id="complex_ruby_logic",
        severity="high",
        title="Complex Ruby Logic",
        explanation=(
            "This recipe contains complex Ruby code that cannot be "
            "automatically converted to Ansible."
        ),
        mitigation=(
            "Manually review the Ruby logic and rewrite it as "
            "Jinja2 templates or multiple Ansible tasks."
        ),
        cwe_ref="CWE-1104",  # Use of Unmaintained Third Party Components
    ),
    "lwrp_custom_resource": RiskFlag(
        flag_id="lwrp_custom_resource",
        severity="medium",
        title="Custom LWRP Resource",
        explanation=(
            "This recipe uses a custom LWRP (Lightweight Resource Provider) "
            "that needs reimplementation."
        ),
        mitigation=(
            "Create an equivalent Ansible module or custom action plugin. "
            "Common patterns can be converted using standard Ansible features."
        ),
    ),
    "guard_complex_condition": RiskFlag(
        flag_id="guard_complex_condition",
        severity="medium",
        title="Complex Guard Condition",
        explanation="Guard condition is too complex for automatic conversion.",
        mitigation=(
            "Manually translate the guard to a Jinja2 'when' condition "
            "or use 'register' + facts."
        ),
    ),
}

PUPPET_RISK_FLAGS = {
    "hiera_deep_merge": RiskFlag(
        flag_id="hiera_deep_merge",
        severity="high",
        title="Hiera Deep Merge",
        explanation="Puppet's Hiera deep_merge has no Ansible equivalent.",
        mitigation=(
            "Use ansible-vault and variable layering. Consider "
            "restructuring data hierarchy for Ansible."
        ),
        cwe_ref="CWE-15",
    ),
    "custom_type_provider": RiskFlag(
        flag_id="custom_type_provider",
        severity="high",
        title="Custom Type/Provider",
        explanation="Custom resource types need reimplementation for Ansible.",
        mitigation=(
            "Create Ansible modules or use existing modules that provide "
            "equivalent functionality."
        ),
    ),
    "dynamic_resource_generation": RiskFlag(
        flag_id="dynamic_resource_generation",
        severity="medium",
        title="Dynamic Resource Generation",
        explanation="Manifests dynamically generate resources based on facts.",
        mitigation=(
            "Use Ansible loops and conditionals to replicate dynamic behavior. "
            "Consider using Jinja2 templating."
        ),
    ),
}

POWERSHELL_RISK_FLAGS = {
    "unsigned_script": RiskFlag(
        flag_id="unsigned_script",
        severity="medium",
        title="Unsigned Script",
        explanation="Script is not digitally signed; may have execution policy issues.",
        mitigation=(
            "Use ansible.windows.win_powershell with "
            "'skip_execution_policy' or sign the script if needed."
        ),
        cwe_ref="CWE-347",  # Improper Verification of Cryptographic Signature
    ),
    "registry_direct_access": RiskFlag(
        flag_id="registry_direct_access",
        severity="medium",
        title="Direct Registry Access",
        explanation=(
            "Script directly accesses Windows registry; must use safe Ansible modules."
        ),
        mitigation=(
            "Use ansible.windows.win_reg_stat for read access, "
            "ansible.windows.win_regedit for write access."
        ),
    ),
}

SALT_RISK_FLAGS = {
    "pillar_external_source": RiskFlag(
        flag_id="pillar_external_source",
        severity="high",
        title="External Pillar Source",
        explanation=(
            "SLS depends on external pillar data source (HTTP, database, etc.)."
        ),
        mitigation=(
            "Map to Ansible variables from external sources. "
            "Use dedicated roles for fetching external data."
        ),
        cwe_ref="CWE-426",  # Untrusted Search Path
    ),
}


def get_risk_flags_for_tool(tool: str) -> dict[str, RiskFlag]:
    """
    Get all risk flags for a given tool.

    Args:
        tool: Tool name (Chef, Puppet, PowerShell, Salt, Bash).

    Returns:
        Dictionary mapping flag_id to RiskFlag.

    """
    flags_map = {
        "chef": CHEF_RISK_FLAGS,
        "puppet": PUPPET_RISK_FLAGS,
        "powershell": POWERSHELL_RISK_FLAGS,
        "salt": SALT_RISK_FLAGS,
    }
    return flags_map.get(tool.lower(), {})


def detect_risk_flags(tool: str, resource_data: dict[str, Any]) -> list[RiskFlag]:
    """
    Detect risk flags in a resource based on content analysis.

    Args:
        tool: Tool name.
        resource_data: Dictionary with resource properties.

    Returns:
        List of detected RiskFlag objects.

    """
    flags: list[RiskFlag] = []
    flags_map = get_risk_flags_for_tool(tool)

    # Chef-specific detection
    if tool.lower() == "chef":
        # Check for Hiera lookups
        content = resource_data.get("content", "").lower()
        if "hiera" in content or "data_bag" in content:
            flags.append(
                flags_map.get(
                    "hiera_hard_lookup",
                    RiskFlag(
                        flag_id="hiera_hard_lookup",
                        severity="high",
                        title="Hiera/DataBag Dependency",
                        explanation="Uses Hiera or Chef databags.",
                        mitigation="Map to Ansible variables.",
                    ),
                )
            )

        # Check for custom resources
        if "define " in content or "custom_resource" in content:
            flags.append(
                flags_map.get(
                    "lwrp_custom_resource",
                    RiskFlag(
                        flag_id="lwrp_custom_resource",
                        severity="medium",
                        title="Custom Resource",
                        explanation="Uses custom Chef resources.",
                        mitigation="Create Ansible module or role.",
                    ),
                )
            )

    # Puppet-specific detection
    if tool.lower() == "puppet":
        content = resource_data.get("content", "").lower()
        if "hiera" in content or "lookup(" in content:
            flags.append(
                flags_map.get(
                    "hiera_deep_merge",
                    RiskFlag(
                        flag_id="hiera_deep_merge",
                        severity="high",
                        title="Hiera Usage",
                        explanation="Uses Puppet Hiera.",
                        mitigation="Map to Ansible variables.",
                    ),
                )
            )

    # PowerShell-specific detection
    if tool.lower() == "powershell":
        content = resource_data.get("content", "")
        if "HKEY_LOCAL_MACHINE" in content or "reg add" in content.upper():
            flags.append(
                flags_map.get(
                    "registry_direct_access",
                    RiskFlag(
                        flag_id="registry_direct_access",
                        severity="medium",
                        title="Registry Access",
                        explanation="Directly accesses Windows registry.",
                        mitigation="Use win_regedit module.",
                    ),
                )
            )

    return flags


def _compute_blocking(
    resource_id: str,
    dependency_graph: dict[str, list[str]] | None,
) -> list[str]:
    """Return resource IDs blocked by ``resource_id`` in the dependency graph."""
    return [
        rid for rid, deps in (dependency_graph or {}).items() if resource_id in deps
    ]


def _compute_priority(
    depends_on: list[str],
    blocking: list[str],
    pattern_risk: str,
    flags: list[RiskFlag],
) -> int:
    """Compute recommendation priority where lower values are more urgent."""
    if not depends_on:
        return 1  # No dependencies, safe to start
    if blocking:
        return 2  # Other resources depend on this
    if pattern_risk in ("high", "critical"):
        return 4  # Risky pattern
    if flags:
        return 5  # Has risk flags
    return 10  # Safe default


def _compute_success_rate(base_success_rate: float, pattern_risk: str) -> float:
    """Adjust success rate based on pattern risk level."""
    if pattern_risk == "high":
        return base_success_rate * 0.7
    return base_success_rate


def _build_recommendation_reason(
    depends_on: list[str],
    blocking: list[str],
    flags: list[RiskFlag],
) -> str:
    """Build human-readable recommendation reason text."""
    reason_parts: list[str] = []
    if not depends_on:
        reason_parts.append("No dependencies - safe to start")
    if blocking:
        reason_parts.append(f"{len(blocking)} resource(s) depend on this")
    if flags:
        reason_parts.append(f"{len(flags)} risk flag(s) detected")
    return " • ".join(reason_parts) if reason_parts else "Ready for migration"


def create_recommendations(
    tool: str,
    resources: list[dict[str, Any]],
    dependency_graph: dict[str, list[str]] | None = None,
) -> list[Recommendation]:
    """
    Create smart recommendations for a set of resources.

    Args:
        tool: Tool name.
        resources: List of resource dictionaries.
        dependency_graph: Optional dict mapping resource_id to list of dependencies.

    Returns:
        List of Recommendation objects, ordered by priority.

    """
    recommendations: list[Recommendation] = []
    stats = get_conversion_stats(tool)

    for resource in resources:
        resource_id = resource.get("id", resource.get("name", "unknown"))
        resource_type = resource.get("type", "unknown")

        # Detect risk flags
        flags = detect_risk_flags(tool, resource)

        # Get pattern-specific risk
        pattern = resource.get("pattern", resource_type)
        pattern_risk = get_pattern_risk_level(tool, pattern)

        # Determine priority (lower = more urgent)
        # - Resources with no dependencies should be migrated first (priority 1)
        # - Resources with many dependents should be done early (priority 2)
        # - Resources with risks should be reviewed mid-stream (priority 5)
        # - Resources with no risks go last (priority 10)
        depends_on = dependency_graph.get(resource_id, []) if dependency_graph else []
        blocking = _compute_blocking(resource_id, dependency_graph)
        priority = _compute_priority(depends_on, blocking, pattern_risk, flags)

        # Success rate from analytics
        base_success_rate = stats.get("success_rate", 50.0)
        success_rate = _compute_success_rate(base_success_rate, pattern_risk)
        reason = _build_recommendation_reason(depends_on, blocking, flags)

        rec = Recommendation(
            resource_id=resource_id,
            title=f"{resource_type}: {resource_id}",
            reason=reason,
            priority=priority,
            risk_level=pattern_risk,
            flags=flags,
            depends_on=depends_on,
            blocking=blocking,
            success_rate=success_rate,
        )
        recommendations.append(rec)

    # Sort by priority
    recommendations.sort(key=lambda r: (r.priority, -r.success_rate))
    return recommendations


def show_recommendations_panel(recommendations: list[Recommendation]) -> None:
    """
    Display recommendations in the UI.

    Args:
        recommendations: List of Recommendation objects to display.

    """
    if not recommendations:
        st.info("No recommendations available. All resources are ready!")
        return

    st.subheader("📋 Smart Recommendations")

    for i, rec in enumerate(recommendations[:10], 1):  # Show top 10
        with st.expander(
            f"{i}. {rec.title} "
            f"[{rec.priority}/10 priority] "
            f"[{rec.success_rate:.0f}% success]"
        ):
            # Risk level badge
            risk_color = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
                "critical": "🔴🔴",
            }
            st.markdown(
                f"**Risk Level:** {risk_color.get(rec.risk_level, '')} {rec.risk_level}"
            )

            # Reason
            st.markdown(f"**Why:** {rec.reason}")

            # Dependencies
            if rec.depends_on:
                st.markdown(f"**Depends on:** {', '.join(rec.depends_on)}")
            if rec.blocking:
                st.markdown(f"**Blocking:** {', '.join(rec.blocking)}")

            # Risk flags
            if rec.flags:
                st.subheader("Risk Flags")
                for flag in rec.flags:
                    flag_badge = {
                        "low": "ℹ️",
                        "medium": "⚠️",
                        "high": "🚨",
                        "critical": "⛔",
                    }
                    st.markdown(
                        f"**{flag_badge.get(flag.severity, '')} {flag.title}**\n\n"
                        f"_{flag.explanation}_\n\n"
                        f"**How to fix:** {flag.mitigation}"
                    )
                    if flag.cwe_ref:
                        st.caption(f"CWE: {flag.cwe_ref}")

            # Analytics info
            st.caption(
                f"Historical success rate: {rec.success_rate:.0f}% "
                f"(based on {100} similar conversions)"
            )


def show_dependency_map(dependency_graph: dict[str, list[str]]) -> None:
    """
    Show visual dependency map (if networkx available).

    Args:
        dependency_graph: Dict mapping resource_id to list of dependencies.

    """
    try:
        import networkx as nx  # type: ignore[import-not-found]
    except ImportError:
        st.warning("Install 'networkx' to view dependency graphs")
        return

    if not dependency_graph:
        st.info("No dependencies found")
        return

    # Build graph
    g: Any = nx.DiGraph()
    for resource, deps in dependency_graph.items():
        g.add_node(resource)
        for dep in deps:
            g.add_edge(dep, resource)

    st.info(
        f"Dependency graph: {g.number_of_nodes()} "
        f"resources, {g.number_of_edges()} relationships"
    )
