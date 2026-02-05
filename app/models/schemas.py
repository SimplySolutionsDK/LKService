from pydantic import BaseModel
from typing import Optional
from datetime import date, time
from enum import Enum


class EmployeeType(str, Enum):
    LAERLING = "Lærling"
    SVEND = "Svend"
    FUNKTIONAER = "Funktionær"
    ELEV = "Elev"


class DayType(str, Enum):
    WEEKDAY = "Weekday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class AbsentType(str, Enum):
    """Type of absence that should be credited as work hours"""
    NONE = "None"
    VACATION = "Vacation"
    SICK = "Sick"
    PUBLIC_HOLIDAY = "Public Holiday"


class TimeEntry(BaseModel):
    """Represents a single time registration entry"""
    activity: str
    case_number: Optional[str] = None
    start_time: time
    end_time: time
    total_hours: float
    hours_in_norm: float = 0.0
    hours_outside_norm: float = 0.0


class DailyRecord(BaseModel):
    """Represents all time entries for a single day"""
    worker_name: str
    date: date
    day_name: str
    day_type: DayType
    week_number: int
    entries: list[TimeEntry] = []
    total_hours: float = 0.0
    hours_in_norm: float = 0.0
    hours_outside_norm: float = 0.0
    has_call_out_qualifying_time: bool = False
    is_day_off: bool = False  # Vacation/scheduled day off
    absent_type: 'AbsentType' = AbsentType.NONE
    credited_hours: float = 0.0  # Hours credited for vacation/sick/holiday


class OvertimeBreakdown(BaseModel):
    """Detailed breakdown of overtime hours by category (DBR 2026)"""
    # Weekday hourly cumulative (1st/2nd, 3rd/4th, 5th+ overtime hours)
    ot_weekday_hour_1_2: float = 0.0
    ot_weekday_hour_3_4: float = 0.0
    ot_weekday_hour_5_plus: float = 0.0
    
    # Time-of-day scheduled work
    ot_weekday_scheduled_day: float = 0.0  # 06:00-18:00
    ot_weekday_scheduled_night: float = 0.0  # 18:00-06:00
    
    # Day off (vacation/scheduled off)
    ot_dayoff_day: float = 0.0  # 06:00-18:00
    ot_dayoff_night: float = 0.0  # 18:00-06:00
    
    # Weekend/holiday
    ot_saturday_day: float = 0.0  # 06:00-18:00
    ot_saturday_night: float = 0.0  # 18:00-06:00
    ot_sunday_before_noon: float = 0.0  # Before 12:00
    ot_sunday_after_noon: float = 0.0  # After 12:00


class WeeklySummary(BaseModel):
    """Summary of a worker's week with overtime calculations"""
    worker_name: str
    week_number: int
    year: int
    total_hours: float = 0.0
    normal_hours: float = 0.0
    
    # New detailed overtime breakdown
    overtime_breakdown: OvertimeBreakdown = OvertimeBreakdown()
    
    # Legacy fields for backward compatibility
    overtime_1: float = 0.0
    overtime_2: float = 0.0
    overtime_3: float = 0.0


class DailyOutput(BaseModel):
    """Output row for the final CSV"""
    worker: str
    date: str
    day: str
    day_type: str
    total_hours: float
    hours_norm_time: float
    hours_outside_norm: float
    week_number: int
    weekly_total: float
    normal_hours: float
    
    # New detailed overtime breakdown
    overtime_breakdown: OvertimeBreakdown = OvertimeBreakdown()
    
    # Legacy fields for backward compatibility
    overtime_1: float
    overtime_2: float
    overtime_3: float
    
    has_call_out_qualifying_time: bool = False
    call_out_payment: float = 0.0
    call_out_applied: bool = False
    entries: list[TimeEntry] = []


class ProcessingResult(BaseModel):
    """Result of processing CSV files"""
    success: bool
    message: str
    output_filename: Optional[str] = None
    records_processed: int = 0
