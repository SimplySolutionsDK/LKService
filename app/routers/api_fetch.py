from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import httpx
import os
import uuid
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.schemas import EmployeeType
from app.services.api_transformer import transform_time_registrations_to_records, get_employee_full_name
from app.services.time_calculator import process_records_with_segments
from app.services.call_out_detector import mark_call_out_eligibility, get_call_out_eligible_days
from app.services.absence_detector import mark_absence_types
from app.services.overtime_calculator import apply_credited_hours, process_all_records
from app.services.date_filler import fill_missing_dates
from app.services.api_auth import get_auth_service


router = APIRouter(prefix="/api", tags=["api-fetch"])
logger = logging.getLogger(__name__)


@router.get("/fetch-employees")
async def fetch_employees():
    """
    Fetch list of employees from the external Core API.
    
    Returns:
        JSON with employee list
    """
    auth_service = get_auth_service()
    
    try:
        # Get authentication token
        token = await auth_service.get_token()
        headers = auth_service.get_headers(token)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{auth_service.core_api_url}/Employee/search?ShowDeleted=false"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return JSONResponse(content=data)
            
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employees: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching employees: {str(e)}")


@router.post("/fetch-from-external")
async def fetch_from_external_api(
    employee_id: int = Form(...),
    employee_name: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    employee_type: str = Form(default="Svend")
):
    """
    Fetch time registrations from external API and process them.
    
    Args:
        employee_id: Employee ID to fetch registrations for
        employee_name: Full name of the employee
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        employee_type: Employee type for overtime calculation
        
    Returns:
        JSON with preview data (daily and weekly summaries)
    """
    auth_service = get_auth_service()
    
    # Map employee type string to enum
    emp_type_map = {
        "Lærling": EmployeeType.LAERLING,
        "Svend": EmployeeType.SVEND,
        "Funktionær": EmployeeType.FUNKTIONAER,
        "Elev": EmployeeType.ELEV
    }
    emp_type = emp_type_map.get(employee_type, EmployeeType.SVEND)
    
    try:
        # Get authentication token
        token = await auth_service.get_token()
        headers = auth_service.get_headers(token)
        
        # Parse dates as Denmark local time
        denmark_tz = ZoneInfo("Europe/Copenhagen")
        start_dt = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=denmark_tz)
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=denmark_tz)
        
        logger.info(f"📅 User requested date range: {start_date} to {end_date}")
        logger.info(f"🇩🇰 Denmark local time: {start_dt} to {end_dt}")
        
        # Convert to UTC for API query
        start_dt_utc = start_dt.astimezone(ZoneInfo("UTC"))
        end_dt_utc = end_dt.astimezone(ZoneInfo("UTC"))
        
        # Format dates for API (UTC with time component)
        start_date_utc = start_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date_utc = end_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"🌍 UTC time for API query: {start_date_utc} to {end_date_utc}")
        
        # Fetch time registrations from external API with pagination
        async with httpx.AsyncClient(timeout=30.0) as client:
            time_api_url = os.getenv("TIME_API_URL", "")
            if not time_api_url:
                raise HTTPException(status_code=500, detail="TIME_API_URL not configured")
            
            # Fetch all pages of results
            time_registrations = []
            page_number = 1
            page_size = 100  # Request larger page size
            total_count = 0
            
            while True:
                url = (
                    f"{time_api_url}/timeRegistration/search"
                    f"?EmployeeIds={employee_id}"
                    f"&SortOrder=Descending"
                    f"&ShowOnlyCompleted=true"
                    f"&StartTimeUtc={start_date_utc}"
                    f"&EndTimeUtc={end_date_utc}"
                    f"&PageNumber={page_number}"
                    f"&PageSize={page_size}"
                )
                
                if page_number == 1:
                    logger.info(f"🔗 FTZ API Request URL: {url}")
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                api_data = response.json()
                page_results = api_data.get('results', [])
                total_count = api_data.get('totalCount', 0)
                
                if page_number == 1:
                    logger.info(f"📊 FTZ API Response: Total count = {total_count}, Page size = {page_size}")
                
                time_registrations.extend(page_results)
                
                logger.info(f"📄 Fetched page {page_number}: {len(page_results)} records (total so far: {len(time_registrations)}/{total_count})")
                
                # Stop if we got all records or if this page was not full
                if len(time_registrations) >= total_count or len(page_results) < page_size:
                    break
                
                page_number += 1
            
            logger.info(f"✅ Fetched all {len(time_registrations)} records from FTZ API")
            
            # Log first 3 records for debugging
            if time_registrations:
                logger.info(f"📝 First record sample from FTZ:")
                for i, reg in enumerate(time_registrations[:3]):
                    logger.info(f"   Record {i+1}: startTimeUtc={reg.get('startTimeUtc')}, endTimeUtc={reg.get('endTimeUtc')}, caseNo={reg.get('caseNo')}")
        
        if not time_registrations:
            # Return empty preview data
            session_id = str(uuid.uuid4())
            return JSONResponse(content={
                "success": True,
                "session_id": session_id,
                "daily": [],
                "weekly": [],
                "call_out_eligible_days": {},
                "total_records": 0,
                "total_weeks": 0
            })
        
        # Transform to DailyRecord format
        all_records = transform_time_registrations_to_records(
            time_registrations, 
            employee_name
        )
        
        # Process through the existing pipeline
        all_records = process_records_with_segments(all_records)
        all_records = mark_call_out_eligibility(all_records)
        all_records = mark_absence_types(all_records)
        all_records = apply_credited_hours(all_records)
        
        # Calculate overtime
        summaries, outputs = process_all_records(all_records, emp_type)
        
        # Fill in missing dates
        outputs = fill_missing_dates(outputs)
        
        # Get call out eligible days
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
        
        # Cache the processed data (reusing the existing preview_cache from upload.py)
        # We'll need to import this or use a shared cache
        from app.routers.upload import preview_cache
        preview_cache[session_id] = {
            "outputs": outputs,
            "summaries": summaries,
            "call_out_eligible_days": call_out_eligible_days,
            "timestamp": datetime.now()
        }
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "daily": daily_data,
            "weekly": weekly_data,
            "call_out_eligible_days": call_out_eligible_days,
            "total_records": len(outputs),
            "total_weeks": len(summaries)
        })
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch time registrations: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")
