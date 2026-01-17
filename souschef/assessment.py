"""
Assessment and migration planning module for Chef to Ansible migrations.

This module provides tools for analyzing Chef cookbook migration complexity,
generating migration plans, analyzing dependencies, and validating conversions.
"""

import json
import re
from pathlib import Path
from typing import Any

from souschef.core import METADATA_FILENAME, _normalize_path, _safe_join
from souschef.core.errors import format_error_with_context
from souschef.core.validation import (
    ValidationEngine,
    ValidationLevel,
    ValidationResult,
)


def assess_chef_migration_complexity(
    cookbook_paths: str,
    migration_scope: str = "full",
    target_platform: str = "ansible_awx",
) -> str:
    """
    Assess the complexity of migrating Chef cookbooks to Ansible with detailed analysis.

    Args:
        cookbook_paths: Comma-separated paths to Chef cookbooks or cookbook directory
        migration_scope: Scope of migration (full, recipes_only, infrastructure_only)
        target_platform: Target platform (ansible_awx, ansible_core, ansible_tower)

    Returns:
        Comprehensive migration complexity assessment with recommendations

    """
    try:
        # Validate and parse inputs
        error_msg = _validate_assessment_inputs(
            cookbook_paths, migration_scope, target_platform
        )
        if error_msg:
            return error_msg

        # Process cookbook analysis
        return _process_cookbook_assessment(
            cookbook_paths, migration_scope, target_platform
        )

    except Exception as e:
        return format_error_with_context(
            e, "assessing Chef migration complexity", cookbook_paths
        )


def _process_cookbook_assessment(
    cookbook_paths: str, migration_scope: str, target_platform: str
) -> str:
    """Process the cookbook assessment workflow."""
    # Parse cookbook paths (may be empty if none exist)
    valid_paths = _parse_cookbook_paths(cookbook_paths)

    # Analyze all cookbooks (handles empty list gracefully)
    cookbook_assessments, overall_metrics = _analyse_cookbook_metrics(valid_paths)

    # Generate recommendations and reports
    recommendations = _generate_migration_recommendations_from_assessment(
        cookbook_assessments, overall_metrics, target_platform
    )
    roadmap = _create_migration_roadmap(cookbook_assessments)

    # Format final assessment report
    return _format_assessment_report(
        migration_scope,
        target_platform,
        overall_metrics,
        cookbook_assessments,
        recommendations,
        roadmap,
    )


def parse_chef_migration_assessment(
    cookbook_paths: str,
    migration_scope: str = "full",
    target_platform: str = "ansible_awx",
) -> dict[str, Any]:
    """
    Parse Chef cookbook migration assessment and return as dictionary.

    Args:
        cookbook_paths: Comma-separated paths to Chef cookbooks or cookbook directory
        migration_scope: Scope of migration (full, recipes_only, infrastructure_only)
        target_platform: Target platform (ansible_awx, ansible_core, ansible_tower)

    Returns:
        Dictionary containing assessment data with complexity, recommendations, etc.

    """
    try:
        # Validate inputs
        error_msg = _validate_assessment_inputs(
            cookbook_paths, migration_scope, target_platform
        )
        if error_msg:
            return {"error": error_msg}

        # Parse cookbook paths (may be empty if none exist)
        valid_paths = _parse_cookbook_paths(cookbook_paths)

        # Analyze all cookbooks (handles empty list gracefully)
        cookbook_assessments, overall_metrics = _analyse_cookbook_metrics(valid_paths)

        # Generate recommendations and reports
        recommendations = _generate_migration_recommendations_from_assessment(
            cookbook_assessments, overall_metrics, target_platform
        )
        roadmap = _create_migration_roadmap(cookbook_assessments)

        return {
            "migration_scope": migration_scope,
            "target_platform": target_platform,
            "overall_metrics": overall_metrics,
            "cookbook_assessments": cookbook_assessments,
            "recommendations": recommendations,
            "roadmap": roadmap,
            "complexity": _get_overall_complexity_level(overall_metrics),
            "estimated_hours": overall_metrics.get("estimated_effort_days", 0)
            * 8,  # Convert days to hours
        }

    except Exception as e:
        return {
            "error": format_error_with_context(
                e, "assessing Chef migration complexity", cookbook_paths
            )
        }


def _get_overall_complexity_level(metrics: dict[str, int]) -> str:
    """Get overall complexity level based on metrics."""
    avg_complexity = metrics.get("avg_complexity", 0)
    if avg_complexity < 30:
        return "Low"
    elif avg_complexity < 70:
        return "Medium"
    else:
        return "High"


def _validate_migration_plan_inputs(
    cookbook_paths: str, migration_strategy: str, timeline_weeks: int
) -> str | None:
    """
    Validate migration plan inputs.

    Returns:
        Error message if validation fails, None if valid.

    """
    if not cookbook_paths or not cookbook_paths.strip():
        return (
            "Error: Cookbook paths cannot be empty\n\n"
            "Suggestion: Provide comma-separated paths to Chef cookbooks"
        )

    valid_strategies = ["big_bang", "phased", "parallel"]
    if migration_strategy not in valid_strategies:
        return (
            f"Error: Invalid migration strategy '{migration_strategy}'\n\n"
            f"Suggestion: Use one of {', '.join(valid_strategies)}"
        )

    if not (1 <= timeline_weeks <= 104):  # 1 week to 2 years
        return (
            f"Error: Timeline must be between 1 and 104 weeks, got {timeline_weeks}\n\n"
            "Suggestion: Provide a realistic timeline (4-12 weeks typical)"
        )

    return None


def _parse_and_assess_cookbooks(cookbook_paths: str) -> tuple[list, str | None]:
    """
    Parse cookbook paths and assess each cookbook.

    Returns:
        Tuple of (cookbook_assessments, error_message).

    """
    paths = [_normalize_path(path.strip()) for path in cookbook_paths.split(",")]
    valid_paths = [p for p in paths if p.exists()]

    if not valid_paths:
        return (
            [],
            "Error: No valid cookbook paths found\n\n"
            "Suggestion: Ensure paths exist and point to cookbook directories",
        )

    cookbook_assessments = []
    for cookbook_path in valid_paths:
        # deepcode ignore PT: path normalized via _normalize_path
        assessment = _assess_single_cookbook(cookbook_path)
        cookbook_assessments.append(assessment)

    return cookbook_assessments, None


def _format_migration_plan_output(
    migration_plan: dict,
    migration_strategy: str,
    timeline_weeks: int,
    num_cookbooks: int,
) -> str:
    """Format migration plan as markdown output."""
    return f"""# Chef to Ansible Migration Plan
# Strategy: {migration_strategy}
# Timeline: {timeline_weeks} weeks
# Cookbooks: {num_cookbooks}

## Executive Summary:
{migration_plan["executive_summary"]}

## Migration Phases:
{migration_plan["phases"]}

## Timeline and Milestones:
{migration_plan["timeline"]}

## Team Requirements:
{migration_plan["team_requirements"]}

## Prerequisites and Dependencies:
{migration_plan["prerequisites"]}

## Testing Strategy:
{migration_plan["testing_strategy"]}

## Risk Mitigation:
{migration_plan["risk_mitigation"]}

## Success Criteria:
{migration_plan["success_criteria"]}

## Post-Migration Tasks:
{migration_plan["post_migration"]}
"""


def generate_migration_plan(
    cookbook_paths: str, migration_strategy: str = "phased", timeline_weeks: int = 12
) -> str:
    """
    Generate a detailed migration plan from Chef to Ansible with timeline and milestones.

    Args:
        cookbook_paths: Comma-separated paths to Chef cookbooks
        migration_strategy: Migration approach (big_bang, phased, parallel)
        timeline_weeks: Target timeline in weeks

    Returns:
        Detailed migration plan with phases, milestones, and deliverables

    """
    try:
        # Validate inputs
        error = _validate_migration_plan_inputs(
            cookbook_paths, migration_strategy, timeline_weeks
        )
        if error:
            return error

        # Parse and assess cookbooks
        cookbook_assessments, error = _parse_and_assess_cookbooks(cookbook_paths)
        if error:
            return error

        # Generate migration plan based on strategy
        migration_plan = _generate_detailed_migration_plan(
            cookbook_assessments, migration_strategy, timeline_weeks
        )

        return _format_migration_plan_output(
            migration_plan,
            migration_strategy,
            timeline_weeks,
            len(cookbook_assessments),
        )

    except Exception as e:
        return format_error_with_context(e, "generating migration plan", cookbook_paths)


def analyse_cookbook_dependencies(
    cookbook_path: str, dependency_depth: str = "direct"
) -> str:
    """
    Analyse cookbook dependencies and identify migration order requirements.

    Args:
        cookbook_path: Path to Chef cookbook or cookbooks directory
        dependency_depth: Analysis depth (direct, transitive, full)

    Returns:
        Dependency analysis with migration order recommendations

    """
    try:
        # Validate inputs
        valid_depths = ["direct", "transitive", "full"]
        if dependency_depth not in valid_depths:
            return (
                f"Error: Invalid dependency depth '{dependency_depth}'\n\n"
                f"Suggestion: Use one of {', '.join(valid_depths)}"
            )

        cookbook_path_obj = _normalize_path(cookbook_path)
        if not cookbook_path_obj.exists():
            return (
                f"Error: Cookbook path not found: {cookbook_path}\n\n"
                "Suggestion: Check that the path exists and points to a cookbook directory"
            )

        # Analyze dependencies
        dependency_analysis = _analyse_cookbook_dependencies_detailed(cookbook_path_obj)

        # Determine migration order
        migration_order = _determine_migration_order(dependency_analysis)

        # Identify circular dependencies
        circular_deps = _identify_circular_dependencies(dependency_analysis)

        return f"""# Cookbook Dependency Analysis
# Cookbook: {cookbook_path_obj.name}
# Analysis Depth: {dependency_depth}

## Dependency Overview:
{_format_dependency_overview(dependency_analysis)}

## Dependency Graph:
{_format_dependency_graph(dependency_analysis)}

## Migration Order Recommendations:
{_format_migration_order(migration_order)}

## Circular Dependencies:
{_format_circular_dependencies(circular_deps)}

## External Dependencies:
{_format_external_dependencies(dependency_analysis)}

## Community Cookbooks:
{_format_community_cookbooks(dependency_analysis)}

## Migration Impact Analysis:
{_analyse_dependency_migration_impact(dependency_analysis)}
"""
    except Exception as e:
        return format_error_with_context(
            e, "analyzing cookbook dependencies", cookbook_path
        )


def generate_migration_report(
    _assessment_results: str,
    report_format: str = "executive",
    include_technical_details: str = "yes",
) -> str:
    """
    Generate comprehensive migration report from assessment results.

    Args:
        _assessment_results: JSON string or summary of assessment results (reserved for future use)
        report_format: Report format (executive, technical, combined)
        include_technical_details: Include detailed technical analysis (yes/no)

    Returns:
        Formatted migration report for stakeholders

    """
    try:
        from datetime import datetime

        # Generate report based on format
        report = _generate_comprehensive_migration_report(
            include_technical_details == "yes"
        )

        current_date = datetime.now().strftime("%Y-%m-%d")

        return f"""# Chef to Ansible Migration Report
**Generated:** {current_date}
**Report Type:** {report_format.title()}
**Technical Details:** {"Included" if include_technical_details == "yes" else "Summary Only"}

## Executive Summary
{report["executive_summary"]}

## Migration Scope and Objectives
{report["scope_objectives"]}

## Current State Analysis
{report["current_state"]}

## Target State Architecture
{report["target_state"]}

## Migration Strategy and Approach
{report["strategy"]}

## Cost-Benefit Analysis
{report["cost_benefit"]}

## Timeline and Resource Requirements
{report["timeline_resources"]}

## Risk Assessment and Mitigation
{report["risk_assessment"]}

{"## Technical Implementation Details" if include_technical_details == "yes" else ""}
{report.get("technical_details", "") if include_technical_details == "yes" else ""}

## Recommendations and Next Steps
{report["recommendations"]}

## Appendices
{report["appendices"]}
"""
    except Exception as e:
        return format_error_with_context(e, "generating migration report")


def validate_conversion(
    conversion_type: str,
    result_content: str,
    output_format: str = "text",
) -> str:
    """
    Validate a Chef-to-Ansible conversion for correctness, best practices, and quality.

    This validation framework checks conversions across multiple dimensions:
    - Syntax: YAML/Jinja2/Python syntax validation
    - Semantic: Logic equivalence, variable usage, dependencies
    - Best practices: Naming conventions, idempotency, task organization
    - Security: Privilege escalation, sensitive data handling
    - Performance: Efficiency recommendations

    Args:
        conversion_type: Type of conversion to validate
            ('resource', 'recipe', 'template', 'inspec')
        result_content: Converted Ansible code or configuration
        output_format: Output format ('text', 'json', 'summary')

    Returns:
        Validation report with errors, warnings, and suggestions

    """
    try:
        engine = ValidationEngine()
        results = engine.validate_conversion(conversion_type, result_content)
        summary = engine.get_summary()

        if output_format == "json":
            return json.dumps(
                {
                    "summary": summary,
                    "results": [result.to_dict() for result in results],
                },
                indent=2,
            )
        elif output_format == "summary":
            return _format_validation_results_summary(conversion_type, summary)
        else:
            return _format_validation_results_text(conversion_type, results, summary)

    except Exception as e:
        return format_error_with_context(
            e, f"validating Ansible {conversion_type} conversion"
        )


# Private helper functions for assessment


def _validate_assessment_inputs(
    cookbook_paths: str, migration_scope: str, target_platform: str
) -> str | None:
    """
    Validate inputs for migration assessment.

    Args:
        cookbook_paths: Paths to cookbooks
        migration_scope: Scope of migration
        target_platform: Target platform

    Returns:
        Error message if validation fails, None otherwise

    """
    if not cookbook_paths or not cookbook_paths.strip():
        return (
            "Error: Cookbook paths cannot be empty\n\n"
            "Suggestion: Provide comma-separated paths to Chef cookbooks"
        )

    valid_scopes = ["full", "recipes_only", "infrastructure_only"]
    if migration_scope not in valid_scopes:
        return (
            f"Error: Invalid migration scope '{migration_scope}'\n\n"
            f"Suggestion: Use one of {', '.join(valid_scopes)}"
        )

    valid_platforms = ["ansible_awx", "ansible_core", "ansible_tower"]
    if target_platform not in valid_platforms:
        return (
            f"Error: Invalid target platform '{target_platform}'\n\n"
            f"Suggestion: Use one of {', '.join(valid_platforms)}"
        )

    return None


def _parse_cookbook_paths(cookbook_paths: str) -> list[Any]:
    """
    Parse and validate cookbook paths.

    Args:
        cookbook_paths: Comma-separated paths to cookbooks

    Returns:
        List of valid Path objects (may be empty)

    """
    paths = [_normalize_path(path.strip()) for path in cookbook_paths.split(",")]
    valid_paths = [p for p in paths if p.exists()]
    return valid_paths


def _analyse_cookbook_metrics(
    valid_paths: list[Any],
) -> tuple[list[Any], dict[str, int]]:
    """
    Analyse metrics for all cookbooks.

    Args:
        valid_paths: List of valid cookbook paths

    Returns:
        Tuple of (cookbook_assessments, overall_metrics)

    """
    cookbook_assessments = []
    overall_metrics = {
        "total_cookbooks": 0,
        "total_recipes": 0,
        "total_resources": 0,
        "complexity_score": 0,
        "estimated_effort_days": 0,
    }

    for cookbook_path in valid_paths:
        # deepcode ignore PT: path normalized via _normalize_path
        assessment = _assess_single_cookbook(cookbook_path)
        cookbook_assessments.append(assessment)

        # Aggregate metrics
        overall_metrics["total_cookbooks"] += 1
        overall_metrics["total_recipes"] += assessment["metrics"]["recipe_count"]
        overall_metrics["total_resources"] += assessment["metrics"]["resource_count"]
        overall_metrics["complexity_score"] += assessment["complexity_score"]
        overall_metrics["estimated_effort_days"] += assessment["estimated_effort_days"]

    # Calculate averages
    if cookbook_assessments:
        overall_metrics["avg_complexity"] = int(
            overall_metrics["complexity_score"] / len(cookbook_assessments)
        )

    return cookbook_assessments, overall_metrics


def _format_assessment_report(
    migration_scope: str,
    target_platform: str,
    overall_metrics: dict[str, int],
    cookbook_assessments: list[Any],
    recommendations: str,
    roadmap: str,
) -> str:
    """
    Format the final assessment report.

    Args:
        migration_scope: Scope of migration
        target_platform: Target platform
        overall_metrics: Overall metrics dictionary
        cookbook_assessments: List of cookbook assessments
        recommendations: Migration recommendations
        roadmap: Migration roadmap

    Returns:
        Formatted report string

    """
    return f"""# Chef to Ansible Migration Assessment
# Scope: {migration_scope}
# Target Platform: {target_platform}

## Overall Migration Metrics:
{_format_overall_metrics(overall_metrics)}

## Cookbook Assessments:
{_format_cookbook_assessments(cookbook_assessments)}

## Migration Complexity Analysis:
{_format_complexity_analysis(cookbook_assessments)}

## Migration Recommendations:
{recommendations}

## Migration Roadmap:
{roadmap}

## Risk Assessment:
{_assess_migration_risks(cookbook_assessments, target_platform)}

## Resource Requirements:
{_estimate_resource_requirements(overall_metrics, target_platform)}
"""


def _count_cookbook_artifacts(cookbook_path) -> dict[str, int]:
    """Count basic cookbook artifacts (recipes, templates, files)."""
    recipes_dir = _safe_join(cookbook_path, "recipes")
    recipe_count = len(list(recipes_dir.glob("*.rb"))) if recipes_dir.exists() else 0

    templates_count = (
        len(list(_safe_join(cookbook_path, "templates").glob("*")))
        if _safe_join(cookbook_path, "templates").exists()
        else 0
    )

    files_count = (
        len(list(_safe_join(cookbook_path, "files").glob("*")))
        if _safe_join(cookbook_path, "files").exists()
        else 0
    )

    return {
        "recipe_count": recipe_count,
        "templates": templates_count,
        "files": files_count,
    }


def _analyse_recipe_complexity(cookbook_path) -> dict[str, int]:
    """Analyse recipe files for resource counts, Ruby blocks, and custom resources."""
    recipes_dir = _safe_join(cookbook_path, "recipes")
    resource_count = 0
    custom_resources = 0
    ruby_blocks = 0

    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            with recipe_file.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Count Chef resources
                resources = len(
                    re.findall(r'\w{1,100}\s+[\'"]([^\'"]{0,200})[\'"]\s+do', content)
                )
                ruby_blocks += len(
                    re.findall(r"ruby_block|execute|bash", content, re.IGNORECASE)
                )
                custom_resources += len(
                    re.findall(
                        r"custom_resource|provides|use_inline_resources", content
                    )
                )
                resource_count += resources

    return {
        "resource_count": resource_count,
        "custom_resources": custom_resources,
        "ruby_blocks": ruby_blocks,
    }


def _calculate_complexity_score(metrics: dict[str, int]) -> int:
    """Calculate complexity score (0-100) based on metrics."""
    recipe_count = metrics["recipe_count"]
    resource_count = metrics["resource_count"]

    complexity_factors = {
        "recipe_count": min(recipe_count * 2, 20),
        "resource_density": min(resource_count / max(recipe_count, 1) * 5, 25),
        "custom_resources": metrics["custom_resources"] * 10,
        "ruby_blocks": metrics["ruby_blocks"] * 5,
        "templates": min(metrics["templates"] * 2, 15),
        "files": min(metrics["files"] * 1, 10),
    }

    return int(sum(complexity_factors.values()))


def _identify_migration_challenges(
    metrics: dict[str, int], complexity_score: int
) -> list[str]:
    """Identify migration challenges based on metrics."""
    challenges = []

    if metrics["custom_resources"] > 0:
        challenges.append(
            f"{metrics['custom_resources']} custom resources requiring manual conversion"
        )
    if metrics["ruby_blocks"] > 5:
        challenges.append(
            f"{metrics['ruby_blocks']} Ruby blocks needing shell script conversion"
        )
    if complexity_score > 70:
        challenges.append("High complexity cookbook requiring expert review")

    return challenges


def _determine_migration_priority(complexity_score: int) -> str:
    """Determine migration priority based on complexity score."""
    if complexity_score < 30:
        return "low"
    elif complexity_score > 70:
        return "high"
    return "medium"


def _assess_single_cookbook(cookbook_path: Path) -> dict:
    """Assess complexity of a single cookbook."""
    # cookbook_path is already normalized to a Path object
    cookbook = cookbook_path

    # Collect metrics
    artifact_counts = _count_cookbook_artifacts(cookbook)
    recipe_complexity = _analyse_recipe_complexity(cookbook)
    metrics = {**artifact_counts, **recipe_complexity}

    # Calculate complexity and effort
    complexity_score = _calculate_complexity_score(metrics)
    # More realistic effort: 0.5-2 hours per recipe with AI assistance
    # Base: 1 hour per recipe = 0.125 days (8-hour day)
    base_effort = metrics["recipe_count"] * 0.125  # 0.125 days per recipe
    complexity_multiplier = 1 + (complexity_score / 100)
    estimated_effort = round(base_effort * complexity_multiplier, 1)

    # Build assessment
    return {
        "cookbook_name": cookbook.name,
        "cookbook_path": str(cookbook),
        "metrics": metrics,
        "complexity_score": complexity_score,
        "estimated_effort_days": estimated_effort,
        "challenges": _identify_migration_challenges(metrics, complexity_score),
        "migration_priority": _determine_migration_priority(complexity_score),
        "dependencies": [],
    }


def _format_overall_metrics(metrics: dict) -> str:
    """Format overall migration metrics."""
    return f"""• Total Cookbooks: {metrics["total_cookbooks"]}
• Total Recipes: {metrics["total_recipes"]}
• Total Resources: {metrics["total_resources"]}
• Average Complexity: {metrics.get("avg_complexity", 0):.1f}/100
• Estimated Total Effort: {metrics["estimated_effort_days"]:.1f} person-days
• Estimated Duration: {max(1, int(metrics["estimated_effort_days"] / 2))}-{max(2, int(metrics["estimated_effort_days"]))} weeks (with 2-4 parallel engineers)"""


def _format_cookbook_assessments(assessments: list) -> str:
    """Format individual cookbook assessments."""
    if not assessments:
        return "No cookbooks assessed."

    def _get_priority_icon(priority: str) -> str:
        """Get priority icon based on migration priority level."""
        if priority == "high":
            return "🔴"
        elif priority == "medium":
            return "🟡"
        else:
            return "🟢"

    formatted = []
    for assessment in assessments:
        priority_icon = _get_priority_icon(assessment["migration_priority"])
        formatted.append(f"""### {assessment["cookbook_name"]} {priority_icon}
• Complexity Score: {assessment["complexity_score"]:.1f}/100
• Estimated Effort: {assessment["estimated_effort_days"]} days
• Recipes: {assessment["metrics"]["recipe_count"]}
• Resources: {assessment["metrics"]["resource_count"]}
• Custom Resources: {assessment["metrics"]["custom_resources"]}
• Challenges: {len(assessment["challenges"])}""")

    return "\n\n".join(formatted)


def _format_complexity_analysis(assessments: list) -> str:
    """Format complexity analysis."""
    if not assessments:
        return "No complexity analysis available."

    high_complexity = [a for a in assessments if a["complexity_score"] > 70]
    medium_complexity = [a for a in assessments if 30 <= a["complexity_score"] <= 70]
    low_complexity = [a for a in assessments if a["complexity_score"] < 30]

    return f"""• High Complexity (>70): {len(high_complexity)} cookbooks
• Medium Complexity (30-70): {len(medium_complexity)} cookbooks
• Low Complexity (<30): {len(low_complexity)} cookbooks

**Top Migration Challenges:**
{_identify_top_challenges(assessments)}"""


def _identify_top_challenges(assessments: list) -> str:
    """Identify the most common migration challenges."""
    challenge_counts: dict[str, int] = {}
    for assessment in assessments:
        for challenge in assessment["challenges"]:
            challenge_counts[challenge] = challenge_counts.get(challenge, 0) + 1

    top_challenges = sorted(challenge_counts.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]

    formatted = []
    for challenge, count in top_challenges:
        formatted.append(f"  - {challenge} ({count} cookbooks)")

    return (
        "\n".join(formatted)
        if formatted
        else "  - No significant challenges identified"
    )


def _generate_migration_recommendations_from_assessment(
    assessments: list, metrics: dict, target_platform: str
) -> str:
    """Generate migration recommendations based on assessment."""
    recommendations = []

    # Platform-specific recommendations
    if target_platform == "ansible_awx":
        recommendations.append(
            "• Implement AWX/AAP integration for job templates and workflows"
        )
        recommendations.append(
            "• Set up dynamic inventory sources for Chef server integration"
        )

    # Complexity-based recommendations
    avg_complexity = metrics.get("avg_complexity", 0)
    if avg_complexity > 60:
        recommendations.append(
            "• Consider phased migration approach due to high complexity"
        )
        recommendations.append(
            "• Allocate additional time for custom resource conversion"
        )
        recommendations.append("• Plan for comprehensive testing and validation")
    else:
        recommendations.append("• Standard migration timeline should be sufficient")
        recommendations.append("• Consider big-bang approach for faster delivery")

    # Effort-based recommendations
    total_effort = metrics["estimated_effort_days"]
    if total_effort > 30:
        recommendations.append("• Establish dedicated migration team")
        recommendations.append("• Consider parallel migration tracks")
    else:
        recommendations.append("• Single developer can handle migration with oversight")

    # Custom resource recommendations
    custom_resource_cookbooks = [
        a for a in assessments if a["metrics"]["custom_resources"] > 0
    ]
    if custom_resource_cookbooks:
        recommendations.append(
            f"• {len(custom_resource_cookbooks)} cookbooks need custom resource conversion"
        )
        recommendations.append(
            "• Prioritize custom resource analysis and conversion strategy"
        )

    return "\n".join(recommendations)


def _create_migration_roadmap(assessments: list) -> str:
    """Create a migration roadmap based on assessments."""
    # Sort cookbooks by complexity (low to high for easier wins first)
    sorted_cookbooks = sorted(assessments, key=lambda x: x["complexity_score"])

    phases = {
        "Phase 1 - Foundation (Weeks 1-2)": [
            "Set up Ansible/AWX environment",
            "Establish CI/CD pipelines",
            "Create testing framework",
            "Train team on Ansible best practices",
        ],
        "Phase 2 - Low Complexity Migration (Weeks 3-5)": [],
        "Phase 3 - Medium Complexity Migration (Weeks 6-9)": [],
        "Phase 4 - High Complexity Migration (Weeks 10-12)": [],
        "Phase 5 - Validation and Cleanup (Weeks 13-14)": [
            "Comprehensive testing",
            "Performance validation",
            "Documentation updates",
            "Team training and handover",
        ],
    }

    # Distribute cookbooks across phases
    for cookbook in sorted_cookbooks:
        if cookbook["complexity_score"] < 30:
            phases["Phase 2 - Low Complexity Migration (Weeks 3-5)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )
        elif cookbook["complexity_score"] < 70:
            phases["Phase 3 - Medium Complexity Migration (Weeks 6-9)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )
        else:
            phases["Phase 4 - High Complexity Migration (Weeks 10-12)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )

    # Format roadmap
    roadmap_formatted = []
    for phase, tasks in phases.items():
        roadmap_formatted.append(f"\n### {phase}")
        for task in tasks:
            roadmap_formatted.append(f"  - {task}")

    return "\n".join(roadmap_formatted)


def _assess_technical_complexity_risks(assessments: list) -> list[str]:
    """Assess risks related to technical complexity."""
    risks = []
    high_complexity_count = len([a for a in assessments if a["complexity_score"] > 70])
    if high_complexity_count > 0:
        risks.append(
            f"🔴 HIGH: {high_complexity_count} high-complexity cookbooks may cause delays"
        )
    return risks


def _assess_custom_resource_risks(assessments: list) -> list[str]:
    """Assess risks related to custom resources and Ruby blocks."""
    risks = []
    custom_resource_count = sum(a["metrics"]["custom_resources"] for a in assessments)
    if custom_resource_count > 0:
        risks.append(
            f"🟡 MEDIUM: {custom_resource_count} custom resources need manual conversion"
        )

    ruby_block_count = sum(a["metrics"]["ruby_blocks"] for a in assessments)
    if ruby_block_count > 10:
        risks.append(
            f"🟡 MEDIUM: {ruby_block_count} Ruby blocks require shell script conversion"
        )

    return risks


def _assess_timeline_risks(assessments: list) -> list[str]:
    """Assess risks related to migration timeline and scope."""
    risks = []
    total_effort = sum(a["estimated_effort_days"] for a in assessments)
    if total_effort > 50:
        risks.append("🟡 MEDIUM: Large migration scope may impact timeline")
    return risks


def _assess_platform_risks(target_platform: str) -> list[str]:
    """Assess risks related to target platform."""
    if target_platform == "ansible_awx":
        return ["🟢 LOW: AWX integration well-supported with existing tools"]
    return []


def _assess_migration_risks(assessments: list, target_platform: str) -> str:
    """Assess migration risks."""
    risks = []

    risks.extend(_assess_technical_complexity_risks(assessments))
    risks.extend(_assess_custom_resource_risks(assessments))
    risks.extend(_assess_timeline_risks(assessments))
    risks.extend(_assess_platform_risks(target_platform))

    if not risks:
        risks.append("🟢 LOW: No significant migration risks identified")

    return "\n".join(risks)


def _estimate_resource_requirements(metrics: dict, target_platform: str) -> str:
    """Estimate resource requirements for migration."""
    total_effort = metrics["estimated_effort_days"]

    # Team size recommendations
    if total_effort < 20:
        team_size = "1 developer + 1 reviewer"
        timeline = "4-6 weeks"
    elif total_effort < 50:
        team_size = "2 developers + 1 senior reviewer"
        timeline = "6-10 weeks"
    else:
        team_size = "3-4 developers + 1 tech lead + 1 architect"
        timeline = "10-16 weeks"

    return f"""• **Team Size:** {team_size}
• **Estimated Timeline:** {timeline}
• **Total Effort:** {total_effort:.1f} person-days
• **Infrastructure:** {target_platform.replace("_", "/").upper()} environment
• **Testing:** Dedicated test environment recommended
• **Training:** 2-3 days Ansible/AWX training for team"""


def _analyse_cookbook_dependencies_detailed(cookbook_path) -> dict:
    """Analyze cookbook dependencies in detail."""
    analysis = {
        "cookbook_name": cookbook_path.name,
        "direct_dependencies": [],
        "transitive_dependencies": [],
        "external_dependencies": [],
        "community_cookbooks": [],
        "circular_dependencies": [],
    }

    # Read metadata.rb for dependencies
    metadata_file = _safe_join(cookbook_path, METADATA_FILENAME)
    if metadata_file.exists():
        with metadata_file.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Parse dependencies

        depends_matches = re.findall(r'depends\s+[\'"]([^\'"]+)[\'"]', content)
        analysis["direct_dependencies"] = depends_matches

    # Read Berksfile for additional dependencies
    berksfile = _safe_join(cookbook_path, "Berksfile")
    if berksfile.exists():
        with berksfile.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        cookbook_matches = re.findall(r'cookbook\s+[\'"]([^\'"]+)[\'"]', content)
        analysis["external_dependencies"].extend(cookbook_matches)

    # Identify community cookbooks (common ones)
    community_cookbook_patterns = [
        "apache2",
        "nginx",
        "mysql",
        "postgresql",
        "java",
        "python",
        "nodejs",
        "docker",
        "build-essential",
        "git",
        "ntp",
        "sudo",
        "users",
    ]

    all_deps = analysis["direct_dependencies"] + analysis["external_dependencies"]
    for dep in all_deps:
        if any(pattern in dep.lower() for pattern in community_cookbook_patterns):
            analysis["community_cookbooks"].append(dep)

    return analysis


def _determine_migration_order(dependency_analysis: dict) -> list:
    """Determine optimal migration order based on dependencies."""
    # For now, return a simple order based on dependency count
    # In a full implementation, this would use topological sorting

    order = []

    # Leaf nodes first (no dependencies)
    if not dependency_analysis["direct_dependencies"]:
        order.append(
            {
                "cookbook": dependency_analysis["cookbook_name"],
                "priority": 1,
                "reason": "No dependencies - can be migrated first",
            }
        )
    else:
        # Has dependencies - migrate after dependencies
        dep_count = len(dependency_analysis["direct_dependencies"])
        priority = min(dep_count + 1, 5)  # Cap at priority 5
        order.append(
            {
                "cookbook": dependency_analysis["cookbook_name"],
                "priority": priority,
                "reason": f"Has {dep_count} dependencies - migrate after dependencies",
            }
        )

    return order


def _identify_circular_dependencies(dependency_analysis: dict) -> list:
    """Identify circular dependencies (simplified)."""
    # This is a simplified implementation
    # A full implementation would build a dependency graph and detect cycles

    circular = []
    cookbook_name = dependency_analysis["cookbook_name"]

    # Check if any dependency might depend back on this cookbook
    for dep in dependency_analysis["direct_dependencies"]:
        if cookbook_name.lower() in dep.lower():  # Simple heuristic
            circular.append(
                {"cookbook1": cookbook_name, "cookbook2": dep, "type": "potential"}
            )

    return circular


def _generate_detailed_migration_plan(
    assessments: list, strategy: str, timeline_weeks: int
) -> dict:
    """Generate detailed migration plan."""
    plan = {
        "executive_summary": "",
        "phases": "",
        "timeline": "",
        "team_requirements": "",
        "prerequisites": "",
        "testing_strategy": "",
        "risk_mitigation": "",
        "success_criteria": "",
        "post_migration": "",
    }

    total_cookbooks = len(assessments)
    total_effort = sum(a["estimated_effort_days"] for a in assessments)

    plan["executive_summary"] = (
        f"""This migration plan covers {total_cookbooks} Chef cookbooks with an estimated effort of {total_effort:.1f} person-days over {timeline_weeks} weeks using a {strategy} approach. The plan balances speed of delivery with risk mitigation, focusing on early wins to build momentum while carefully handling complex cookbooks."""
    )

    # Generate phases based on strategy
    if strategy == "phased":
        plan["phases"] = _generate_phased_migration_phases(assessments, timeline_weeks)
    elif strategy == "big_bang":
        plan["phases"] = _generate_big_bang_phases(assessments, timeline_weeks)
    else:  # parallel
        plan["phases"] = _generate_parallel_migration_phases(timeline_weeks)

    plan["timeline"] = _generate_migration_timeline(strategy, timeline_weeks)

    plan["team_requirements"] = f"""**Core Team:**
• 1 Migration Lead (Ansible expert)
• {min(3, max(1, total_effort // 10))} Ansible Developers
• 1 Chef SME (part-time consultation)
• 1 QA Engineer for testing
• 1 DevOps Engineer for infrastructure

**Skills Required:**
• Advanced Ansible/AWX experience
• Chef cookbook understanding
• Infrastructure as Code principles
• CI/CD pipeline experience"""
    plan["prerequisites"] = """• AWX/AAP environment setup and configured
• Git repository structure established
• CI/CD pipelines created for Ansible playbooks
• Test environments provisioned
• Team training on Ansible best practices completed
• Chef cookbook inventory and documentation review
• Stakeholder alignment on migration approach"""
    plan["testing_strategy"] = """**Testing Phases:**
1. **Unit Testing:** Ansible syntax validation and linting
2. **Integration Testing:** Playbook execution in test environments
3. **Functional Testing:** End-to-end application functionality validation
4. **Performance Testing:** Resource usage and execution time comparison
5. **User Acceptance Testing:** Stakeholder validation of migrated functionality

**Testing Tools:**
• ansible-lint for syntax validation
• molecule for role testing
• testinfra for infrastructure testing
• Custom validation scripts for Chef parity"""
    plan[
        "success_criteria"
    ] = """• All Chef cookbooks successfully converted to Ansible playbooks
• 100% functional parity between Chef and Ansible implementations
• No performance degradation in deployment times
• All automated tests passing
• Team trained and comfortable with new Ansible workflows
• Documentation complete and accessible
• Rollback procedures tested and documented"""
    return plan


def _generate_comprehensive_migration_report(include_technical: bool) -> dict:
    """Generate comprehensive migration report."""
    report = {
        "executive_summary": "",
        "scope_objectives": "",
        "current_state": "",
        "target_state": "",
        "strategy": "",
        "cost_benefit": "",
        "timeline_resources": "",
        "risk_assessment": "",
        "recommendations": "",
        "appendices": "",
    }

    # Executive Summary
    report[
        "executive_summary"
    ] = """This report outlines the migration strategy from Chef to Ansible/AWX, providing a comprehensive analysis of the current Chef infrastructure and a detailed roadmap for transition. The migration will modernize configuration management capabilities while reducing operational complexity and improving deployment automation.

**Key Findings:**
• Migration is technically feasible with moderate complexity
• Estimated 8-16 week timeline depending on approach
• Significant long-term cost savings and operational improvements
• Low-to-medium risk with proper planning and execution"""
    # Scope and Objectives
    report["scope_objectives"] = """**Migration Scope:**
• All production Chef cookbooks and recipes
• Chef server configurations and node management
• Existing deployment pipelines and automation
• Monitoring and compliance integrations

**Primary Objectives:**
• Modernize configuration management with Ansible/AWX
• Improve deployment reliability and speed
• Reduce operational overhead and complexity
• Enhance security and compliance capabilities
• Standardize on Red Hat ecosystem tools"""
    # Current State Analysis
    report["current_state"] = """**Current Chef Infrastructure:**
• Chef Server managing X nodes across multiple environments
• Y cookbooks covering infrastructure and application deployment
• Established CI/CD pipelines with Chef integration
• Monitoring and compliance reporting in place

**Pain Points Identified:**
• Complex Chef DSL requiring Ruby expertise
• Lengthy convergence times in large environments
• Limited workflow orchestration capabilities
• Dependency management challenges
• Scaling limitations with current architecture"""
    # Target State Architecture
    report["target_state"] = """**Target Ansible/AWX Architecture:**
• Red Hat Ansible Automation Platform (AWX/AAP)
• Git-based playbook and role management
• Dynamic inventory from multiple sources
• Integrated workflow templates and job scheduling
• Enhanced RBAC and audit capabilities

**Key Improvements:**
• YAML-based playbooks (easier to read/write)
• Faster execution with SSH-based architecture
• Rich workflow orchestration capabilities
• Better integration with CI/CD tools
• Enhanced scalability and performance"""
    if include_technical:
        report["technical_details"] = """## Technical Implementation Approach

### Cookbook Conversion Strategy
• **Resource Mapping:** Direct mapping of Chef resources to Ansible modules
• **Variable Extraction:** Chef node attributes converted to Ansible variables
• **Template Conversion:** ERB templates converted to Jinja2 format
• **Custom Resources:** Manual conversion to Ansible roles/modules

### Data Migration
• **Node Attributes:** Migrated to Ansible inventory variables
• **Data Bags:** Converted to Ansible Vault encrypted variables
• **Environments:** Mapped to inventory groups with variable precedence

### Testing and Validation
• **Syntax Validation:** ansible-lint and yaml-lint integration
• **Functional Testing:** molecule framework for role testing
• **Integration Testing:** testinfra for infrastructure validation
• **Performance Testing:** Execution time and resource usage comparison"""
    return report


def _format_dependency_overview(analysis: dict) -> str:
    """Format dependency overview."""
    return f"""• Direct Dependencies: {len(analysis["direct_dependencies"])}
• External Dependencies: {len(analysis["external_dependencies"])}
• Community Cookbooks: {len(analysis["community_cookbooks"])}
• Circular Dependencies: {len(analysis["circular_dependencies"])}"""


def _format_dependency_graph(analysis: dict) -> str:
    """Format dependency graph (text representation)."""
    graph = [f"{analysis['cookbook_name']} depends on:"]

    for dep in analysis["direct_dependencies"]:
        graph.append(f"  ├── {dep}")

    if analysis["external_dependencies"]:
        graph.append("External dependencies:")
        for dep in analysis["external_dependencies"]:
            graph.append(f"  ├── {dep}")

    return "\n".join(graph) if len(graph) > 1 else "No dependencies found."


def _format_migration_order(order: list) -> str:
    """Format migration order recommendations."""
    if not order:
        return "No order analysis available."

    formatted = []
    for item in sorted(order, key=lambda x: x["priority"]):
        priority_text = f"Priority {item['priority']}"
        formatted.append(f"• {item['cookbook']} - {priority_text}: {item['reason']}")

    return "\n".join(formatted)


def _format_circular_dependencies(circular: list) -> str:
    """Format circular dependencies."""
    if not circular:
        return "✅ No circular dependencies detected."

    formatted = []
    for circ in circular:
        formatted.append(
            f"⚠️  {circ['cookbook1']} ↔ {circ['cookbook2']} ({circ['type']})"
        )

    return "\n".join(formatted)


def _format_external_dependencies(analysis: dict) -> str:
    """Format external dependencies."""
    if not analysis["external_dependencies"]:
        return "No external dependencies."

    return "\n".join([f"• {dep}" for dep in analysis["external_dependencies"]])


def _format_community_cookbooks(analysis: dict) -> str:
    """Format community cookbooks."""
    if not analysis["community_cookbooks"]:
        return "No community cookbooks identified."

    return "\n".join(
        [
            f"• {cb} (consider ansible-galaxy role)"
            for cb in analysis["community_cookbooks"]
        ]
    )


def _analyse_dependency_migration_impact(analysis: dict) -> str:
    """Analyse migration impact of dependencies."""
    impacts = []

    if analysis["community_cookbooks"]:
        impacts.append(
            f"• {len(analysis['community_cookbooks'])} community cookbooks can likely be replaced with Ansible Galaxy roles"
        )

    if analysis["circular_dependencies"]:
        impacts.append(
            f"• {len(analysis['circular_dependencies'])} circular dependencies need resolution before migration"
        )

    direct_count = len(analysis["direct_dependencies"])
    if direct_count > 5:
        impacts.append(
            f"• High dependency count ({direct_count}) suggests complex migration order requirements"
        )

    if not impacts:
        impacts.append(
            "• Low dependency complexity - straightforward migration expected"
        )

    return "\n".join(impacts)


def _generate_phased_migration_phases(assessments: list, timeline_weeks: int) -> str:
    """Generate phased migration phases."""
    phases = []

    # Sort by complexity
    sorted_assessments = sorted(assessments, key=lambda x: x["complexity_score"])

    phase1 = [a for a in sorted_assessments if a["complexity_score"] < 30]
    phase2 = [a for a in sorted_assessments if 30 <= a["complexity_score"] < 70]
    phase3 = [a for a in sorted_assessments if a["complexity_score"] >= 70]

    weeks_per_phase = timeline_weeks // 3

    phases.append(
        f"**Phase 1 (Weeks 1-{weeks_per_phase}):** Foundation & Low Complexity"
    )
    phases.append(f"  • {len(phase1)} low-complexity cookbooks")
    phases.append("  • Setup AWX environment and CI/CD")

    phases.append(
        f"\n**Phase 2 (Weeks {weeks_per_phase + 1}-{weeks_per_phase * 2}):** Medium Complexity"
    )
    phases.append(f"  • {len(phase2)} medium-complexity cookbooks")
    phases.append("  • Parallel conversion and testing")

    phases.append(
        f"\n**Phase 3 (Weeks {weeks_per_phase * 2 + 1}-{timeline_weeks}):** High Complexity & Finalization"
    )
    phases.append(f"  • {len(phase3)} high-complexity cookbooks")
    phases.append("  • Final testing and deployment")

    return "\n".join(phases)


def _generate_big_bang_phases(assessments: list, timeline_weeks: int) -> str:
    """Generate big bang migration phases."""
    return f"""**Phase 1 (Weeks 1-2):** Preparation
  • AWX environment setup
  • Team training and preparation
  • Conversion tooling setup

**Phase 2 (Weeks 3-{timeline_weeks - 2}):** Mass Conversion
  • Parallel conversion of all {len(assessments)} cookbooks
  • Continuous integration and testing
  • Issue resolution and refinement

**Phase 3 (Weeks {timeline_weeks - 1}-{timeline_weeks}):** Cutover
  • Final validation and testing
  • Production deployment
  • Rollback readiness verification"""


def _generate_parallel_migration_phases(timeline_weeks: int) -> str:
    """Generate parallel migration phases."""
    return f"""**Track A - Infrastructure (Weeks 1-{timeline_weeks}):**
  • Core infrastructure cookbooks
  • Base OS configuration
  • Security and compliance

**Track B - Applications (Weeks 1-{timeline_weeks}):**
  • Application deployment cookbooks
  • Service configuration
  • Custom business logic

**Track C - Integration (Weeks 1-{timeline_weeks}):**
  • AWX workflow development
  • CI/CD pipeline integration
  • Testing and validation automation"""


def _generate_migration_timeline(strategy: str, timeline_weeks: int) -> str:
    """Generate migration timeline."""
    milestones = []

    if strategy == "phased":
        week_intervals = timeline_weeks // 4
        milestones = [
            f"Week {week_intervals}: Phase 1 completion - Low complexity cookbooks migrated",
            f"Week {week_intervals * 2}: Phase 2 completion - Medium complexity cookbooks migrated",
            f"Week {week_intervals * 3}: Phase 3 completion - High complexity cookbooks migrated",
            f"Week {timeline_weeks}: Final validation and production deployment",
        ]
    else:
        milestones = [
            "Week 2: Environment setup and team training complete",
            f"Week {timeline_weeks // 2}: 50% of cookbooks converted and tested",
            f"Week {timeline_weeks - 2}: All conversions complete, final testing",
            f"Week {timeline_weeks}: Production deployment and go-live",
        ]

    return "\n".join([f"• {milestone}" for milestone in milestones])


def _build_validation_header(
    conversion_type: str, summary: dict[str, int]
) -> list[str]:
    """Build the header section of validation results."""
    return [
        f"# Validation Results for {conversion_type} Conversion",
        "",
        "## Summary",
        f"• Errors: {summary['errors']}",
        f"• Warnings: {summary['warnings']}",
        f"• Info: {summary['info']}",
        "",
    ]


def _group_results_by_level(
    results: list[ValidationResult],
) -> tuple[list[ValidationResult], list[ValidationResult], list[ValidationResult]]:
    """Group validation results by severity level."""
    errors = [r for r in results if r.level == ValidationLevel.ERROR]
    warnings = [r for r in results if r.level == ValidationLevel.WARNING]
    infos = [r for r in results if r.level == ValidationLevel.INFO]
    return errors, warnings, infos


def _format_result_section(
    title: str, icon: str, results: list[ValidationResult]
) -> list[str]:
    """Format a single validation results section."""
    if not results:
        return []

    lines = [f"## {icon} {title}", ""]
    for result in results:
        lines.append(str(result))
        lines.append("")

    return lines


def _format_validation_results_text(
    conversion_type: str, results: list[ValidationResult], summary: dict[str, int]
) -> str:
    """
    Format validation results as text.

    Args:
        conversion_type: Type of conversion.
        results: List of validation results.
        summary: Summary of validation results.

    Returns:
        Formatted text output.

    """
    if not results:
        return f"""# Validation Results for {conversion_type} Conversion

✅ All validation checks passed! No issues found.
"""

    output_lines = _build_validation_header(conversion_type, summary)
    errors, warnings, infos = _group_results_by_level(results)

    output_lines.extend(_format_result_section("❌ Errors", "", errors))
    output_lines.extend(_format_result_section("⚠️  Warnings", "", warnings))
    output_lines.extend(_format_result_section("ℹ️  Information", "", infos))

    return "\n".join(output_lines)


def _format_validation_results_summary(
    conversion_type: str, summary: dict[str, int]
) -> str:
    """
    Format validation results as summary.

    Args:
        conversion_type: Type of conversion.
        summary: Summary of validation results.

    Returns:
        Formatted summary output.

    """
    return f"""# Validation Summary

✓ Conversion Type: {conversion_type}
• Errors: {summary["errors"]}
• Warnings: {summary["warnings"]}
• Info: {summary["info"]}

{"✅ No critical issues found!" if summary["errors"] == 0 else "❌ Critical issues found - review errors"}
"""
