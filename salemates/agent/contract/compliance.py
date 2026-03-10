# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Contract compliance checker.

Validates contracts against required clauses and prohibited terms,
providing compliance scores and risk assessments.

Example:
    >>> from salemates.agent.contract.compliance import ComplianceChecker
    >>> checker = ComplianceChecker()
    >>> result = checker.check(contract_text)
    >>> print(result.compliance_score)
    85.5
"""

import re
from dataclasses import dataclass, field
from typing import Any

from salemates.agent.contract.models import (
    ClauseCategory,
    ComplianceIssue,
    ComplianceResult,
    ContractClause,
    RiskLevel,
)


@dataclass
class RequiredClause:
    """Definition of a required contract clause.

    Attributes:
        name: Human-readable name of the required clause.
        category: Clause category for classification.
        keywords: Keywords to detect presence of this clause.
        description: Description of what this clause should cover.
        risk_if_missing: Risk level if this clause is missing.
    """

    name: str
    category: ClauseCategory
    keywords: list[str]
    description: str
    risk_if_missing: RiskLevel = RiskLevel.HIGH


@dataclass
class ProhibitedTerm:
    """Definition of a prohibited term or phrase.

    Attributes:
        pattern: Regex pattern to detect the prohibited term.
        description: Why this term is prohibited.
        risk_level: Risk level if this term is found.
        suggested_alternative: Suggested replacement term.
    """

    pattern: str
    description: str
    risk_level: RiskLevel = RiskLevel.HIGH
    suggested_alternative: str | None = None


# Standard required clauses for business contracts
REQUIRED_CLAUSES: list[RequiredClause] = [
    RequiredClause(
        name="Payment Terms",
        category=ClauseCategory.PAYMENT,
        keywords=["payment", "付款", "结算", "invoice", "发票", "due", "到期"],
        description="Specifies payment schedule, methods, and terms",
        risk_if_missing=RiskLevel.CRITICAL,
    ),
    RequiredClause(
        name="Termination Clause",
        category=ClauseCategory.TERMINATION,
        keywords=["termination", "终止", "cancel", "取消", "end of contract", "合同结束"],
        description="Defines conditions and procedures for contract termination",
        risk_if_missing=RiskLevel.HIGH,
    ),
    RequiredClause(
        name="Liability Limitation",
        category=ClauseCategory.LIABILITY,
        keywords=["liability", "责任", "indemnify", "赔偿", "limitation", "限制"],
        description="Limits liability and defines indemnification terms",
        risk_if_missing=RiskLevel.HIGH,
    ),
    RequiredClause(
        name="Confidentiality",
        category=ClauseCategory.CONFIDENTIALITY,
        keywords=["confidential", "保密", "non-disclosure", "nda", "机密"],
        description="Protects confidential information exchange",
        risk_if_missing=RiskLevel.MEDIUM,
    ),
    RequiredClause(
        name="Dispute Resolution",
        category=ClauseCategory.DISPUTE_RESOLUTION,
        keywords=["dispute", "争议", "arbitration", "仲裁", "jurisdiction", "管辖"],
        description="Defines how disputes will be resolved",
        risk_if_missing=RiskLevel.MEDIUM,
    ),
    RequiredClause(
        name="Intellectual Property",
        category=ClauseCategory.INTELLECTUAL_PROPERTY,
        keywords=["intellectual property", "知识产权", "copyright", "著作权", "patent", "专利"],
        description="Defines IP ownership and usage rights",
        risk_if_missing=RiskLevel.MEDIUM,
    ),
]

# Prohibited terms that indicate problematic contract language
PROHIBITED_TERMS: list[ProhibitedTerm] = [
    ProhibitedTerm(
        pattern=r"unlimited\s+liability|无限制.*责任",
        description="Unlimited liability clauses expose the company to excessive risk",
        risk_level=RiskLevel.CRITICAL,
        suggested_alternative="Limited liability up to contract value",
    ),
    ProhibitedTerm(
        pattern=r"guarantee.*100%|保证.*100%|无条件退款",
        description="Absolute guarantees without conditions",
        risk_level=RiskLevel.HIGH,
        suggested_alternative="Conditional guarantee with defined terms",
    ),
    ProhibitedTerm(
        pattern=r"perpetual|永久|forever|永久性",
        description="Perpetual obligations without end date",
        risk_level=RiskLevel.HIGH,
        suggested_alternative="Defined term with renewal options",
    ),
    ProhibitedTerm(
        pattern=r"exclusive\s+rights.*all\s+markets|独家.*所有市场",
        description="Overly broad exclusive rights",
        risk_level=RiskLevel.MEDIUM,
        suggested_alternative="Limited exclusive rights by territory or segment",
    ),
    ProhibitedTerm(
        pattern=r"penalty.*exceed|罚款.*超过|违约金.*超过",
        description="Excessive penalty clauses",
        risk_level=RiskLevel.HIGH,
        suggested_alternative="Reasonable penalty proportional to damages",
    ),
]


class ComplianceChecker:
    """Checks contracts for compliance with required clauses and prohibited terms.

    Provides comprehensive compliance analysis including:
    - Detection of missing required clauses
    - Identification of prohibited terms
    - Compliance scoring
    - Risk assessment

    Attributes:
        required_clauses: List of required clause definitions.
        prohibited_terms: List of prohibited term definitions.
        custom_rules: Additional custom compliance rules.
    """

    def __init__(
        self,
        required_clauses: list[RequiredClause] | None = None,
        prohibited_terms: list[ProhibitedTerm] | None = None,
    ):
        """Initialize the compliance checker.

        Args:
            required_clauses: Custom required clauses (uses defaults if not provided).
            prohibited_terms: Custom prohibited terms (uses defaults if not provided).
        """
        self.required_clauses = required_clauses or REQUIRED_CLAUSES
        self.prohibited_terms = prohibited_terms or PROHIBITED_TERMS

    def check(self, contract_text: str) -> ComplianceResult:
        """Check contract text for compliance issues.

        Args:
            contract_text: The full contract text to check.

        Returns:
            ComplianceResult with all findings and compliance score.
        """
        issues: list[ComplianceIssue] = []
        missing_clauses: list[str] = []
        prohibited_found: list[str] = []
        warnings: list[str] = []

        # Check for missing required clauses
        for clause in self.required_clauses:
            if not self._has_clause(contract_text, clause):
                missing_clauses.append(clause.name)
                issues.append(
                    ComplianceIssue(
                        issue_type="missing_clause",
                        description=f"Missing required clause: {clause.name}",
                        risk_level=clause.risk_if_missing,
                        clause_title=clause.name,
                        suggested_fix=f"Add {clause.name} clause: {clause.description}",
                        context={"category": str(clause.category)},
                    )
                )

        # Check for prohibited terms
        for term in self.prohibited_terms:
            matches = self._find_prohibited_term(contract_text, term)
            for match_text in matches:
                prohibited_found.append(match_text)
                issues.append(
                    ComplianceIssue(
                        issue_type="prohibited_term",
                        description=f"Prohibited term found: {term.description}",
                        risk_level=term.risk_level,
                        suggested_fix=f"Consider alternative: {term.suggested_alternative}"
                        if term.suggested_alternative
                        else None,
                        context={"matched_text": match_text, "pattern": term.pattern},
                    )
                )

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(
            total_required=len(self.required_clauses),
            missing_count=len(missing_clauses),
            prohibited_count=len(prohibited_found),
            issues=issues,
        )

        # Determine overall compliance
        is_compliant = (
            len(missing_clauses) == 0
            and len(prohibited_found) == 0
            and not any(i.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) for i in issues)
        )

        # Add warnings for medium-risk issues
        for issue in issues:
            if issue.risk_level == RiskLevel.MEDIUM:
                warnings.append(f"Review recommended: {issue.description}")

        return ComplianceResult(
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            missing_clauses=missing_clauses,
            prohibited_found=prohibited_found,
            issues=issues,
            warnings=warnings,
        )

    def check_clause(self, clause: ContractClause) -> list[ComplianceIssue]:
        """Check a single clause for compliance issues.

        Args:
            clause: The clause to check.

        Returns:
            List of compliance issues found in the clause.
        """
        issues: list[ComplianceIssue] = []

        for term in self.prohibited_terms:
            matches = self._find_prohibited_term(clause.content, term)
            for match_text in matches:
                issues.append(
                    ComplianceIssue(
                        issue_type="prohibited_term",
                        description=f"Prohibited term in '{clause.title}': {term.description}",
                        risk_level=term.risk_level,
                        clause_title=clause.title,
                        suggested_fix=term.suggested_alternative,
                        context={"matched_text": match_text, "pattern": term.pattern},
                    )
                )

        return issues

    def _has_clause(self, text: str, clause: RequiredClause) -> bool:
        """Check if text contains a specific clause type.

        Args:
            text: Contract text to search.
            clause: Required clause definition.

        Returns:
            True if clause keywords are found, False otherwise.
        """
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in clause.keywords)

    def _find_prohibited_term(self, text: str, term: ProhibitedTerm) -> list[str]:
        """Find prohibited term matches in text.

        Args:
            text: Text to search.
            term: Prohibited term definition.

        Returns:
            List of matched text strings.
        """
        matches: list[str] = []
        for match in re.finditer(term.pattern, text, re.IGNORECASE):
            matches.append(match.group())
        return matches

    def _calculate_compliance_score(
        self,
        total_required: int,
        missing_count: int,
        prohibited_count: int,
        issues: list[ComplianceIssue],
    ) -> float:
        """Calculate overall compliance score.

        Args:
            total_required: Total number of required clauses.
            missing_count: Number of missing clauses.
            prohibited_count: Number of prohibited terms found.
            issues: List of all issues.

        Returns:
            Compliance score from 0-100.
        """
        if total_required == 0:
            return 100.0

        # Base score from missing clauses
        clause_score = ((total_required - missing_count) / total_required) * 60

        # Penalty for prohibited terms
        prohibited_penalty = min(prohibited_count * 10, 30)

        # Penalty for risk levels
        risk_penalty = 0.0
        for issue in issues:
            if issue.risk_level == RiskLevel.CRITICAL:
                risk_penalty += 5
            elif issue.risk_level == RiskLevel.HIGH:
                risk_penalty += 3
            elif issue.risk_level == RiskLevel.MEDIUM:
                risk_penalty += 1

        risk_penalty = min(risk_penalty, 30)

        final_score = max(0, clause_score - prohibited_penalty - risk_penalty)
        return round(final_score, 1)
