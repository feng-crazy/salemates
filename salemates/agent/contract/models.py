# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Contract data models for intelligent contract drafting.

This module defines the core data models for contract generation,
including contracts, clauses, compliance issues, and risk levels.

Example:
    >>> from salemates.agent.contract.models import Contract, ContractClause
    >>> clause = ContractClause(
    ...     title="Payment Terms",
    ...     content="Payment due within 30 days of invoice date."
    ... )
    >>> contract = Contract(
    ...     title="Service Agreement",
    ...     parties=["Vendor", "Client"],
    ...     clauses=[clause]
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class RiskLevel(str, Enum):
    """Risk level for contract clauses or issues.

    Each level indicates the severity of a compliance issue or
    the risk associated with a contract clause.
    """

    LOW = "low"  # Minor issue, easily addressable
    MEDIUM = "medium"  # Moderate issue, requires attention
    HIGH = "high"  # Significant issue, requires immediate attention
    CRITICAL = "critical"  # Blocking issue, must be resolved before signing

    def __str__(self) -> str:
        """Return the string value of the risk level."""
        return self.value


class ClauseCategory(str, Enum):
    """Category for contract clauses.

    Used to organize and identify clause types for compliance checking.
    """

    PAYMENT = "payment"  # Payment terms and conditions
    TERMINATION = "termination"  # Termination and cancellation terms
    LIABILITY = "liability"  # Liability and indemnification
    CONFIDENTIALITY = "confidentiality"  # Confidentiality and NDA
    INTELLECTUAL_PROPERTY = "intellectual_property"  # IP rights and ownership
    DISPUTE_RESOLUTION = "dispute_resolution"  # Dispute resolution mechanisms
    WARRANTY = "warranty"  # Warranties and guarantees
    SERVICE_LEVEL = "service_level"  # SLA and performance metrics
    DATA_PROTECTION = "data_protection"  # Data privacy and protection
    GENERAL = "general"  # General terms and conditions

    def __str__(self) -> str:
        """Return the string value of the clause category."""
        return self.value


@dataclass
class ContractClause:
    """Individual contract clause.

    Represents a single clause or section within a contract document.

    Attributes:
        title: Human-readable title for the clause.
        content: The actual text content of the clause.
        category: Category classification for compliance checking.
        is_required: Whether this clause is required for compliance.
        position: Position/order in the contract document.
        metadata: Additional metadata about the clause.
    """

    title: str
    content: str
    category: ClauseCategory = ClauseCategory.GENERAL
    is_required: bool = False
    position: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceIssue:
    """Represents a detected compliance issue in a contract.

    Tracks issues found during contract compliance checking,
    including missing clauses, prohibited terms, and risk levels.

    Attributes:
        issue_type: Type of compliance issue (e.g., "missing_clause", "prohibited_term").
        description: Human-readable description of the issue.
        risk_level: Severity level of the issue.
        clause_title: Title of the related clause (if applicable).
        suggested_fix: Suggested resolution for the issue.
        context: Additional context about where the issue was found.
    """

    issue_type: str
    description: str
    risk_level: RiskLevel
    clause_title: Optional[str] = None
    suggested_fix: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceResult:
    """Result of contract compliance checking.

    Contains all findings from checking a contract against
    compliance rules and required clauses.

    Attributes:
        is_compliant: Whether the contract passes all compliance checks.
        compliance_score: Score from 0-100 indicating overall compliance.
        missing_clauses: List of required clauses that are missing.
        prohibited_found: List of prohibited terms/phrases found.
        issues: List of all compliance issues detected.
        warnings: List of non-blocking warnings.
    """

    is_compliant: bool
    compliance_score: float
    missing_clauses: list[str] = field(default_factory=list)
    prohibited_found: list[str] = field(default_factory=list)
    issues: list[ComplianceIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Contract:
    """Complete contract document.

    Represents a full contract with all clauses, parties,
    and metadata.

    Attributes:
        title: Contract title/name.
        parties: List of parties to the contract.
        clauses: List of contract clauses.
        contract_id: Unique identifier for the contract.
        contract_type: Type of contract (e.g., "service_agreement", "nda").
        effective_date: Date when the contract becomes effective.
        expiration_date: Date when the contract expires.
        negotiation_summary: Summary of negotiation points.
        total_value: Total monetary value of the contract.
        currency: Currency for the contract value.
        status: Current status of the contract.
        metadata: Additional metadata.
        compliance_result: Results of compliance checking.
    """

    title: str
    parties: list[str]
    clauses: list[ContractClause] = field(default_factory=list)
    contract_id: str = field(default_factory=lambda: f"CTR-{uuid.uuid4().hex[:8].upper()}")
    contract_type: str = "service_agreement"
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    negotiation_summary: Optional[str] = None
    total_value: Optional[float] = None
    currency: str = "CNY"
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)
    compliance_result: Optional[ComplianceResult] = None

    def get_full_text(self) -> str:
        """Generate the full contract text.

        Returns:
            Complete contract document as formatted text.
        """
        lines = [
            f"{'=' * 60}",
            f"  {self.title}",
            f"  Contract ID: {self.contract_id}",
            f"{'=' * 60}",
            "",
            "PARTIES",
            "-" * 40,
        ]

        for i, party in enumerate(self.parties, 1):
            lines.append(f"  {i}. {party}")

        lines.extend(
            [
                "",
                "TERMS AND CONDITIONS",
                "-" * 40,
            ]
        )

        # Sort clauses by position
        sorted_clauses = sorted(self.clauses, key=lambda c: c.position)

        for clause in sorted_clauses:
            lines.extend(
                [
                    "",
                    f"## {clause.title}",
                    "",
                    clause.content,
                ]
            )

        lines.extend(
            [
                "",
                "-" * 40,
                f"Contract Type: {self.contract_type}",
            ]
        )

        if self.effective_date:
            lines.append(f"Effective Date: {self.effective_date.strftime('%Y-%m-%d')}")

        if self.expiration_date:
            lines.append(f"Expiration Date: {self.expiration_date.strftime('%Y-%m-%d')}")

        if self.total_value is not None:
            lines.append(f"Total Value: {self.currency} {self.total_value:,.2f}")

        lines.extend(
            [
                "",
                "=" * 60,
            ]
        )

        return "\n".join(lines)

    def get_risk_summary(self) -> dict[str, Any]:
        """Get a summary of risk levels in the contract.

        Returns:
            Dictionary with risk level counts and overall risk assessment.
        """
        if not self.compliance_result:
            return {"has_issues": False, "risk_levels": {}}

        risk_counts: dict[RiskLevel, int] = {}
        for issue in self.compliance_result.issues:
            risk_counts[issue.risk_level] = risk_counts.get(issue.risk_level, 0) + 1

        # Determine overall risk
        overall_risk = RiskLevel.LOW
        if risk_counts.get(RiskLevel.CRITICAL, 0) > 0:
            overall_risk = RiskLevel.CRITICAL
        elif risk_counts.get(RiskLevel.HIGH, 0) > 0:
            overall_risk = RiskLevel.HIGH
        elif risk_counts.get(RiskLevel.MEDIUM, 0) > 0:
            overall_risk = RiskLevel.MEDIUM

        return {
            "has_issues": len(self.compliance_result.issues) > 0,
            "overall_risk": overall_risk,
            "risk_levels": {str(k): v for k, v in risk_counts.items()},
            "compliance_score": self.compliance_result.compliance_score,
        }
