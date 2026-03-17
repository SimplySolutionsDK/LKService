from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from typing import List, Dict, Any
import uuid
import json
from datetime import datetime

from app.models.schemas import EmployeeType, ProcessingResult, DailyOutput, PeriodSummary, DayType, DailyRecord
from app.services.csv_parser import parse_csv_file
from app.services.time_calculator import process_records_with_segments
from app.services.overtime_calculator import (
    process_all_records,
    apply_credited_hours,
    apply_half_sick_day,
    recalculate_period_summaries,
    get_credited_hours_for_day,
)
from app.services.csv_generator import (
    generate_daily_csv,
    generate_period_summary_csv,
    generate_combined_csv,
    generate_detailed_daily_csv,
    generate_detailed_period_summary_csv,
)
from app.services.call_out_detector import mark_call_out_eligibility, get_call_out_eligible_days, apply_call_out_payment
from app.services.absence_detector import mark_absence_types
from app.services.date_filler import fill_missing_dates


router = APIRouter(prefix="/api", tags=["upload"])

# In-memory storage for preview data (keyed by session ID).
# Other routers (e.g. Danløn sync) may import this directly.
preview_cache: Dict[str, Dict[str, Any]] = {}


def _build_preview_response(
    session_id: str,
    outputs: list,
    summaries: list,
    call_out_eligible_days: list,
) -> dict:
    """Build the standard preview JSON response dict."""
    daily_data = []
    for output in outputs:
        output_dict = output.model_dump()
        for entry in output_dict.get('entries', []):
            if 'start_time' in entry and entry['start_time']:
                entry['start_time'] = entry['start_time'].strftime('%H:%M') if hasattr(entry['start_time'], 'strftime') else str(entry['start_time'])
            if 'end_time' in entry and entry['end_time']:
                entry['end_time'] = entry['end_time'].strftime('%H:%M') if hasattr(entry['end_time'], 'strftime') else str(entry['end_time'])
        daily_data.append(output_dict)

    periods_data = [s.model_dump() for s in summaries]

    return {
        "success": True,
        "session_id": session_id,
        "daily": daily_data,
        "periods": periods_data,
        "call_out_eligible_days": call_out_eligible_days,
        "total_records": len(outputs),
        "total_periods": len(summaries),
    }


@router.post("/upload", response_model=ProcessingResult)
async def upload_csv_files(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend"),
    output_format: str = Form(default="daily")
):
    """Upload and process time registration CSV files."""
    try:
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV,
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)

        all_records = []
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
            content = await file.read()
            records = parse_csv_file(content)
            all_records.extend(records)

        if not all_records:
            return ProcessingResult(
                success=False,
                message="No valid CSV data found in uploaded files",
                records_processed=0,
            )

        all_records = process_records_with_segments(all_records)
        all_records = mark_absence_types(all_records)
        all_records = apply_credited_hours(all_records)
        summaries, outputs = process_all_records(all_records, emp_type)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"time_registration_{timestamp}.csv"

        return ProcessingResult(
            success=True,
            message=f"Successfully processed {len(files)} file(s) with {len(outputs)} daily records",
            output_filename=output_filename,
            records_processed=len(outputs),
        )

    except Exception as e:
        return ProcessingResult(
            success=False,
            message=f"Error processing files: {str(e)}",
            records_processed=0,
        )


@router.post("/preview")
async def preview_data(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend")
):
    """Process CSV files and return preview data as JSON."""
    try:
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV,
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)

        all_records = []
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
            content = await file.read()
            records = parse_csv_file(content)
            all_records.extend(records)

        if not all_records:
            raise HTTPException(status_code=400, detail="No valid CSV data found in uploaded files")

        all_records = process_records_with_segments(all_records)
        all_records = mark_call_out_eligibility(all_records)
        all_records = mark_absence_types(all_records)
        all_records = apply_credited_hours(all_records)
        summaries, outputs = process_all_records(all_records, emp_type)
        outputs = fill_missing_dates(outputs)

        call_out_eligible_days = get_call_out_eligible_days(all_records)
        session_id = str(uuid.uuid4())

        preview_cache[session_id] = {
            "records": all_records,
            "outputs": outputs,
            "summaries": summaries,
            "call_out_eligible_days": call_out_eligible_days,
            "overtime_overrides": {},
            "timestamp": datetime.now(),
        }

        _cleanup_old_sessions()

        return JSONResponse(content=_build_preview_response(
            session_id, outputs, summaries, call_out_eligible_days
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


@router.post("/export/{session_id}")
async def export_from_preview(
    session_id: str,
    output_format: str = Form(default="daily"),
    call_out_selections: str = Form(default="{}"),
):
    """Export previously previewed data to CSV."""
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found. Please upload files again.")

    cached = preview_cache[session_id]
    outputs = cached["outputs"]
    summaries = cached["summaries"]
    records = cached.get("records", None)

    try:
        call_out_dict = json.loads(call_out_selections)
    except json.JSONDecodeError:
        call_out_dict = {}

    # Apply overtime overrides to summaries before export
    overrides = cached.get("overtime_overrides", {})
    if overrides:
        summaries = _apply_overtime_overrides_to_summaries(summaries, overrides)

    # Apply aggregate stats overrides before export
    stats_overrides = cached.get("stats_overrides", {})
    if stats_overrides:
        summaries = _apply_stats_overrides_to_summaries(summaries, stats_overrides)

    outputs = apply_call_out_payment(outputs, call_out_dict, records)

    if output_format == "period":
        csv_content = generate_period_summary_csv(summaries)
        filename = "period_summary.csv"
    elif output_format == "period_detailed":
        csv_content = generate_detailed_period_summary_csv(summaries)
        filename = "period_summary_detailed.csv"
    elif output_format == "combined":
        csv_content = generate_combined_csv(outputs, summaries)
        filename = "time_registration_combined.csv"
    elif output_format == "detailed":
        csv_content = generate_detailed_daily_csv(outputs)
        filename = "time_registration_detailed.csv"
    else:
        csv_content = generate_daily_csv(outputs)
        filename = "time_registration_daily.csv"

    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/mark-absence/{session_id}")
async def mark_absence(
    session_id: str,
    absence_selections: str = Form(default="{}"),
):
    """Apply absence types to empty days and recalculate hours."""
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found. Please upload files again.")

    cached = preview_cache[session_id]
    all_records = cached["records"]

    try:
        absence_dict = json.loads(absence_selections)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid absence selections format")

    from app.models.schemas import AbsentType
    absent_type_map = {
        "Vacation": AbsentType.VACATION,
        "Sick": AbsentType.SICK,
        "Kursus": AbsentType.KURSUS,
        "None": AbsentType.NONE,
    }

    records_by_date = {r.date.strftime("%d-%m-%Y"): r for r in all_records}

    for date_str, absence_type_str in absence_dict.items():
        if absence_type_str not in absent_type_map:
            continue
        absence_type = absent_type_map[absence_type_str]

        if date_str in records_by_date:
            record = records_by_date[date_str]
            if len(record.entries) == 0:
                record.absent_type = absence_type
        else:
            from datetime import date as date_type
            date_parts = date_str.split('-')
            if len(date_parts) == 3:
                day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                record_date = date_type(year, month, day)
                weekday = record_date.weekday()
                day_type = DayType.SATURDAY if weekday == 5 else (DayType.SUNDAY if weekday == 6 else DayType.WEEKDAY)
                worker_name = all_records[0].worker_name if all_records else "Unknown"

                new_record = DailyRecord(
                    worker_name=worker_name,
                    date=record_date,
                    day_name=record_date.strftime('%A'),
                    day_type=day_type,
                    week_number=record_date.isocalendar()[1],
                    entries=[],
                    total_hours=0.0,
                    absent_type=absence_type,
                )
                all_records.append(new_record)
                records_by_date[date_str] = new_record

    all_records = process_records_with_segments(all_records)
    all_records = mark_call_out_eligibility(all_records)
    all_records = mark_absence_types(all_records)
    all_records = apply_credited_hours(all_records)
    summaries, outputs = process_all_records(all_records)
    outputs = fill_missing_dates(outputs)
    call_out_eligible_days = get_call_out_eligible_days(all_records)

    preview_cache[session_id]["records"] = all_records
    preview_cache[session_id]["outputs"] = outputs
    preview_cache[session_id]["summaries"] = summaries
    preview_cache[session_id]["call_out_eligible_days"] = call_out_eligible_days

    return JSONResponse(content=_build_preview_response(
        session_id, outputs, summaries, call_out_eligible_days
    ))


@router.post("/half-sick-day/{session_id}")
async def apply_half_sick_day_endpoint(
    session_id: str,
    date: str = Form(...),
):
    """
    Apply a half sick day top-up to a specific date.

    Adds credited sick hours so the day total equals the full daily norm.
    For example: 4h worked on Monday → adds 3.5h sick so day = 7.5h.

    Args:
        session_id: Session ID from preview
        date: Date in DD-MM-YYYY format
    """
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found. Please upload files again.")

    cached = preview_cache[session_id]
    all_records = cached["records"]

    records_by_date = {r.date.strftime("%d-%m-%Y"): r for r in all_records}

    if date not in records_by_date:
        raise HTTPException(status_code=404, detail=f"No record found for date {date}")

    target_record = records_by_date[date]

    if target_record.day_type != DayType.WEEKDAY:
        raise HTTPException(status_code=400, detail="Half sick day can only be applied to weekdays")

    if len(target_record.entries) == 0:
        raise HTTPException(
            status_code=400,
            detail="Half sick day requires actual work entries. Use full absence marking for empty days."
        )

    # Apply half sick day top-up
    target_record = apply_half_sick_day(target_record)

    # Recalculate the full pipeline
    all_records = process_records_with_segments(all_records)
    all_records = mark_call_out_eligibility(all_records)
    all_records = apply_credited_hours(all_records)
    summaries, outputs = process_all_records(all_records)
    outputs = fill_missing_dates(outputs)
    call_out_eligible_days = get_call_out_eligible_days(all_records)

    # Track the half sick day top-up hours in the daily output
    daily_norm = get_credited_hours_for_day(target_record.date.weekday())
    half_sick_applied = max(0.0, daily_norm - (target_record.total_hours - target_record.credited_hours))
    for out in outputs:
        if out.date == date:
            out.half_sick_hours = round(half_sick_applied, 2)

    preview_cache[session_id]["records"] = all_records
    preview_cache[session_id]["outputs"] = outputs
    preview_cache[session_id]["summaries"] = summaries
    preview_cache[session_id]["call_out_eligible_days"] = call_out_eligible_days

    return JSONResponse(content=_build_preview_response(
        session_id, outputs, summaries, call_out_eligible_days
    ))


@router.post("/overtime-overrides/{session_id}")
async def save_overtime_overrides(
    session_id: str,
    overrides: str = Form(default="{}"),
):
    """
    Store user-supplied overtime override values for period summaries.

    These are applied at export time so the user can correct calculated values
    before sending downstream.

    Args:
        session_id: Session ID from preview
        overrides: JSON string mapping period keys to override field values.
            Format: { "WorkerName__2026__3": { "overtime_1": 2.0, "ot_weekend": 4.5 } }
    """
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found.")

    try:
        overrides_dict = json.loads(overrides)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid overrides format")

    preview_cache[session_id]["overtime_overrides"] = overrides_dict

    return JSONResponse(content={"success": True})


@router.post("/stats-overrides/{session_id}")
async def save_stats_overrides(
    session_id: str,
    overrides: str = Form(default="{}"),
):
    """
    Store user-supplied aggregate stats override values.

    These are applied at export time so the user can correct calculated totals
    before sending downstream. The override is distributed across periods so the
    exported totals match the user-supplied values.

    Args:
        session_id: Session ID from preview
        overrides: JSON string with optional keys: ot1, ot2, ot3, ot_weekend, normal_hours
            Format: { "ot1": 4.0, "ot3": 2.5 }
    """
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found.")

    try:
        overrides_dict = json.loads(overrides)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid overrides format")

    preview_cache[session_id]["stats_overrides"] = overrides_dict

    return JSONResponse(content={"success": True})


@router.post("/process")
async def process_and_download(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend"),
    output_format: str = Form(default="daily"),
):
    """Process CSV files and return the resulting CSV as a download."""
    try:
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV,
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)

        all_records = []
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
            content = await file.read()
            records = parse_csv_file(content)
            all_records.extend(records)

        if not all_records:
            raise HTTPException(status_code=400, detail="No valid CSV data found in uploaded files")

        all_records = process_records_with_segments(all_records)
        all_records = mark_absence_types(all_records)
        all_records = apply_credited_hours(all_records)
        summaries, outputs = process_all_records(all_records, emp_type)
        outputs = fill_missing_dates(outputs)

        if output_format == "period":
            csv_content = generate_period_summary_csv(summaries)
            filename = "period_summary.csv"
        elif output_format == "period_detailed":
            csv_content = generate_detailed_period_summary_csv(summaries)
            filename = "period_summary_detailed.csv"
        elif output_format == "combined":
            csv_content = generate_combined_csv(outputs, summaries)
            filename = "time_registration_combined.csv"
        elif output_format == "detailed":
            csv_content = generate_detailed_daily_csv(outputs)
            filename = "time_registration_detailed.csv"
        else:
            csv_content = generate_daily_csv(outputs)
            filename = "time_registration_daily.csv"

        return Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_old_sessions():
    current_time = datetime.now()
    expired_keys = [
        key for key, value in preview_cache.items()
        if (current_time - value["timestamp"]).seconds > 3600
    ]
    for key in expired_keys:
        del preview_cache[key]


def _apply_overtime_overrides_to_summaries(
    summaries: list,
    overrides: dict,
) -> list:
    """
    Apply user-supplied overtime override values to period summaries before export.

    Override key format: "{worker_name}__{year}__{period_number}"
    """
    result = []
    for summary in summaries:
        key = f"{summary.worker_name}__{summary.year}__{summary.period_number}"
        if key in overrides:
            ov = overrides[key]
            if "overtime_1" in ov:
                summary.overtime_1 = float(ov["overtime_1"])
            if "overtime_2" in ov:
                summary.overtime_2 = float(ov["overtime_2"])
            if "overtime_3" in ov:
                summary.overtime_3 = float(ov["overtime_3"])
            if "ot_weekend" in ov:
                summary.overtime_breakdown.ot_weekend = float(ov["ot_weekend"])
        result.append(summary)
    return result


def _apply_stats_overrides_to_summaries(
    summaries: list,
    stats_overrides: dict,
) -> list:
    """
    Apply user-supplied aggregate stats overrides to period summaries before export.

    The override values replace the totals across all periods. The delta between the
    overridden total and the calculated total is applied to the first period that has
    a non-zero value in the relevant field.

    Supported keys: ot1, ot2, ot3, ot_weekend, normal_hours
    """
    if not summaries:
        return summaries

    def _calc_total(field: str) -> float:
        total = 0.0
        for s in summaries:
            if field == "ot1":
                total += s.overtime_breakdown.ot_weekday_hour_1_2
            elif field == "ot2":
                total += s.overtime_breakdown.ot_weekday_hour_3_4
            elif field == "ot3":
                total += (
                    s.overtime_breakdown.ot_weekday_hour_5_plus
                    + s.overtime_breakdown.ot_dayoff_day
                    + s.overtime_breakdown.ot_dayoff_night
                )
            elif field == "ot_weekend":
                total += s.overtime_breakdown.ot_weekend
            elif field == "normal_hours":
                total += s.normal_hours
        return total

    field_map = {
        "ot1": ("overtime_1", None),
        "ot2": ("overtime_2", None),
        "ot3": ("overtime_3", None),
        "ot_weekend": (None, "ot_weekend"),
        "normal_hours": ("normal_hours", None),
    }

    for override_key, (summary_attr, breakdown_attr) in field_map.items():
        if override_key not in stats_overrides:
            continue

        target_total = float(stats_overrides[override_key])
        current_total = _calc_total(override_key)
        delta = target_total - current_total

        if abs(delta) < 1e-9:
            continue

        # Apply delta to the first period with a non-zero value, or the first period if all zero
        target_summary = None
        for s in summaries:
            if summary_attr and getattr(s, summary_attr, 0) > 0:
                target_summary = s
                break
            if breakdown_attr and getattr(s.overtime_breakdown, breakdown_attr, 0) > 0:
                target_summary = s
                break
        if target_summary is None:
            target_summary = summaries[0]

        if summary_attr:
            current_val = getattr(target_summary, summary_attr, 0.0)
            setattr(target_summary, summary_attr, max(0.0, current_val + delta))
        if breakdown_attr:
            current_val = getattr(target_summary.overtime_breakdown, breakdown_attr, 0.0)
            setattr(target_summary.overtime_breakdown, breakdown_attr, max(0.0, current_val + delta))

    return summaries
