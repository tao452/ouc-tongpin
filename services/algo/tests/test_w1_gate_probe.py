def test_w1_deliberate_failure():
    """Isolated W1 quality-gate experiment. This branch is never merged."""
    raise AssertionError("W1_GATE_PROBE: deliberate test failure")
