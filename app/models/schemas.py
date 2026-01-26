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


class WeeklySummary(BaseModel):
    """Summary of a worker's week with overtime calculations"""
    worker_name: str
    week_number: int
    year: int
    total_hours: float = 0.0
    normal_hours: float = 0.0
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
