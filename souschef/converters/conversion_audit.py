"""Audit trail and conversion quality tracking for v2.1."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ConversionDecision(Enum):
    """Track decision types during conversion."""

    FULLY_CONVERTED = "fully_converted"
    PARTIALLY_CONVERTED = "partially_converted"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


@dataclass
class ResourceConversionRecord:
    """Record of a single resource conversion decision."""

    resource_type: str
    resource_name: str
    decision: ConversionDecision
    reason: str
    complexity_level: str = "simple"  # simple, moderate, complex
    duration_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "decision": self.decision.value,
            "reason": self.reason,
            "complexity_level": self.complexity_level,
            "duration_ms": self.duration_ms,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


@dataclass
class ConversionAuditTrail:
    """Audit trail for a complete cookbook migration."""

    migration_id: str
    cookbook_name: str
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str = ""
    resource_records: list[ResourceConversionRecord] = field(default_factory=list)
    recipe_records: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_resource_record(self, record: ResourceConversionRecord) -> None:
        """Add a resource conversion record."""
        self.resource_records.append(record)

    def add_note(self, note: str) -> None:
        """Add a general note to the audit trail."""
        self.notes.append(f"[{datetime.now().isoformat()}] {note}")

    def finalize(self) -> None:
        """Mark audit trail as complete."""
        self.end_time = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert audit trail to dictionary."""
        return {
            "migration_id": self.migration_id,
            "cookbook_name": self.cookbook_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self._calculate_duration(),
            "resource_records": [r.to_dict() for r in self.resource_records],
            "recipe_records": self.recipe_records,
            "notes": self.notes,
            "summary": self._generate_summary(),
        }

    def _calculate_duration(self) -> float:
        """Calculate total migration duration."""
        if not self.end_time:
            return 0.0

        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds()

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        total_resources = len(self.resource_records)
        fully_converted = len(
            [
                r
                for r in self.resource_records
                if r.decision == ConversionDecision.FULLY_CONVERTED
            ]
        )
        partially_converted = len(
            [
                r
                for r in self.resource_records
                if r.decision == ConversionDecision.PARTIALLY_CONVERTED
            ]
        )
        requires_review = len(
            [
                r
                for r in self.resource_records
                if r.decision == ConversionDecision.REQUIRES_MANUAL_REVIEW
            ]
        )
        errors = len(
            [r for r in self.resource_records if r.decision == ConversionDecision.ERROR]
        )

        conversion_rate = (
            (fully_converted / total_resources * 100) if total_resources > 0 else 0
        )

        return {
            "total_resources": total_resources,
            "fully_converted": fully_converted,
            "partially_converted": partially_converted,
            "requires_manual_review": requires_review,
            "errors": errors,
            "conversion_rate_percent": round(conversion_rate, 2),
            "quality_score": self._calculate_quality_score(),
        }

    def _calculate_quality_score(self) -> float:
        """
        Calculate overall conversion quality score (0-100).

        Based on conversion decisions and complexity levels.
        """
        if not self.resource_records:
            return 100.0

        score = 0.0
        weights = {
            ConversionDecision.FULLY_CONVERTED: 1.0,
            ConversionDecision.PARTIALLY_CONVERTED: 0.6,
            ConversionDecision.REQUIRES_MANUAL_REVIEW: 0.3,
            ConversionDecision.NOT_APPLICABLE: 0.5,
            ConversionDecision.ERROR: 0.0,
        }

        complexity_factor = {
            "simple": 1.0,
            "moderate": 0.8,
            "complex": 0.6,
        }

        for record in self.resource_records:
            decision_weight = weights.get(record.decision, 0.0)
            complexity_weight = complexity_factor.get(record.complexity_level, 1.0)
            record_score = decision_weight * complexity_weight
            score += record_score

        average_score = score / len(self.resource_records)
        return round(average_score * 100, 2)

    def export_json(self, filepath: str) -> None:
        """Export audit trail to JSON file."""
        from pathlib import Path

        Path(filepath).write_text(
            json.dumps(self.to_dict(), indent=2), encoding="utf-8"
        )

    def export_html_report(self, filepath: str) -> None:
        """Export audit trail as HTML report."""
        summary = self._generate_summary()
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Migration Audit Trail - {self.cookbook_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin-right: 30px; }}
        .quality-score {{ font-size: 24px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .fully-converted {{ background: #e8f5e9; }}
        .partially-converted {{ background: #fff9c4; }}
        .requires-review {{ background: #ffccbc; }}
        .error {{ background: #ffcdd2; }}
    </style>
</head>
<body>
    <h1>Conversion Audit Trail</h1>
    <p><strong>Cookbook:</strong> {self.cookbook_name}</p>
    <p><strong>Migration ID:</strong> {self.migration_id}</p>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">
            <strong>Conversion Rate:</strong> {summary["conversion_rate_percent"]}%
        </div>
        <div class="metric quality-score">
            Quality Score: {summary["quality_score"]}/100
        </div>
        <div style="margin-top: 15px;">
            <p>Total Resources: {summary["total_resources"]}</p>
            <p class="fully-converted">
                ✓ Fully Converted: {summary["fully_converted"]}
            </p>
            <p class="partially-converted">
                ~ Partially Converted: {summary["partially_converted"]}
            </p>
            <p class="requires-review">
                ⚠ Requires Manual Review: {summary["requires_manual_review"]}
            </p>
            <p class="error">
                ✗ Errors: {summary["errors"]}
            </p>
        </div>
    </div>

    <h2>Resource Conversion Details</h2>
    <table>
        <tr>
            <th>Resource Type</th>
            <th>Resource Name</th>
            <th>Decision</th>
            <th>Complexity</th>
            <th>Reason</th>
        </tr>
"""

        for record in self.resource_records:
            row_class = {
                ConversionDecision.FULLY_CONVERTED: "fully-converted",
                ConversionDecision.PARTIALLY_CONVERTED: "partially-converted",
                ConversionDecision.REQUIRES_MANUAL_REVIEW: "requires-review",
                ConversionDecision.ERROR: "error",
            }.get(record.decision, "")

            html += f"""
        <tr class="{row_class}">
            <td>{record.resource_type}</td>
            <td>{record.resource_name}</td>
            <td>{record.decision.value}</td>
            <td>{record.complexity_level}</td>
            <td>{record.reason}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        from pathlib import Path

        Path(filepath).write_text(html, encoding="utf-8")
