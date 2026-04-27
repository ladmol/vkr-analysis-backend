from io import BytesIO
from typing import Any

from openpyxl import Workbook

from app.analytics.schemas import AnalyticsQueryResponse, RatingResponse


def analytics_response_to_xlsx(response: AnalyticsQueryResponse) -> bytes:
    rows = [
        [column.label for column in response.columns],
        *[
            [row.get(column.key) for column in response.columns]
            for row in response.rows
        ],
    ]
    return rows_to_xlsx(rows, sheet_name="Report")


def rating_response_to_xlsx(response: RatingResponse) -> bytes:
    headers = [
        "ФИО",
        "Группа",
        "ВУС",
        "Статус",
        "Категория годности",
        "Категория профпригодности",
        "Балл успеваемости",
        "Физподготовка",
        "Итоговый балл",
    ]
    rows: list[list[Any]] = [headers]
    for row in response.rows:
        rows.append(
            [
                row.full_name,
                row.study_group,
                row.military_specialty,
                row.status,
                row.fitness_category,
                row.psycho_category,
                row.grade100,
                row.total_points,
                row.final_result,
            ]
        )
    return rows_to_xlsx(rows, sheet_name="Rating")


def rows_to_xlsx(rows: list[list[Any]], sheet_name: str) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name

    for row in rows:
        worksheet.append(row)

    for column_cells in worksheet.columns:
        max_length = max(
            len(str(cell.value)) if cell.value is not None else 0
            for cell in column_cells
        )
        column_letter = column_cells[0].column_letter
        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 42)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
