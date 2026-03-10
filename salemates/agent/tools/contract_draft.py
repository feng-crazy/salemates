# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Contract drafting tool for intelligent contract generation.

This tool generates contracts while enforcing:
- Compliance with required clauses
- Detection of prohibited terms
- Risk assessment and scoring

Example:
    >>> from salemates.agent.tools.contract_draft import ContractDraftTool
    >>> tool = ContractDraftTool()
    >>> result = await tool.execute(ctx, customer_name="Acme Corp", ...)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from loguru import logger

from salemates.agent.contract import (
    ClauseCategory,
    ComplianceChecker,
    Contract,
    ContractClause,
    RiskLevel,
)
from salemates.agent.tools.base import Tool, ToolContext


@dataclass
class ContractTemplate:
    """Template for generating contracts.

    Attributes:
        name: Template name.
        contract_type: Type identifier for this template.
        default_clauses: Default clauses included in this template.
        required_parties: Minimum parties required.
    """

    name: str
    contract_type: str
    default_clauses: list[ContractClause]
    required_parties: int = 2


# Standard contract templates
CONTRACT_TEMPLATES: dict[str, ContractTemplate] = {
    "service_agreement": ContractTemplate(
        name="Service Agreement",
        contract_type="service_agreement",
        required_parties=2,
        default_clauses=[
            ContractClause(
                title="Services",
                content="The Provider agrees to provide the services as described in Schedule A attached hereto.",
                category=ClauseCategory.GENERAL,
                is_required=True,
                position=1,
            ),
            ContractClause(
                title="Payment Terms",
                content="Payment shall be due within thirty (30) days of invoice date. Late payments shall accrue interest at a rate of 1.5% per month.",
                category=ClauseCategory.PAYMENT,
                is_required=True,
                position=2,
            ),
            ContractClause(
                title="Term and Termination",
                content="This Agreement shall commence on the Effective Date and continue for a period of one (1) year. Either party may terminate with thirty (30) days written notice.",
                category=ClauseCategory.TERMINATION,
                is_required=True,
                position=3,
            ),
            ContractClause(
                title="Confidentiality",
                content="Each party agrees to maintain the confidentiality of any proprietary information received from the other party during the term of this Agreement.",
                category=ClauseCategory.CONFIDENTIALITY,
                is_required=True,
                position=4,
            ),
            ContractClause(
                title="Limitation of Liability",
                content="In no event shall either party's liability exceed the total fees paid under this Agreement in the twelve (12) months preceding the claim.",
                category=ClauseCategory.LIABILITY,
                is_required=True,
                position=5,
            ),
            ContractClause(
                title="Governing Law",
                content="This Agreement shall be governed by and construed in accordance with the laws of the People's Republic of China.",
                category=ClauseCategory.DISPUTE_RESOLUTION,
                is_required=True,
                position=6,
            ),
        ],
    ),
    "nda": ContractTemplate(
        name="Non-Disclosure Agreement",
        contract_type="nda",
        required_parties=2,
        default_clauses=[
            ContractClause(
                title="Definition of Confidential Information",
                content="Confidential Information means any information disclosed by either party to the other party, either directly or indirectly, in writing, orally or by inspection of tangible objects.",
                category=ClauseCategory.CONFIDENTIALITY,
                is_required=True,
                position=1,
            ),
            ContractClause(
                title="Obligations",
                content="Each party agrees to hold and maintain the Confidential Information in strict confidence for the sole and exclusive benefit of the disclosing party.",
                category=ClauseCategory.CONFIDENTIALITY,
                is_required=True,
                position=2,
            ),
            ContractClause(
                title="Term",
                content="The obligations of this Agreement shall survive for a period of three (3) years from the date of disclosure of the Confidential Information.",
                category=ClauseCategory.TERMINATION,
                is_required=True,
                position=3,
            ),
        ],
    ),
    "sales_contract": ContractTemplate(
        name="Sales Contract",
        contract_type="sales_contract",
        required_parties=2,
        default_clauses=[
            ContractClause(
                title="Product Description",
                content="The Seller agrees to sell and deliver to the Buyer the products as specified in the attached Schedule A.",
                category=ClauseCategory.GENERAL,
                is_required=True,
                position=1,
            ),
            ContractClause(
                title="Price and Payment",
                content="The Buyer shall pay the total purchase price as specified in Schedule A within thirty (30) days of delivery.",
                category=ClauseCategory.PAYMENT,
                is_required=True,
                position=2,
            ),
            ContractClause(
                title="Delivery",
                content="The Seller shall deliver the products to the address specified by the Buyer within the timeframe agreed upon by both parties.",
                category=ClauseCategory.GENERAL,
                is_required=True,
                position=3,
            ),
            ContractClause(
                title="Warranty",
                content="The Seller warrants that the products shall be free from defects in materials and workmanship for a period of twelve (12) months from the date of delivery.",
                category=ClauseCategory.WARRANTY,
                is_required=True,
                position=4,
            ),
            ContractClause(
                title="Limitation of Liability",
                content="The Seller's total liability under this Contract shall not exceed the total purchase price paid by the Buyer.",
                category=ClauseCategory.LIABILITY,
                is_required=True,
                position=5,
            ),
        ],
    ),
}


class ContractDraftTool(Tool):
    """Tool for generating contracts with compliance checking.

    Generates professional contracts while enforcing:
    - Required clause inclusion
    - Prohibited term detection
    - Risk scoring
    - Compliance verification

    Attributes:
        _compliance_checker: Checker for contract compliance.
        _templates: Available contract templates.
    """

    def __init__(self, compliance_checker: ComplianceChecker | None = None):
        """Initialize the contract draft tool.

        Args:
            compliance_checker: Optional custom compliance checker.
        """
        self._compliance_checker = compliance_checker or ComplianceChecker()
        self._templates = CONTRACT_TEMPLATES

    @property
    def name(self) -> str:
        return "draft_contract"

    @property
    def description(self) -> str:
        return (
            "Generate contracts with automatic compliance checking. "
            "Creates professional contracts based on templates, checks for required clauses, "
            "detects prohibited terms, and provides risk assessment. "
            "Returns formatted contract with compliance warnings."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer/client name for the contract",
                },
                "negotiation_summary": {
                    "type": "string",
                    "description": "Summary of negotiation points and agreed terms",
                },
                "contract_type": {
                    "type": "string",
                    "description": "Type of contract to generate",
                    "enum": ["service_agreement", "nda", "sales_contract"],
                    "default": "service_agreement",
                },
                "total_value": {
                    "type": "number",
                    "description": "Total contract value (optional)",
                    "minimum": 0,
                },
                "check_compliance": {
                    "type": "boolean",
                    "description": "Whether to perform compliance checking (default: true)",
                    "default": True,
                },
                "custom_clauses": {
                    "type": "array",
                    "description": "Additional custom clauses to include",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            "required": ["customer_name"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Execute the contract draft tool.

        Args:
            tool_context: Runtime context with session info.
            **kwargs: Tool parameters including customer and contract details.

        Returns:
            Formatted contract with compliance warnings.
        """
        customer_name = kwargs.get("customer_name")
        negotiation_summary = kwargs.get("negotiation_summary", "")
        contract_type = kwargs.get("contract_type", "service_agreement")
        total_value = kwargs.get("total_value")
        check_compliance = kwargs.get("check_compliance", True)
        custom_clauses = kwargs.get("custom_clauses", [])

        try:
            template = self._templates.get(contract_type)
            if not template:
                return f"Error: Unknown contract type '{contract_type}'. Available types: {list(self._templates.keys())}"

            contract = self._create_contract(
                template=template,
                customer_name=customer_name,
                negotiation_summary=negotiation_summary,
                total_value=total_value,
                custom_clauses=custom_clauses,
            )

            if check_compliance:
                contract_text = contract.get_full_text()
                contract.compliance_result = self._compliance_checker.check(contract_text)

            return self._format_contract(contract)

        except Exception as e:
            logger.exception(f"Contract draft error: {e}")
            return f"Error generating contract: {str(e)}"

    def _create_contract(
        self,
        template: ContractTemplate,
        customer_name: str,
        negotiation_summary: str,
        total_value: float | None,
        custom_clauses: list[dict[str, str]],
    ) -> Contract:
        """Create a contract from template.

        Args:
            template: Contract template to use.
            customer_name: Customer name.
            negotiation_summary: Summary of negotiations.
            total_value: Optional contract value.
            custom_clauses: Additional custom clauses.

        Returns:
            Populated Contract object.
        """
        clauses = list(template.default_clauses)

        for i, custom in enumerate(custom_clauses):
            clause = ContractClause(
                title=custom.get("title", f"Custom Clause {i + 1}"),
                content=custom.get("content", ""),
                category=ClauseCategory.GENERAL,
                is_required=False,
                position=len(clauses) + 1,
            )
            clauses.append(clause)

        return Contract(
            title=f"{template.name} - {customer_name}",
            parties=["SaleMates Inc.", customer_name],
            clauses=clauses,
            contract_type=template.contract_type,
            effective_date=datetime.utcnow(),
            expiration_date=datetime.utcnow() + timedelta(days=365),
            negotiation_summary=negotiation_summary if negotiation_summary else None,
            total_value=total_value,
            status="draft",
        )

    def _format_contract(self, contract: Contract) -> str:
        """Format contract for display.

        Args:
            contract: Contract to format.

        Returns:
            Formatted contract string with compliance info.
        """
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║                    📄 CONTRACT DRAFT                         ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Contract ID: {contract.contract_id:<46}║",
            f"║  Type: {contract.contract_type:<51}║",
            f"║  Status: {contract.status:<50}║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
            contract.get_full_text(),
        ]

        if contract.compliance_result:
            result = contract.compliance_result
            lines.extend(
                [
                    "",
                    "╔══════════════════════════════════════════════════════════════╗",
                    "║                 🛡️ COMPLIANCE REPORT                         ║",
                    "╠══════════════════════════════════════════════════════════════╣",
                    f"║  Compliance Score: {result.compliance_score:>5.1f}/100{' ' * 38}║",
                    f"║  Status: {'✅ COMPLIANT' if result.is_compliant else '⚠️  NEEDS REVIEW':<49}║",
                    "╚══════════════════════════════════════════════════════════════╝",
                ]
            )

            if result.missing_clauses:
                lines.append("")
                lines.append("📋 MISSING REQUIRED CLAUSES:")
                for clause in result.missing_clauses:
                    lines.append(f"  ❌ {clause}")

            if result.prohibited_found:
                lines.append("")
                lines.append("⚠️  PROHIBITED TERMS FOUND:")
                for term in result.prohibited_found:
                    lines.append(f"  🚫 {term}")

            if result.issues:
                lines.append("")
                lines.append("🔍 ISSUES DETECTED:")
                for issue in result.issues:
                    risk_icon = {
                        RiskLevel.CRITICAL: "🔴",
                        RiskLevel.HIGH: "🟠",
                        RiskLevel.MEDIUM: "🟡",
                        RiskLevel.LOW: "🟢",
                    }.get(issue.risk_level, "⚪")
                    lines.append(
                        f"  {risk_icon} [{issue.risk_level.value.upper()}] {issue.description}"
                    )
                    if issue.suggested_fix:
                        lines.append(f"     💡 Suggested: {issue.suggested_fix}")

            if result.warnings:
                lines.append("")
                lines.append("⚡ WARNINGS:")
                for warning in result.warnings:
                    lines.append(f"  • {warning}")

        risk_summary = contract.get_risk_summary()
        if risk_summary.get("has_issues"):
            lines.extend(
                [
                    "",
                    "📊 RISK SUMMARY:",
                    f"  Overall Risk Level: {risk_summary['overall_risk'].value.upper()}",
                ]
            )

        if contract.negotiation_summary:
            lines.extend(
                [
                    "",
                    "📝 NEGOTIATION SUMMARY:",
                    f"  {contract.negotiation_summary}",
                ]
            )

        lines.extend(
            [
                "",
                "────────────────────────────────────────────────────────────────",
                "⚠️  This is a DRAFT contract. Review and approval required.",
                "    Contact legal department for final review before signing.",
                "────────────────────────────────────────────────────────────────",
            ]
        )

        return "\n".join(lines)

    def get_available_templates(self) -> list[dict[str, Any]]:
        """Get available contract templates.

        Returns:
            List of template information dictionaries.
        """
        return [
            {
                "type": template.contract_type,
                "name": template.name,
                "required_parties": template.required_parties,
                "clause_count": len(template.default_clauses),
            }
            for template in self._templates.values()
        ]
