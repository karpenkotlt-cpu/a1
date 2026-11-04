"""Динамическое ценообразование (APS): Kmargin по загрузке группы станков.

Docx: U < 40% → 0.4-0.7 (Marginal Costing, простой);
40-80% → 1.0 (Target Costing); 80-95% → 1.25-1.5; > 95% → 1.8-2.5 (Surge).
Узкое место маршрута = max(Ugroup) по всем группам станков маршрута.
"""


def get_dynamic_margin_multiplier(utilization_percent: float) -> float:
    if utilization_percent < 40.0:
        return 0.55
    if utilization_percent <= 80.0:
        return 1.0
    if utilization_percent <= 95.0:
        return 1.35
    return 2.0
