"""Turn applications into a CSV download."""

import csv
import io
from collections.abc import Iterable, Iterator

from app.models import Application
from app.services.presenters import to_application_out

CSV_COLUMNS = ["Candidate name", "Email", "Job", "Status", "Prediction", "Probability", "Created date"]
# Excel needs this mark to read the file as UTF-8, or accented names come out garbled.
UTF8_BOM = "﻿"
# A spreadsheet runs a cell starting with one of these as a formula.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str) -> str:
    """Stop text typed into the portal from running as a formula when the file is opened."""
    return f"'{value}" if value.startswith(FORMULA_PREFIXES) else value


def to_csv_rows(applications: Iterable[Application]) -> list[list[str]]:
    """Read everything now. The database session closes before the response is streamed."""
    rows = []
    for application in applications:
        out = to_application_out(application)
        rows.append(
            [
                _safe_cell(out.candidate_name),
                _safe_cell(out.candidate_email),
                _safe_cell(out.job_title),
                out.status,
                out.prediction.label if out.prediction else "Unavailable",
                f"{out.prediction.probability:.4f}" if out.prediction else "",
                out.created_at.date().isoformat(),
            ]
        )
    return rows


def stream_csv(rows: list[list[str]]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    yield UTF8_BOM + buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate()
        writer.writerow(row)
        yield buffer.getvalue()
