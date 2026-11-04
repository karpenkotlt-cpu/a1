from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Border, Font, PatternFill, Side

from app.domain.dto.calculation import (
    HoleArrayFeature,
    RectPocketFeature,
    StepDTO,
    T1Template,
    T2Template,
    T3Template,
    T5Template,
)
from app.domain.dto.quote import QuoteDetailDTO

TEMPLATE_TITLES = {
    "T1_STEPPED_SHAFT": "Вал ступенчатый (T1)",
    "T2_BUSHING": "Втулка / стакан (T2)",
    "T3_FLANGE": "Фланец / диск (T3)",
    "T4_PLATE": "Плита / блок (T4)",
    "T5_HOUSING": "Корпус (T5)",
}

THIN = Side(style="thin", color="9CA3AF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="E5E7EB")
MONEY_FORMAT = "#,##0.00"


def _steps_text(steps: Sequence[StepDTO]) -> str:
    return " + ".join(f"Ø{step.diameter}×{step.length}" for step in steps)


def _template_rows(detail: QuoteDetailDTO) -> list[tuple[str, object]]:
    template = detail.request.base_template
    rows: list[tuple[str, object]] = [
        ("Шаблон", TEMPLATE_TITLES.get(template.type, template.type))
    ]
    if isinstance(template, T1Template):
        rows.append(("Ступени, мм", _steps_text(template.dimensions.steps)))
    elif isinstance(template, T2Template):
        rows.append(
            ("Наружные ступени, мм", _steps_text(template.dimensions.outer_steps))
        )
        if template.dimensions.inner_steps:
            inner = _steps_text(template.dimensions.inner_steps)
            rows.append(("Расточка, мм", inner))
    elif isinstance(template, T3Template):
        outer = f"{template.dimensions.outer_diameter}×{template.dimensions.thickness}"
        rows.append(("Ø внешний × толщина, мм", outer))
        rows.append(("Ø центральный, мм", template.dimensions.center_hole_diameter))
    elif isinstance(template, T5Template):
        dims5 = template.dimensions
        rows.append(
            (
                "Габариты, мм",
                f"{dims5.length}×{dims5.width}×{dims5.height}",
            )
        )
        rows.append(("Kвыб (доля в стружку)", dims5.removal_ratio))
    else:
        dims4 = template.dimensions
        rows.append(
            (
                "Габариты, мм",
                f"{dims4.length}×{dims4.width}×{dims4.height}",
            )
        )
    return rows


def _feature_rows(detail: QuoteDetailDTO) -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    for feature in detail.request.features:
        if isinstance(feature, HoleArrayFeature):
            through = "сквозные" if feature.is_through else f"гл. {feature.depth}"
            cb = ""
            if feature.counterbore_diameter and feature.counterbore_depth:
                cb = (
                    f", цек. Ø{feature.counterbore_diameter}"
                    f"×{feature.counterbore_depth}"
                )
            thread = f", {feature.thread}" if feature.thread else ""
            rows.append(
                (
                    "Группа отверстий",
                    f"{feature.count}×Ø{feature.diameter} {through} · "
                    f"{feature.tolerance}{thread}{cb}",
                )
            )
        elif isinstance(feature, RectPocketFeature):
            rows.append(
                (
                    "Карман",
                    f"{feature.count}× {feature.length}×{feature.width}"
                    f"×{feature.depth} · {feature.tolerance}",
                )
            )
    return rows


def build_quote_xlsx(detail: QuoteDetailDTO) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Коммерческое предложение"

    sheet.merge_cells("A1:D1")
    title = sheet["A1"]
    title.value = "Коммерческое предложение"
    title.font = Font(bold=True, size=14)
    sheet.merge_cells("A2:D2")
    sheet["A2"].value = detail.name
    sheet["A2"].font = Font(bold=True, size=12)

    row = 4
    meta: list[tuple[str, object]] = [
        ("Дата", detail.created_at.strftime("%d.%m.%Y %H:%M")),
        ("Автор", detail.author_email),
        ("Партия, шт", detail.batch_size),
    ]
    for label, value in meta:
        sheet.cell(row=row, column=1, value=label)
        sheet.cell(row=row, column=2, value=value)
        row += 1

    def section(title: str, rows: list[tuple[str, object]]) -> None:
        nonlocal row
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        header = sheet.cell(row=row, column=1, value=title)
        header.fill = HEADER_FILL
        header.font = HEADER_FONT
        row += 1
        for label, value in rows:
            label_cell = sheet.cell(row=row, column=1, value=label)
            value_cell = sheet.cell(row=row, column=2, value=value)
            label_cell.border = BORDER
            value_cell.border = BORDER
            if isinstance(value, int | float) and "₽" in label:
                value_cell.number_format = MONEY_FORMAT
            row += 1

    section("Деталь", _template_rows(detail) + _feature_rows(detail))

    material = detail.request.material
    section(
        "Материал",
        [
            ("ISO-группа", material.iso_group),
            ("Kq (черновой)", float(material.k_mach_rough)),
            ("Ks (чистовой)", float(material.k_mach_finish)),
            ("Плотность, г/см³", float(material.density_g_cm3)),
            ("Цена, ₽/кг", float(material.cost_per_kg)),
            ("Стружка, ₽/кг", float(material.scrap_price_per_kg)),
        ],
    )
    result_rows: list[tuple[str, object]] = [
        ("Чистая масса, кг", detail.result.m_net_kg),
        ("Масса заготовки, кг", detail.result.m_gross_kg),
        ("Съём Vrem, см³", detail.result.v_removed_cm3),
        ("Материал, ₽/дет", float(detail.result.material_cost)),
        ("Машинное время Tшт, мин", detail.result.machine_time_min),
        ("Наладка Tпз, мин", detail.result.setup_time_min),
    ]
    if detail.result.tool_cost and float(detail.result.tool_cost) > 0:
        result_rows.append(("Инструмент, ₽/дет", float(detail.result.tool_cost)))
    section("Результаты расчёта", result_rows)

    if detail.result.cooperations:
        coop_rows: list[tuple[str, object]] = [
            (
                line.name,
                f"{line.qty} {line.unit} × {line.unit_price} = {line.cost} ₽",
            )
            for line in detail.result.cooperations
        ]
        coop_rows.append(
            ("ИТОГО кооперация, ₽/дет", float(detail.result.cooperation_cost))
        )
        section("Кооперация", coop_rows)
    section(
        "Цена",
        [
            ("Цена за деталь, ₽", float(detail.result.price_per_part)),
            ("ИТОГО за партию, ₽", float(detail.result.batch_total_price)),
        ],
    )
    label_total = sheet.cell(row=row - 1, column=1)
    value_total = sheet.cell(row=row - 1, column=2)
    label_total.fill = TOTAL_FILL
    value_total.fill = TOTAL_FILL
    value_total.font = Font(bold=True, size=12)

    sheet.column_dimensions["A"].width = 32
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 16
    sheet.column_dimensions["D"].width = 16

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
