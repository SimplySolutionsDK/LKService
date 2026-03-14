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
    KURSUS = "Kursus"


class TimeEntry(BaseModel):
    """Represents a single time registration entry"""
    activity: str
    case_number: Optional[str] = None
    start_time: time
    end_time: time
    total_hours: float
    hours_in_norm: float = 0.0
    hours_outside_norm: float = 0.0
    duration_display: Optional[str] = None  # Format "H:MM" for display (e.g., "2:26")


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

    # Time-of-day scheduled work (weekdays)
    ot_weekday_scheduled_day: float = 0.0  # 06:00-18:00
    ot_weekday_scheduled_night: float = 0.0  # 18:00-06:00

    # Day off (vacation/scheduled off)
    ot_dayoff_day: float = 0.0  # 06:00-18:00
    ot_dayoff_night: float = 0.0  # 18:00-06:00

    # Weekend (Saturday + Sunday combined, flat OT3 rate)
    ot_weekend: float = 0.0


class PeriodSummary(BaseModel):
    """Summary of a worker's 14-day period with overtime calculations"""
    worker_name: str
    period_number: int   # 0-based index within the year: floor((week - 1) / 2)
    period_start: str    # DD-MM-YYYY of Monday starting the period
    period_end: str      # DD-MM-YYYY of Sunday ending the period
    year: int
    total_hours: float = 0.0
    weekday_hours: float = 0.0   # Weekday-only hours (used for norm comparison)
    normal_hours: float = 0.0    # Min(weekday_hours, 74)

    # Detailed overtime breakdown
    overtime_breakdown: OvertimeBreakdown = OvertimeBreakdown()

    # Top-level OT values (kept for easy access)
    overtime_1: float = 0.0
    overtime_2: float = 0.0
    overtime_3: float = 0.0


class DailyOutput(BaseModel):
    """Output row for the final CSV / preview"""
    worker: str
    date: str
    day: str
    day_type: str
    total_hours: float
    hours_norm_time: float
    hours_outside_norm: float
    week_number: int
    period_number: int   # 14-day period index
    normal_hours: float

    # Detailed overtime breakdown (weekend hours are meaningful per-day;
    # weekday OT tiers only accumulate at period level)
    overtime_breakdown: OvertimeBreakdown = OvertimeBreakdown()

    # Half sick day top-up hours applied to this day
    half_sick_hours: float = 0.0

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
