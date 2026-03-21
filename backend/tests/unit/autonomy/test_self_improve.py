"""Tests for self-improvement — Bayesian weight adjustment with safeguards."""

from app.application.autonomy.self_improve import SelfImprovementService


class TestSelfImprovement:
    def test_insufficient_samples_rejected(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.6, "b": 0.4},
            sample_counts={"a": 50, "b": 50},
        )
        assert not proposal.approved
        assert "Insufficient" in proposal.reason

    def test_minimum_samples_accepted(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.6, "b": 0.4},
            sample_counts={"a": 100, "b": 100},
        )
        assert proposal.approved

    def test_weights_sum_to_one(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25},
            pillar_accuracy={"a": 0.8, "b": 0.6, "c": 0.4, "d": 0.2},
            sample_counts={"a": 200, "b": 200, "c": 200, "d": 200},
        )
        total = sum(proposal.new_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_max_change_capped(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.99, "b": 0.01},
            sample_counts={"a": 200, "b": 200},
        )
        for pillar in proposal.old_weights:
            change = abs(proposal.new_weights[pillar] - proposal.old_weights[pillar])
            assert change <= 0.10  # post-normalization can shift slightly

    def test_change_log_immutable(self):
        svc = SelfImprovementService()
        svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.6, "b": 0.4},
            sample_counts={"a": 100, "b": 100},
        )
        assert len(svc.change_log) == 1
        log_copy = svc.change_log
        log_copy.clear()
        assert len(svc.change_log) == 1

    def test_zero_accuracy_rejected(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.0, "b": 0.0},
            sample_counts={"a": 100, "b": 100},
        )
        assert not proposal.approved

    def test_shrinkage_keeps_weights_conservative(self):
        svc = SelfImprovementService()
        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.7, "b": 0.3},
            sample_counts={"a": 200, "b": 200},
        )
        assert proposal.new_weights["a"] > 0.5
        assert proposal.new_weights["a"] < 0.7
