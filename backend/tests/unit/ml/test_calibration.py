"""Tests for calibration evaluation."""

from app.ml.evaluation.calibration import evaluate_calibration


def test_perfectly_calibrated():
    pred = [0.1] * 10 + [0.5] * 10 + [0.9] * 10
    actual = [0] * 9 + [1] * 1 + [0] * 5 + [1] * 5 + [1] * 9 + [0] * 1
    report = evaluate_calibration(pred, actual, n_bins=5)
    assert report.expected_calibration_error < 0.2


def test_overconfident_model():
    pred = [0.9] * 100
    actual = [1] * 50 + [0] * 50
    report = evaluate_calibration(pred, actual, n_bins=5)
    assert not report.is_well_calibrated
