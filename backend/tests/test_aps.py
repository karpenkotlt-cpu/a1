from app.domain.engine.aps import get_dynamic_margin_multiplier


def test_margin_multiplier_boundaries() -> None:
    # docx: <40% → 0.4-0.7; 40-80% → 1.0; 80-95% → 1.25-1.5; >95% → 1.8-2.5
    assert get_dynamic_margin_multiplier(0.0) == 0.55
    assert get_dynamic_margin_multiplier(39.9) == 0.55
    assert get_dynamic_margin_multiplier(40.0) == 1.0
    assert get_dynamic_margin_multiplier(80.0) == 1.0
    assert get_dynamic_margin_multiplier(80.1) == 1.35
    assert get_dynamic_margin_multiplier(95.0) == 1.35
    assert get_dynamic_margin_multiplier(95.1) == 2.0
    assert get_dynamic_margin_multiplier(100.0) == 2.0
