# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for content guardrails.

Tests the GuardrailManager and individual guardrails for
detecting policy violations in sales agent responses.
"""

import pytest

from salesmate.agent.safety.guardrails import (
    CompetitorGuardrail,
    CompetitorGuardrailConfig,
    ContractGuardrail,
    ContractGuardrailConfig,
    FeatureGuardrail,
    FeatureGuardrailConfig,
    Guardrail,
    GuardrailConfig,
    GuardrailManager,
    GuardrailType,
    GuardrailViolation,
    PriceGuardrail,
    PriceGuardrailConfig,
    ViolationSeverity,
    create_default_guardrails,
)


# ============ Test Classes ============


class TestGuardrailTypeEnum:
    """Test GuardrailType enum values."""

    def test_all_guardrail_type_values_exist(self):
        """Test all expected guardrail type enum values exist."""
        assert GuardrailType.PRICE.value == "price"
        assert GuardrailType.CONTRACT.value == "contract"
        assert GuardrailType.FEATURE.value == "feature"
        assert GuardrailType.COMPETITOR.value == "competitor"

    def test_guardrail_type_string_representation(self):
        """Test guardrail type string representation."""
        assert str(GuardrailType.PRICE) == "price"
        assert str(GuardrailType.CONTRACT) == "contract"


class TestViolationSeverityEnum:
    """Test ViolationSeverity enum values."""

    def test_all_severity_values_exist(self):
        """Test all expected severity enum values exist."""
        assert ViolationSeverity.WARNING.value == "warning"
        assert ViolationSeverity.BLOCK.value == "block"
        assert ViolationSeverity.REVIEW.value == "review"

    def test_severity_string_representation(self):
        """Test severity string representation."""
        assert str(ViolationSeverity.WARNING) == "warning"
        assert str(ViolationSeverity.BLOCK) == "block"


class TestGuardrailViolation:
    """Test GuardrailViolation dataclass."""

    def test_violation_creation(self):
        """Test creating a GuardrailViolation."""
        violation = GuardrailViolation(
            type=GuardrailType.PRICE,
            severity=ViolationSeverity.WARNING,
            message="Unauthorized discount detected",
            context={"discount_percent": 20, "max_allowed": 15},
            guardrail_name="PriceGuardrail",
        )

        assert violation.type == GuardrailType.PRICE
        assert violation.severity == ViolationSeverity.WARNING
        assert violation.message == "Unauthorized discount detected"
        assert violation.context["discount_percent"] == 20
        assert violation.guardrail_name == "PriceGuardrail"

    def test_violation_default_values(self):
        """Test violation with default values."""
        violation = GuardrailViolation(
            type=GuardrailType.FEATURE,
            severity=ViolationSeverity.REVIEW,
            message="Test violation",
        )

        assert violation.context == {}
        assert violation.guardrail_name == ""


class TestPriceGuardrail:
    """Test PriceGuardrail functionality."""

    @pytest.fixture
    def price_guardrail(self):
        """Create a price guardrail with 15% max discount."""
        return PriceGuardrail(max_discount_percent=15.0)

    def test_detect_unauthorized_discount(self, price_guardrail):
        """Test detection of unauthorized discount exceeding limit."""
        violations = price_guardrail.check("我可以给你20%的折扣")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.PRICE
        assert violations[0].context["discount_percent"] == 20
        assert violations[0].context["max_allowed"] == 15

    def test_detect_authorized_discount(self, price_guardrail):
        """Test authorized discount within limit is allowed."""
        violations = price_guardrail.check("我可以给您10%的折扣")

        # 10% is within 15% limit, should not trigger violation
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]
        assert len(price_violations) == 0

    def test_detect_discount_at_exact_limit(self, price_guardrail):
        """Test discount at exact limit is allowed."""
        violations = price_guardrail.check("我可以给您15%的折扣")

        # 15% is exactly at limit, should not trigger violation
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]
        assert len(price_violations) == 0

    def test_detect_multiple_discount_mentions(self, price_guardrail):
        """Test detection of multiple discount mentions."""
        violations = price_guardrail.check("我可以给你20%折扣，甚至25%优惠")

        assert len(violations) >= 1
        # Should detect at least the highest discount

    def test_detect_discount_patterns_variants(self, price_guardrail):
        """Test detection of various discount phrase patterns."""
        patterns_and_expected = [
            ("可以打85折", False),  # 15% discount
            ("优惠20%", True),  # 20% discount
            ("减免18%", True),  # 18% discount
        ]

        for pattern, should_violate in patterns_and_expected:
            violations = price_guardrail.check(pattern)
            has_violation = len(violations) > 0
            assert has_violation == should_violate, f"Pattern '{pattern}' failed"

    def test_disabled_guardrail(self):
        """Test disabled guardrail doesn't check."""
        config = PriceGuardrailConfig(enabled=False, max_discount_percent=15.0)
        guardrail = PriceGuardrail(config=config)

        violations = guardrail.check("我可以给你50%的折扣")

        assert len(violations) == 0

    def test_no_discount_mentioned(self, price_guardrail):
        """Test text without discount mentions has no violations."""
        violations = price_guardrail.check("我们的产品非常好用")

        assert len(violations) == 0


class TestContractGuardrail:
    """Test ContractGuardrail functionality."""

    @pytest.fixture
    def contract_guardrail(self):
        """Create a contract guardrail."""
        return ContractGuardrail()

    def test_detect_contract_commitment(self, contract_guardrail):
        """Test detection of unauthorized contract commitment."""
        violations = contract_guardrail.check("我们可以签订5年合同")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.CONTRACT
        assert violations[0].severity == ViolationSeverity.BLOCK

    def test_detect_guarantee_commitment(self, contract_guardrail):
        """Test detection of guarantee commitment."""
        violations = contract_guardrail.check("我们保证在一个月内完成交付")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.CONTRACT

    def test_detect_promise_commitment(self, contract_guardrail):
        """Test detection of promise commitment."""
        violations = contract_guardrail.check("我们承诺提供终身维护")

        assert len(violations) >= 1

    def test_allowed_with_escape_hatch(self, contract_guardrail):
        """Test allowed phrases escape contract guardrail."""
        violations = contract_guardrail.check("我们可以签订合同，但需要法务审核")

        assert len(violations) == 0

    def test_allowed_with_approval_escape(self, contract_guardrail):
        """Test approval escape hatch works."""
        violations = contract_guardrail.check("我们保证效果，但需要上级审批确认")

        assert len(violations) == 0

    def test_no_contract_mentioned(self, contract_guardrail):
        """Test text without contract mentions has no violations."""
        violations = contract_guardrail.check("我们的产品功能很强大")

        assert len(violations) == 0

    def test_disabled_guardrail(self):
        """Test disabled guardrail doesn't check."""
        config = ContractGuardrailConfig(enabled=False)
        guardrail = ContractGuardrail(config=config)

        violations = guardrail.check("我们可以签订终身合同")

        assert len(violations) == 0


class TestFeatureGuardrail:
    """Test FeatureGuardrail functionality."""

    @pytest.fixture
    def feature_guardrail(self):
        """Create a feature guardrail."""
        return FeatureGuardrail()

    def test_detect_unverified_feature_claim(self, feature_guardrail):
        """Test detection of claims about unverified features."""
        violations = feature_guardrail.check("我们的产品支持AI自动决策")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.FEATURE
        assert violations[0].severity == ViolationSeverity.REVIEW
        assert "AI自动决策" in violations[0].context["unverified_feature"]

    def test_detect_intelligent_risk_prediction(self, feature_guardrail):
        """Test detection of intelligent risk prediction claim."""
        violations = feature_guardrail.check("我们可以提供智能风险预测功能")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.FEATURE

    def test_detect_automatic_contract_generation(self, feature_guardrail):
        """Test detection of automatic contract generation claim."""
        violations = feature_guardrail.check("系统具有自动合同生成功能")

        assert len(violations) >= 1

    def test_verified_feature_allowed(self, feature_guardrail):
        """Test verified features are allowed."""
        violations = feature_guardrail.check("我们的产品支持团队协作功能")

        # "团队协作" is not in unverified features list
        assert len(violations) == 0

    def test_no_feature_claim(self, feature_guardrail):
        """Test text without feature claims has no violations."""
        violations = feature_guardrail.check("我们的服务非常好")

        assert len(violations) == 0

    def test_disabled_guardrail(self):
        """Test disabled guardrail doesn't check."""
        config = FeatureGuardrailConfig(enabled=False)
        guardrail = FeatureGuardrail(config=config)

        violations = guardrail.check("我们的产品支持AI自动决策")

        assert len(violations) == 0


class TestCompetitorGuardrail:
    """Test CompetitorGuardrail functionality."""

    @pytest.fixture
    def competitor_guardrail(self):
        """Create a competitor guardrail."""
        return CompetitorGuardrail()

    def test_detect_negative_competitor_comparison(self, competitor_guardrail):
        """Test detection of negative competitor comparisons."""
        violations = competitor_guardrail.check("竞品A比我们差很多")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.COMPETITOR
        assert violations[0].severity == ViolationSeverity.REVIEW

    def test_detect_competitor_inferior_claim(self, competitor_guardrail):
        """Test detection of competitor inferior claims."""
        violations = competitor_guardrail.check("竞品B不如我们好用")

        assert len(violations) >= 1

    def test_detect_competitor_problem_mention(self, competitor_guardrail):
        """Test detection of competitor problem mentions."""
        violations = competitor_guardrail.check("他们的问题很多，服务很差")

        assert len(violations) >= 1

    def test_neutral_competitor_mention(self, competitor_guardrail):
        """Test neutral competitor mention without negative comparison."""
        violations = competitor_guardrail.check("竞品A也是市场上不错的选择")

        # No negative comparison pattern
        assert len(violations) == 0

    def test_no_competitor_mentioned(self, competitor_guardrail):
        """Test text without competitor mentions has no violations."""
        violations = competitor_guardrail.check("我们的产品是最好的")

        assert len(violations) == 0

    def test_custom_competitor_names(self):
        """Test guardrail with custom competitor names."""
        config = CompetitorGuardrailConfig(competitor_names=["产品X", "产品Y"])
        guardrail = CompetitorGuardrail(config=config)

        violations = guardrail.check("产品X比我们差很多")

        assert len(violations) >= 1

    def test_disabled_guardrail(self):
        """Test disabled guardrail doesn't check."""
        config = CompetitorGuardrailConfig(enabled=False)
        guardrail = CompetitorGuardrail(config=config)

        violations = guardrail.check("竞品A比我们差很多")

        assert len(violations) == 0


class TestGuardrailManager:
    """Test GuardrailManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a guardrail manager with all default guardrails."""
        return create_default_guardrails(max_discount_percent=15.0)

    def test_add_guardrail(self):
        """Test adding guardrails to manager."""
        manager = GuardrailManager()
        manager.add_guardrail(PriceGuardrail())

        assert len(manager.get_guardrails()) == 1

    def test_remove_guardrail(self):
        """Test removing guardrails from manager."""
        manager = GuardrailManager()
        manager.add_guardrail(PriceGuardrail())
        manager.add_guardrail(ContractGuardrail())

        removed = manager.remove_guardrail("PriceGuardrail")

        assert removed is True
        assert len(manager.get_guardrails()) == 1

    def test_remove_nonexistent_guardrail(self):
        """Test removing non-existent guardrail returns False."""
        manager = GuardrailManager()

        removed = manager.remove_guardrail("NonExistent")

        assert removed is False

    def test_check_multiple_violations(self, manager):
        """Test checking text with multiple violations."""
        # Message with price violation AND competitor violation
        violations = manager.check("我可以给您25%折扣，而且竞品A比我们差很多")

        violation_types = {v.type for v in violations}
        assert GuardrailType.PRICE in violation_types
        assert GuardrailType.COMPETITOR in violation_types

    def test_check_no_violations(self, manager):
        """Test checking text with no violations."""
        violations = manager.check("我们的产品功能非常强大，欢迎了解")

        assert len(violations) == 0

    def test_has_violations_true(self, manager):
        """Test has_violations returns True when violations exist."""
        has_violations = manager.has_violations("我可以给您25%折扣")

        assert has_violations is True

    def test_has_violations_false(self, manager):
        """Test has_violations returns False when no violations."""
        has_violations = manager.has_violations("我们的服务很好")

        assert has_violations is False

    def test_get_blocking_violations(self, manager):
        """Test getting only blocking violations."""
        # Contract violation has BLOCK severity
        violations = manager.get_blocking_violations("我们可以签订终身合同")

        assert len(violations) >= 1
        assert all(v.severity == ViolationSeverity.BLOCK for v in violations)

    def test_needs_review_true(self, manager):
        """Test needs_review returns True for REVIEW or BLOCK severity."""
        # Feature and competitor violations have REVIEW severity
        needs_review = manager.needs_review("我们的产品支持AI自动决策")

        assert needs_review is True

    def test_needs_review_false(self, manager):
        """Test needs_review returns False when no review needed."""
        needs_review = manager.needs_review("我们的产品很好用")

        assert needs_review is False


class TestCreateDefaultGuardrails:
    """Test create_default_guardrails factory function."""

    def test_creates_all_guardrails(self):
        """Test factory creates all default guardrails."""
        manager = create_default_guardrails()

        guardrails = manager.get_guardrails()
        assert len(guardrails) == 4  # Price, Contract, Feature, Competitor

    def test_custom_max_discount(self):
        """Test factory with custom max discount."""
        manager = create_default_guardrails(max_discount_percent=20.0)

        violations = manager.check("我可以给您18%的折扣")
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]

        # 18% is within 20% limit
        assert len(price_violations) == 0

    def test_custom_competitor_names(self):
        """Test factory with custom competitor names."""
        manager = create_default_guardrails(competitor_names=["产品X", "产品Y"])

        violations = manager.check("产品X比我们差很多")

        assert len(violations) >= 1
        assert violations[0].type == GuardrailType.COMPETITOR


class TestGuardrailEdgeCases:
    """Test edge cases in guardrail checking."""

    @pytest.fixture
    def manager(self):
        """Create a guardrail manager."""
        return create_default_guardrails(max_discount_percent=15.0)

    def test_empty_text(self, manager):
        """Test checking empty text."""
        violations = manager.check("")

        assert violations == []

    def test_very_long_text(self, manager):
        """Test checking very long text."""
        long_text = "我们的产品很好" * 100

        violations = manager.check(long_text)

        assert isinstance(violations, list)

    def test_special_characters(self, manager):
        """Test checking text with special characters."""
        violations = manager.check("我可以给您20%！@#折扣")

        assert isinstance(violations, list)

    def test_mixed_case_patterns(self, manager):
        """Test patterns work with mixed case."""
        violations = manager.check("I CAN GIVE YOU 20% DISCOUNT")

        # English patterns should also be detected
        assert isinstance(violations, list)


class TestGuardrailViolationSeverity:
    """Test different violation severity levels."""

    def test_price_violation_severity_warning(self):
        """Test price violations have WARNING severity."""
        guardrail = PriceGuardrail(max_discount_percent=15.0)
        violations = guardrail.check("我可以给您20%折扣")

        assert violations[0].severity == ViolationSeverity.WARNING

    def test_contract_violation_severity_block(self):
        """Test contract violations have BLOCK severity."""
        guardrail = ContractGuardrail()
        violations = guardrail.check("我们可以签订合同")

        assert violations[0].severity == ViolationSeverity.BLOCK

    def test_feature_violation_severity_review(self):
        """Test feature violations have REVIEW severity."""
        guardrail = FeatureGuardrail()
        violations = guardrail.check("我们的产品支持AI自动决策")

        assert violations[0].severity == ViolationSeverity.REVIEW

    def test_competitor_violation_severity_review(self):
        """Test competitor violations have REVIEW severity."""
        guardrail = CompetitorGuardrail()
        violations = guardrail.check("竞品A比我们差很多")

        assert violations[0].severity == ViolationSeverity.REVIEW
