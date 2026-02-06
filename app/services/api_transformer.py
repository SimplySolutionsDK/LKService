"""
API data transformer for converting external API responses to internal format.
"""
from datetime import datetime, time, date
from typing import List, Dict, Any
from zoneinfo import ZoneInfo
import logging
from app.models.schemas import DailyRecord, TimeEntry, DayType

logger = logging.getLogger(__name__)


def transform_time_registrations_to_records(
    time_registrations: List[Dict[str, Any]],
    employee_name: str
) -> List[DailyRecord]:
    """
    Transform time registration API response to DailyRecord format.
    
    Args:
        time_registrations: List of time registration objects from API
        employee_name: Full name of the employee
        
    Returns:
        List of DailyRecord objects grouped by date
    """
    # Group registrations by date
    records_by_date: Dict[date, List[Dict[str, Any]]] = {}
    
    logger.info(f"🔄 Transforming {len(time_registrations)} time registrations...")
    
    for i, reg in enumerate(time_registrations):
        # Parse UTC timestamp
        start_dt_utc = datetime.fromisoformat(reg['startTimeUtc'].replace('Z', '+00:00'))
        end_dt_utc = datetime.fromisoformat(reg['endTimeUtc'].replace('Z', '+00:00'))
        
        # Convert to Denmark local time (UTC+1/UTC+2 with DST)
        denmark_tz = ZoneInfo("Europe/Copenhagen")
        start_dt = start_dt_utc.astimezone(denmark_tz)
        end_dt = end_dt_utc.astimezone(denmark_tz)
        
        # Use the Denmark local date for grouping
        reg_date = start_dt.date()
        
        # Log first 3 conversions for debugging
        if i < 3:
            logger.info(f"   ✅ Record {i+1} converted:")
            logger.info(f"      UTC: {start_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"      🇩🇰 DK:  {start_dt.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"      Date: {reg_date}, Case: {reg.get('caseNo')}")
        
        if reg_date not in records_by_date:
            records_by_date[reg_date] = []
        
        records_by_date[reg_date].append({
            'start_dt': start_dt,
            'end_dt': end_dt,
            'case_no': reg.get('caseNo', 0),
            'elapsed_hours': reg.get('elapsedHours', 0.0),
            'registration_type': reg.get('registrationTypeId', 1)
        })
    
    # Convert to DailyRecord objects
    daily_records = []
    
    logger.info(f"📅 Grouped into {len(records_by_date)} dates: {sorted([str(d) for d in records_by_date.keys()])}")
    
    for reg_date, regs in sorted(records_by_date.items()):
        # Determine day type
        weekday = reg_date.weekday()
        if weekday == 5:  # Saturday
            day_type = DayType.SATURDAY
        elif weekday == 6:  # Sunday
            day_type = DayType.SUNDAY
        else:
            day_type = DayType.WEEKDAY
        
        # Create time entries
        entries = []
        total_hours = 0.0
        
        for reg in regs:
            # Determine activity based on registration type
            # Type 1 = Work, Type 4 = Other/Non-billable
            activity = f"Sag {reg['case_no']}" if reg['case_no'] > 0 else "Diverse"
            
            entry = TimeEntry(
                activity=activity,
                case_number=str(reg['case_no']) if reg['case_no'] > 0 else None,
                start_time=time(reg['start_dt'].hour, reg['start_dt'].minute),
                end_time=time(reg['end_dt'].hour, reg['end_dt'].minute),
                total_hours=reg['elapsed_hours']
            )
            entries.append(entry)
            total_hours += reg['elapsed_hours']
        
        # Create daily record
        daily_record = DailyRecord(
            worker_name=employee_name,
            date=reg_date,
            day_name=reg_date.strftime('%A'),
            day_type=day_type,
            week_number=reg_date.isocalendar()[1],
            entries=entries,
            total_hours=total_hours
        )
        
        daily_records.append(daily_record)
    
    return daily_records


def get_employee_full_name(employee: Dict[str, Any]) -> str:
    """
    Get full name from employee object.
    
    Args:
        employee: Employee object from API
        
    Returns:
        Full name string
    """
    firstname = employee.get('firstname', '').strip()
    lastname = employee.get('lastname', '').strip()
    
    if firstname and lastname:
        return f"{firstname} {lastname}"
    elif firstname:
        return firstname
    elif lastname:
        return lastname
    else:
        return f"Employee {employee.get('employeeId', 'Unknown')}"
