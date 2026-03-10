# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Contract drafting module for intelligent contract generation.

This module provides tools and models for generating contracts
with compliance checking and risk assessment.

Example:
    >>> from salemates.agent.contract import ContractDraftTool, ComplianceChecker
    >>> checker = ComplianceChecker()
    >>> result = checker.check(contract_text)
"""

from salemates.agent.contract.models import (
    ClauseCategory,
    ComplianceIssue,
    ComplianceResult,
    Contract,
    ContractClause,
    RiskLevel,
)
from salemates.agent.contract.compliance import (
    REQUIRED_CLAUSES,
    PROHIBITED_TERMS,
    ComplianceChecker,
    ProhibitedTerm,
    RequiredClause,
)

__all__ = [
    "ClauseCategory",
    "ComplianceIssue",
    "ComplianceResult",
    "Contract",
    "ContractClause",
    "RiskLevel",
    "REQUIRED_CLAUSES",
    "PROHIBITED_TERMS",
    "ComplianceChecker",
    "ProhibitedTerm",
    "RequiredClause",
]
