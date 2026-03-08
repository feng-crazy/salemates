"""
Unit tests for sales stage state machine.
"""

import pytest

from salesmate.agent.stages import (
    NEGATIVE_SIGNALS,
    POSITIVE_SIGNALS,
    SIGNAL_TO_STAGE,
    TRANSITION_RULES,
    TRANSITION_TRIGGERS,
    ConversationSignal,
    SalesStage,
    SalesStageStateMachine,
    SignalCategory,
    StageTransition,
    TransitionRule,
    TransitionType,
    evaluate_transition,
    get_all_signals,
    get_signal_definition,
    get_signals_by_category,
    get_transition_rule,
)


class TestSalesStage:
    """Test SalesStage enum."""

    def test_all_stages_exist(self):
        """Test all expected stages exist."""
        assert SalesStage.NEW_CONTACT.value == "new_contact"
        assert SalesStage.DISCOVERY.value == "discovery"
        assert SalesStage.PRESENTATION.value == "presentation"
        assert SalesStage.NEGOTIATION.value == "negotiation"
        assert SalesStage.CLOSE.value == "close"
        assert SalesStage.LOST.value == "lost"

    def test_stage_string_representation(self):
        """Test stage string representation."""
        assert str(SalesStage.NEW_CONTACT) == "new_contact"
        assert str(SalesStage.DISCOVERY) == "discovery"

    def test_stage_count(self):
        """Test correct number of stages."""
        assert len(SalesStage) == 6


class TestStageTransition:
    """Test StageTransition dataclass."""

    def test_transition_creation(self):
        """Test creating a stage transition."""
        transition = StageTransition(
            from_stage=SalesStage.NEW_CONTACT,
            to_stage=SalesStage.DISCOVERY,
            trigger="customer_replied",
            required_signals=["customer_shows_interest"],
        )
        assert transition.from_stage == SalesStage.NEW_CONTACT
        assert transition.to_stage == SalesStage.DISCOVERY
        assert transition.trigger == "customer_replied"
        assert "customer_shows_interest" in transition.required_signals
        assert transition.timestamp is not None

    def test_transition_default_values(self):
        """Test transition with default values."""
        transition = StageTransition(
            from_stage=SalesStage.NEW_CONTACT,
            to_stage=SalesStage.DISCOVERY,
            trigger="test",
        )
        assert transition.required_signals == []
        assert transition.timestamp is not None


class TestSalesStageStateMachine:
    """Test SalesStageStateMachine class."""

    def test_initial_state(self):
        """Test initial state is set correctly."""
        sm = SalesStageStateMachine()
        assert sm.transition_history == []

    def test_valid_transitions_defined(self):
        """Test valid transitions are properly defined."""
        sm = SalesStageStateMachine()
        assert SalesStage.DISCOVERY in sm.VALID_TRANSITIONS[SalesStage.NEW_CONTACT]
        assert SalesStage.LOST in sm.VALID_TRANSITIONS[SalesStage.NEW_CONTACT]
        assert sm.VALID_TRANSITIONS[SalesStage.CLOSE] == []
        assert sm.VALID_TRANSITIONS[SalesStage.LOST] == []

    def test_can_transition_valid(self):
        """Test valid transition detection."""
        sm = SalesStageStateMachine()
        # NEW_CONTACT → DISCOVERY
        assert sm.can_transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        # NEW_CONTACT → LOST
        assert sm.can_transition(SalesStage.NEW_CONTACT, SalesStage.LOST)
        # DISCOVERY → PRESENTATION
        assert sm.can_transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        # PRESENTATION → NEGOTIATION
        assert sm.can_transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION)
        # NEGOTIATION → CLOSE
        assert sm.can_transition(SalesStage.NEGOTIATION, SalesStage.CLOSE)
        # NEGOTIATION → LOST
        assert sm.can_transition(SalesStage.NEGOTIATION, SalesStage.LOST)

    def test_can_transition_invalid(self):
        """Test invalid transition detection."""
        sm = SalesStageStateMachine()
        # Cannot skip stages
        assert not sm.can_transition(SalesStage.NEW_CONTACT, SalesStage.CLOSE)
        # Cannot go backwards
        assert not sm.can_transition(SalesStage.PRESENTATION, SalesStage.NEW_CONTACT)
        # Terminal states have no outgoing transitions
        assert not sm.can_transition(SalesStage.CLOSE, SalesStage.NEW_CONTACT)
        assert not sm.can_transition(SalesStage.LOST, SalesStage.NEW_CONTACT)
        # Cannot transition to same stage
        assert not sm.can_transition(SalesStage.NEW_CONTACT, SalesStage.NEW_CONTACT)

    def test_transition_success(self):
        """Test successful transition."""
        sm = SalesStageStateMachine()
        success, error = sm.transition(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            "customer_replied",
        )
        assert success is True
        assert error is None
        assert len(sm.transition_history) == 1

        transition = sm.transition_history[0]
        assert transition.from_stage == SalesStage.NEW_CONTACT
        assert transition.to_stage == SalesStage.DISCOVERY
        assert transition.trigger == "customer_replied"

    def test_transition_failure(self):
        """Test failed transition."""
        sm = SalesStageStateMachine()
        success, error = sm.transition(
            SalesStage.NEW_CONTACT,
            SalesStage.CLOSE,  # Invalid: cannot skip stages
        )
        assert success is False
        assert error is not None
        assert "Invalid transition" in error
        assert len(sm.transition_history) == 0

    def test_transition_from_terminal_state(self):
        """Test that terminal states cannot transition."""
        sm = SalesStageStateMachine()
        # CLOSE is terminal
        success, error = sm.transition(SalesStage.CLOSE, SalesStage.LOST)
        assert success is False
        assert error is not None

        # LOST is terminal
        success, error = sm.transition(SalesStage.LOST, SalesStage.NEW_CONTACT)
        assert success is False
        assert error is not None

    def test_get_next_possible_stages(self):
        """Test getting next possible stages."""
        sm = SalesStageStateMachine()

        # NEW_CONTACT can go to DISCOVERY or LOST
        next_stages = sm.get_next_possible_stages(SalesStage.NEW_CONTACT)
        assert SalesStage.DISCOVERY in next_stages
        assert SalesStage.LOST in next_stages
        assert len(next_stages) == 2

        # CLOSE is terminal
        next_stages = sm.get_next_possible_stages(SalesStage.CLOSE)
        assert len(next_stages) == 0

        # LOST is terminal
        next_stages = sm.get_next_possible_stages(SalesStage.LOST)
        assert len(next_stages) == 0

    def test_suggest_transition_with_signals(self):
        """Test signal-based transition suggestions."""
        sm = SalesStageStateMachine()

        # Interest signal → DISCOVERY
        result = sm.suggest_transition(["customer_shows_interest"])
        assert result == SalesStage.DISCOVERY

        # Needs identified → PRESENTATION
        result = sm.suggest_transition(["needs_identified"])
        assert result == SalesStage.PRESENTATION

        # Objection raised → NEGOTIATION
        result = sm.suggest_transition(["objection_raised"])
        assert result == SalesStage.NEGOTIATION

        # Agreement reached → CLOSE
        result = sm.suggest_transition(["agreement_reached"])
        assert result == SalesStage.CLOSE

        # Customer unresponsive → LOST
        result = sm.suggest_transition(["customer_unresponsive"])
        assert result == SalesStage.LOST

    def test_suggest_transition_with_current_stage_validation(self):
        """Test transition suggestions respect current stage."""
        sm = SalesStageStateMachine()

        # From NEW_CONTACT, agreement_reached is invalid
        result = sm.suggest_transition(
            ["agreement_reached"],
            current_stage=SalesStage.NEW_CONTACT,
        )
        # Should not suggest CLOSE from NEW_CONTACT (invalid transition)
        assert result is None

        # From NEGOTIATION, agreement_reached is valid
        result = sm.suggest_transition(
            ["agreement_reached"],
            current_stage=SalesStage.NEGOTIATION,
        )
        assert result == SalesStage.CLOSE

        # From NEW_CONTACT, customer_shows_interest is valid
        result = sm.suggest_transition(
            ["customer_shows_interest"],
            current_stage=SalesStage.NEW_CONTACT,
        )
        assert result == SalesStage.DISCOVERY

    def test_suggest_transition_priority(self):
        """Test signal priority in suggestions."""
        sm = SalesStageStateMachine()

        # Agreement reached should take priority over objection
        result = sm.suggest_transition(
            ["objection_raised", "agreement_reached"],
            current_stage=SalesStage.NEGOTIATION,
        )
        assert result == SalesStage.CLOSE  # Agreement wins

    def test_suggest_transition_no_matching_signals(self):
        """Test suggestion with no matching signals."""
        sm = SalesStageStateMachine()
        result = sm.suggest_transition(["unknown_signal"])
        assert result is None

        result = sm.suggest_transition([])
        assert result is None

    def test_transition_history_tracking(self):
        """Test transition history is tracked correctly."""
        sm = SalesStageStateMachine()

        # Perform multiple transitions
        sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY, "replied")
        sm.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION, "needs_found")
        sm.transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION, "pricing")

        assert len(sm.transition_history) == 3

        # Verify order
        assert sm.transition_history[0].from_stage == SalesStage.NEW_CONTACT
        assert sm.transition_history[1].from_stage == SalesStage.DISCOVERY
        assert sm.transition_history[2].from_stage == SalesStage.PRESENTATION

    def test_get_transition_count(self):
        """Test transition count methods."""
        sm = SalesStageStateMachine()

        sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        sm.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        sm.transition(SalesStage.PRESENTATION, SalesStage.LOST)

        assert sm.get_transition_count() == 3
        assert sm.get_transition_count(to_stage=SalesStage.LOST) == 1
        assert sm.get_transition_count(to_stage=SalesStage.CLOSE) == 0

    def test_get_last_transition(self):
        """Test getting last transition."""
        sm = SalesStageStateMachine()

        assert sm.get_last_transition() is None

        sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        last = sm.get_last_transition()
        assert last is not None
        assert last.to_stage == SalesStage.DISCOVERY

        sm.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        last = sm.get_last_transition()
        assert last is not None
        assert last.to_stage == SalesStage.PRESENTATION

    def test_clear_history(self):
        """Test clearing transition history."""
        sm = SalesStageStateMachine()

        sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        assert len(sm.transition_history) == 1

        sm.clear_history()
        assert len(sm.transition_history) == 0

    def test_is_terminal_stage(self):
        """Test terminal stage detection."""
        sm = SalesStageStateMachine()

        assert not sm.is_terminal_stage(SalesStage.NEW_CONTACT)
        assert not sm.is_terminal_stage(SalesStage.DISCOVERY)
        assert not sm.is_terminal_stage(SalesStage.PRESENTATION)
        assert not sm.is_terminal_stage(SalesStage.NEGOTIATION)
        assert sm.is_terminal_stage(SalesStage.CLOSE)
        assert sm.is_terminal_stage(SalesStage.LOST)

    def test_get_valid_triggers(self):
        """Test getting valid triggers for transitions."""
        sm = SalesStageStateMachine()

        triggers = sm.get_valid_triggers(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
        )
        assert "customer_replied" in triggers
        assert "meeting_scheduled" in triggers

        # No triggers for invalid transition
        triggers = sm.get_valid_triggers(SalesStage.CLOSE, SalesStage.NEW_CONTACT)
        assert triggers == []


class TestTransitionRules:
    """Test transition rules and signals."""

    def test_transition_rules_exist(self):
        """Test transition rules are defined."""
        assert len(TRANSITION_RULES) > 0

        # Check specific rules exist
        assert (SalesStage.NEW_CONTACT, SalesStage.DISCOVERY) in TRANSITION_RULES
        assert (SalesStage.NEGOTIATION, SalesStage.CLOSE) in TRANSITION_RULES

    def test_get_transition_rule(self):
        """Test getting transition rules."""
        rule = get_transition_rule(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        assert rule is not None
        assert rule.from_stage == SalesStage.NEW_CONTACT
        assert rule.to_stage == SalesStage.DISCOVERY
        assert rule.transition_type == TransitionType.PROGRESSION

    def test_signal_to_stage_mapping(self):
        """Test signal to stage mapping."""
        assert SIGNAL_TO_STAGE["customer_shows_interest"] == SalesStage.DISCOVERY
        assert SIGNAL_TO_STAGE["needs_identified"] == SalesStage.PRESENTATION
        assert SIGNAL_TO_STAGE["agreement_reached"] == SalesStage.CLOSE

    def test_positive_signals_defined(self):
        """Test positive signals are defined."""
        assert "customer_replied" in POSITIVE_SIGNALS
        assert "agreement_reached" in POSITIVE_SIGNALS
        assert "needs_identified" in POSITIVE_SIGNALS

    def test_negative_signals_defined(self):
        """Test negative signals are defined."""
        assert "customer_declined" in NEGATIVE_SIGNALS
        assert "no_budget" in NEGATIVE_SIGNALS
        assert "competitor_chosen" in NEGATIVE_SIGNALS

    def test_get_signal_definition(self):
        """Test getting signal definitions."""
        signal = get_signal_definition("customer_replied")
        assert signal is not None
        assert signal.name == "customer_replied"
        assert signal.category == SignalCategory.POSITIVE

        signal = get_signal_definition("customer_declined")
        assert signal is not None
        assert signal.category == SignalCategory.NEGATIVE

        signal = get_signal_definition("nonexistent_signal")
        assert signal is None

    def test_get_all_signals(self):
        """Test getting all signals."""
        all_signals = get_all_signals()
        assert len(all_signals) > 0
        assert "customer_replied" in all_signals
        assert "customer_declined" in all_signals

    def test_get_signals_by_category(self):
        """Test filtering signals by category."""
        positive = get_signals_by_category(SignalCategory.POSITIVE)
        assert all(s.category == SignalCategory.POSITIVE for s in positive.values())

        negative = get_signals_by_category(SignalCategory.NEGATIVE)
        assert all(s.category == SignalCategory.NEGATIVE for s in negative.values())

    def test_evaluate_transition_success(self):
        """Test successful transition evaluation."""
        should_transition, reason = evaluate_transition(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            ["customer_shows_interest"],
        )
        assert should_transition is True

    def test_evaluate_transition_blocked(self):
        """Test blocked transition evaluation."""
        should_transition, reason = evaluate_transition(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            ["customer_shows_interest", "customer_declined"],  # Blocking signal
        )
        assert should_transition is False
        assert "Blocked" in reason

    def test_evaluate_transition_missing_required(self):
        """Test transition evaluation with missing required signals."""
        should_transition, reason = evaluate_transition(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            ["unknown_signal"],  # No required signals
        )
        assert should_transition is False
        assert "Missing required signals" in reason

    def test_evaluate_transition_no_rule(self):
        """Test transition evaluation with no rule."""
        should_transition, reason = evaluate_transition(
            SalesStage.CLOSE,
            SalesStage.NEW_CONTACT,  # No rule for this transition
            [],
        )
        assert should_transition is False
        assert "No transition rule" in reason


class TestTransitionTriggers:
    """Test transition triggers."""

    def test_transition_triggers_defined(self):
        """Test transition triggers are defined."""
        assert len(TRANSITION_TRIGGERS) > 0

        # Check specific triggers
        key = (SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        assert key in TRANSITION_TRIGGERS
        assert "customer_replied" in TRANSITION_TRIGGERS[key]

    def test_loss_transition_triggers(self):
        """Test loss transition triggers."""
        # NEW_CONTACT → LOST
        key = (SalesStage.NEW_CONTACT, SalesStage.LOST)
        assert key in TRANSITION_TRIGGERS
        assert "no_response" in TRANSITION_TRIGGERS[key]
        assert "wrong_contact" in TRANSITION_TRIGGERS[key]


class TestConversationSignal:
    """Test ConversationSignal dataclass."""

    def test_signal_creation(self):
        """Test creating a conversation signal."""
        signal = ConversationSignal(
            name="test_signal",
            category=SignalCategory.POSITIVE,
            confidence=0.9,
            evidence="Customer said yes",
            metadata={"source": "chat"},
        )
        assert signal.name == "test_signal"
        assert signal.category == SignalCategory.POSITIVE
        assert signal.confidence == 0.9
        assert signal.evidence == "Customer said yes"
        assert signal.metadata["source"] == "chat"

    def test_signal_default_values(self):
        """Test signal with default values."""
        signal = ConversationSignal(
            name="test_signal",
            category=SignalCategory.NEUTRAL,
            confidence=0.5,
        )
        assert signal.evidence == ""
        assert signal.metadata == {}


class TestTransitionRule:
    """Test TransitionRule dataclass."""

    def test_rule_creation(self):
        """Test creating a transition rule."""
        rule = TransitionRule(
            from_stage=SalesStage.NEW_CONTACT,
            to_stage=SalesStage.DISCOVERY,
            transition_type=TransitionType.PROGRESSION,
            required_signals=["customer_replied"],
            blocking_signals=["customer_declined"],
            confidence_threshold=0.7,
            description="Test rule",
        )
        assert rule.from_stage == SalesStage.NEW_CONTACT
        assert rule.to_stage == SalesStage.DISCOVERY
        assert rule.transition_type == TransitionType.PROGRESSION
        assert "customer_replied" in rule.required_signals
        assert "customer_declined" in rule.blocking_signals
        assert rule.confidence_threshold == 0.7

    def test_rule_default_values(self):
        """Test rule with default values."""
        rule = TransitionRule(
            from_stage=SalesStage.NEW_CONTACT,
            to_stage=SalesStage.DISCOVERY,
            transition_type=TransitionType.PROGRESSION,
        )
        assert rule.required_signals == []
        assert rule.blocking_signals == []
        assert rule.confidence_threshold == 0.7
        assert rule.description == ""


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_rapid_transitions(self):
        """Test multiple rapid transitions."""
        sm = SalesStageStateMachine()

        # Perform full pipeline
        sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        sm.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        sm.transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION)
        sm.transition(SalesStage.NEGOTIATION, SalesStage.CLOSE)

        assert len(sm.transition_history) == 4
        assert sm.get_last_transition().to_stage == SalesStage.CLOSE

    def test_transition_to_lost_from_all_stages(self):
        """Test that LOST is reachable from all non-terminal stages."""
        sm = SalesStageStateMachine()

        for stage in [
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            SalesStage.PRESENTATION,
            SalesStage.NEGOTIATION,
        ]:
            assert sm.can_transition(stage, SalesStage.LOST)

    def test_empty_signal_list(self):
        """Test behavior with empty signal list."""
        sm = SalesStageStateMachine()
        result = sm.suggest_transition([])
        assert result is None

    def test_multiple_valid_signals(self):
        """Test behavior with multiple valid signals."""
        sm = SalesStageStateMachine()

        # Multiple progression signals
        result = sm.suggest_transition(
            [
                "customer_shows_interest",
                "needs_identified",
                "objection_raised",
            ]
        )
        # Should return highest priority (agreement_reached would be CLOSE, but not present)
        # objection_raised → NEGOTIATION is priority
        assert result == SalesStage.NEGOTIATION

    def test_stage_enum_comparison(self):
        """Test stage enum comparison."""
        assert SalesStage.NEW_CONTACT == SalesStage.NEW_CONTACT
        assert SalesStage.NEW_CONTACT != SalesStage.DISCOVERY
        assert SalesStage.NEW_CONTACT.value == "new_contact"

    def test_transition_with_low_confidence(self):
        """Test transition evaluation with low confidence signals."""
        should_transition, reason = evaluate_transition(
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            ["customer_shows_interest"],
            signal_confidences={"customer_shows_interest": 0.3},  # Below threshold
        )
        # Should fail due to low confidence
        assert should_transition is False
