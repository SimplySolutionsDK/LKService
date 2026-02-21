from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from typing import List, Dict, Any
import uuid
import json
from datetime import datetime

from app.models.schemas import EmployeeType, ProcessingResult, DailyOutput, WeeklySummary, DayType, DailyRecord
from app.services.csv_parser import parse_csv_file
from app.services.time_calculator import process_records_with_segments
from app.services.overtime_calculator import process_all_records, apply_credited_hours
from app.services.csv_generator import (
    generate_daily_csv, 
    generate_weekly_summary_csv, 
    generate_combined_csv,
    generate_detailed_daily_csv,
    generate_detailed_weekly_summary_csv
)
from app.services.call_out_detector import mark_call_out_eligibility, get_call_out_eligible_days, apply_call_out_payment
from app.services.absence_detector import mark_absence_types
from app.services.date_filler import fill_missing_dates


router = APIRouter(prefix="/api", tags=["upload"])

# In-memory storage for preview data (keyed by session ID).
# Other routers (e.g. Danløn sync) may import this directly.
preview_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=ProcessingResult)
async def upload_csv_files(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend"),
    output_format: str = Form(default="daily")
):
    """
    Upload and process time registration CSV files.
    
    Args:
        files: List of CSV files to process
        employee_type: Employee type for overtime calculation (Lærling, Svend, Funktionær, Elev)
        output_format: Output format - 'daily', 'weekly', or 'combined'
        
    Returns:
        ProcessingResult with success status and output filename
    """
    try:
        # Map employee type string to enum
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)
        
        all_records = []
        
        # Process each uploaded file
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
                records_processed=0
            )
        
        # Calculate time segments
        all_records = process_records_with_segments(all_records)
        
        # Detect and mark absence types (vacation/sick/holiday)
        all_records = mark_absence_types(all_records)
        
        # Apply credited hours for vacation/sick/holiday
        all_records = apply_credited_hours(all_records)
        
        # Calculate overtime
        summaries, outputs = process_all_records(all_records, emp_type)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"time_registration_{timestamp}.csv"
        
        return ProcessingResult(
            success=True,
            message=f"Successfully processed {len(files)} file(s) with {len(outputs)} daily records",
            output_filename=output_filename,
            records_processed=len(outputs)
        )
        
    except Exception as e:
        return ProcessingResult(
            success=False,
            message=f"Error processing files: {str(e)}",
            records_processed=0
        )


@router.post("/preview")
async def preview_data(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend")
):
    """
    Process CSV files and return preview data as JSON.
    
    Args:
        files: List of CSV files to process
        employee_type: Employee type for overtime calculation
        
    Returns:
        JSON with daily and weekly data for preview
    """
    try:
        # Map employee type string to enum
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)
        
        all_records = []
        
        # Process each uploaded file
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
            
            content = await file.read()
            records = parse_csv_file(content)
            all_records.extend(records)
        
        if not all_records:
            raise HTTPException(status_code=400, detail="No valid CSV data found in uploaded files")
        
        # Calculate time segments
        all_records = process_records_with_segments(all_records)
        
        # Mark call out eligibility
        all_records = mark_call_out_eligibility(all_records)
        
        # Detect and mark absence types (vacation/sick/holiday)
        all_records = mark_absence_types(all_records)
        
        # Apply credited hours for vacation/sick/holiday
        all_records = apply_credited_hours(all_records)
        
        # Calculate overtime
        summaries, outputs = process_all_records(all_records, emp_type)
        
        # Fill in missing dates per worker
        outputs = fill_missing_dates(outputs)
        
        # Get call out eligible days information
        call_out_eligible_days = get_call_out_eligible_days(all_records)
        
        # Generate session ID for caching
        session_id = str(uuid.uuid4())
        
        # Convert to dictionaries for JSON response
        daily_data = []
        for output in outputs:
            output_dict = output.model_dump()
            # Convert time objects to strings in entries
            for entry in output_dict.get('entries', []):
                if 'start_time' in entry and entry['start_time']:
                    entry['start_time'] = entry['start_time'].strftime('%H:%M') if hasattr(entry['start_time'], 'strftime') else str(entry['start_time'])
                if 'end_time' in entry and entry['end_time']:
                    entry['end_time'] = entry['end_time'].strftime('%H:%M') if hasattr(entry['end_time'], 'strftime') else str(entry['end_time'])
            daily_data.append(output_dict)
        
        weekly_data = [summary.model_dump() for summary in summaries]
        
        # Cache the processed data for later export
        preview_cache[session_id] = {
            "records": all_records,  # Store original DailyRecords for re-processing
            "outputs": outputs,
            "summaries": summaries,
            "call_out_eligible_days": call_out_eligible_days,
            "timestamp": datetime.now()
        }
        
        # Clean up old cache entries (older than 1 hour)
        current_time = datetime.now()
        expired_keys = [
            key for key, value in preview_cache.items()
            if (current_time - value["timestamp"]).seconds > 3600
        ]
        for key in expired_keys:
            del preview_cache[key]
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "daily": daily_data,
            "weekly": weekly_data,
            "call_out_eligible_days": call_out_eligible_days,
            "total_records": len(outputs),
            "total_weeks": len(summaries)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


@router.post("/export/{session_id}")
async def export_from_preview(
    session_id: str,
    output_format: str = Form(default="daily"),
    call_out_selections: str = Form(default="{}")
):
    """
    Export previously previewed data to CSV.
    
    Args:
        session_id: Session ID from preview
        output_format: Output format - 'daily', 'weekly', or 'combined'
        call_out_selections: JSON string mapping dates to boolean for call out payment
        
    Returns:
        CSV file download
    """
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found. Please upload files again.")
    
    cached = preview_cache[session_id]
    outputs = cached["outputs"]
    summaries = cached["summaries"]
    records = cached.get("records", None)  # Get original DailyRecords
    
    # Parse call out selections
    try:
        call_out_dict = json.loads(call_out_selections)
    except json.JSONDecodeError:
        call_out_dict = {}
    
    # Apply call out payment to selected days with overtime recalculation
    outputs = apply_call_out_payment(outputs, call_out_dict, records)
    
    # Generate CSV based on format
    if output_format == "weekly":
        csv_content = generate_weekly_summary_csv(summaries)
        filename = "weekly_summary.csv"
    elif output_format == "weekly_detailed":
        csv_content = generate_detailed_weekly_summary_csv(summaries)
        filename = "weekly_summary_detailed.csv"
    elif output_format == "combined":
        csv_content = generate_combined_csv(outputs, summaries)
        filename = "time_registration_combined.csv"
    elif output_format == "detailed":
        csv_content = generate_detailed_daily_csv(outputs)
        filename = "time_registration_detailed.csv"
    else:
        csv_content = generate_daily_csv(outputs)
        filename = "time_registration_daily.csv"
    
    # Return as downloadable file
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/mark-absence/{session_id}")
async def mark_absence(
    session_id: str,
    absence_selections: str = Form(default="{}")
):
    """
    Apply absence types to empty days and recalculate hours.
    
    This endpoint re-runs the full overtime calculation pipeline with absence types applied,
    ensuring that weekly overtime is correctly distributed across working days.
    
    Args:
        session_id: Session ID from preview
        absence_selections: JSON string mapping dates (DD-MM-YYYY) to absence types
            Example: {"26-01-2026": "Vacation", "27-01-2026": "Sick"}
    
    Returns:
        Updated preview data with credited hours applied and overtime recalculated
    """
    if session_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview session not found. Please upload files again.")
    
    cached = preview_cache[session_id]
    all_records = cached["records"]  # Get original DailyRecords
    
    # Parse absence selections
    try:
        absence_dict = json.loads(absence_selections)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid absence selections format")
    
    # Map string to AbsentType enum
    from app.models.schemas import AbsentType
    absent_type_map = {
        "Vacation": AbsentType.VACATION,
        "Sick": AbsentType.SICK,
        "Kursus": AbsentType.KURSUS,
        "None": AbsentType.NONE
    }
    
    # Create a dict of existing records by date for quick lookup
    # Date format in absence_dict is DD-MM-YYYY
    records_by_date = {}
    for record in all_records:
        date_key = record.date.strftime("%d-%m-%Y")
        records_by_date[date_key] = record
    
    # Apply absence types to records
    for date_str, absence_type_str in absence_dict.items():
        if absence_type_str in absent_type_map:
            absence_type = absent_type_map[absence_type_str]
            
            if date_str in records_by_date:
                # Update existing record
                record = records_by_date[date_str]
                # Only update if the record has no actual time entries
                if len(record.entries) == 0:
                    record.absent_type = absence_type
            else:
                # Create a new record for this date if it doesn't exist
                # Parse the date string (DD-MM-YYYY)
                from datetime import date as date_type
                date_parts = date_str.split('-')
                if len(date_parts) == 3:
                    day = int(date_parts[0])
                    month = int(date_parts[1])
                    year = int(date_parts[2])
                    record_date = date_type(year, month, day)
                    
                    # Determine day type
                    weekday = record_date.weekday()
                    if weekday == 5:
                        day_type = DayType.SATURDAY
                    elif weekday == 6:
                        day_type = DayType.SUNDAY
                    else:
                        day_type = DayType.WEEKDAY
                    
                    # Get worker name from first existing record
                    worker_name = all_records[0].worker_name if all_records else "Unknown"
                    
                    # Create new DailyRecord with absence type
                    new_record = DailyRecord(
                        worker_name=worker_name,
                        date=record_date,
                        day_name=record_date.strftime('%A'),
                        day_type=day_type,
                        week_number=record_date.isocalendar()[1],
                        entries=[],
                        total_hours=0.0,
                        absent_type=absence_type
                    )
                    all_records.append(new_record)
                    records_by_date[date_str] = new_record
    
    # Re-run the full processing pipeline
    from app.services.time_calculator import process_records_with_segments
    from app.services.overtime_calculator import apply_credited_hours, process_all_records
    from app.services.call_out_detector import mark_call_out_eligibility, get_call_out_eligible_days
    from app.services.absence_detector import mark_absence_types
    from app.services.date_filler import fill_missing_dates
    
    # Process with the updated absence types
    all_records = process_records_with_segments(all_records)
    all_records = mark_call_out_eligibility(all_records)
    all_records = mark_absence_types(all_records)
    all_records = apply_credited_hours(all_records)  # This now uses day-specific hours
    
    # Recalculate overtime with the credited hours
    summaries, outputs = process_all_records(all_records)
    
    # Fill in missing dates
    outputs = fill_missing_dates(outputs)
    
    # Get call out eligible days
    call_out_eligible_days = get_call_out_eligible_days(all_records)
    
    # Update cache with new results
    preview_cache[session_id]["records"] = all_records
    preview_cache[session_id]["outputs"] = outputs
    preview_cache[session_id]["summaries"] = summaries
    preview_cache[session_id]["call_out_eligible_days"] = call_out_eligible_days
    
    # Convert to dictionaries for JSON response
    daily_data = []
    for output in outputs:
        output_dict = output.model_dump()
        # Convert time objects to strings in entries
        for entry in output_dict.get('entries', []):
            if 'start_time' in entry and entry['start_time']:
                entry['start_time'] = entry['start_time'].strftime('%H:%M') if hasattr(entry['start_time'], 'strftime') else str(entry['start_time'])
            if 'end_time' in entry and entry['end_time']:
                entry['end_time'] = entry['end_time'].strftime('%H:%M') if hasattr(entry['end_time'], 'strftime') else str(entry['end_time'])
        daily_data.append(output_dict)
    
    weekly_data = [summary.model_dump() for summary in summaries]
    
    return JSONResponse(content={
        "success": True,
        "session_id": session_id,
        "daily": daily_data,
        "weekly": weekly_data,
        "call_out_eligible_days": call_out_eligible_days,
        "total_records": len(outputs),
        "total_weeks": len(summaries)
    })


@router.post("/process")
async def process_and_download(
    files: List[UploadFile] = File(...),
    employee_type: str = Form(default="Svend"),
    output_format: str = Form(default="daily")
):
    """
    Process CSV files and return the resulting CSV as a download.
    
    Args:
        files: List of CSV files to process
        employee_type: Employee type for overtime calculation
        output_format: Output format - 'daily', 'weekly', or 'combined'
        
    Returns:
        CSV file download
    """
    try:
        # Map employee type string to enum
        emp_type_map = {
            "Lærling": EmployeeType.LAERLING,
            "Svend": EmployeeType.SVEND,
            "Funktionær": EmployeeType.FUNKTIONAER,
            "Elev": EmployeeType.ELEV
        }
        emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)
        
        all_records = []
        
        # Process each uploaded file
        for file in files:
            if not file.filename.endswith(".csv"):
                continue
            
            content = await file.read()
            records = parse_csv_file(content)
            all_records.extend(records)
        
        if not all_records:
            raise HTTPException(status_code=400, detail="No valid CSV data found in uploaded files")
        
        # Calculate time segments
        all_records = process_records_with_segments(all_records)
        
        # Detect and mark absence types (vacation/sick/holiday)
        all_records = mark_absence_types(all_records)
        
        # Apply credited hours for vacation/sick/holiday
        all_records = apply_credited_hours(all_records)
        
        # Calculate overtime
        summaries, outputs = process_all_records(all_records, emp_type)
        
        # Fill in missing dates per worker
        outputs = fill_missing_dates(outputs)
        
        # Generate CSV based on format
        if output_format == "weekly":
            csv_content = generate_weekly_summary_csv(summaries)
            filename = "weekly_summary.csv"
        elif output_format == "weekly_detailed":
            csv_content = generate_detailed_weekly_summary_csv(summaries)
            filename = "weekly_summary_detailed.csv"
        elif output_format == "combined":
            csv_content = generate_combined_csv(outputs, summaries)
            filename = "time_registration_combined.csv"
        elif output_format == "detailed":
            csv_content = generate_detailed_daily_csv(outputs)
            filename = "time_registration_detailed.csv"
        else:
            csv_content = generate_daily_csv(outputs)
            filename = "time_registration_daily.csv"
        
        # Return as downloadable file
        return Response(
            content=csv_content.encode("utf-8-sig"),  # UTF-8 with BOM for Excel compatibility
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")
