from datetime import time, datetime, timedelta
from typing import Tuple

from app.models.schemas import TimeEntry, DailyRecord, DayType


# Norm time boundaries (07:00 - 17:00)
NORM_START = time(7, 0)
NORM_END = time(17, 0)


def time_to_minutes(t: time) -> int:
    """Convert time object to minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_hours(minutes: int) -> float:
    """Convert minutes to decimal hours."""
    return minutes / 60.0


def calculate_time_segments(start: time, end: time) -> Tuple[float, float]:
    """
    Calculate hours within norm time (07:00-17:00) and outside.
    
    Args:
        start: Start time of the work period
        end: End time of the work period
        
    Returns:
        Tuple of (hours_in_norm, hours_outside_norm)
    """
    start_minutes = time_to_minutes(start)
    end_minutes = time_to_minutes(end)
    norm_start_minutes = time_to_minutes(NORM_START)
    norm_end_minutes = time_to_minutes(NORM_END)
    
    # Handle case where end is before start (shouldn't happen in this data)
    if end_minutes <= start_minutes:
        return 0.0, 0.0
    
    total_minutes = end_minutes - start_minutes
    
    # Calculate overlap with norm time (07:00-17:00)
    overlap_start = max(start_minutes, norm_start_minutes)
    overlap_end = min(end_minutes, norm_end_minutes)
    
    if overlap_end > overlap_start:
        norm_minutes = overlap_end - overlap_start
    else:
        norm_minutes = 0
    
    outside_minutes = total_minutes - norm_minutes
    
    return minutes_to_hours(norm_minutes), minutes_to_hours(outside_minutes)


def calculate_entry_segments(entry: TimeEntry) -> TimeEntry:
    """
    Calculate and update time segments for a single time entry.
    
    Args:
        entry: TimeEntry object to calculate segments for
        
    Returns:
        Updated TimeEntry with hours_in_norm and hours_outside_norm populated
    """
    hours_in_norm, hours_outside_norm = calculate_time_segments(
        entry.start_time, entry.end_time
    )
    
    entry.hours_in_norm = round(hours_in_norm, 2)
    entry.hours_outside_norm = round(hours_outside_norm, 2)
    
    return entry


def calculate_daily_segments(record: DailyRecord) -> DailyRecord:
    """
    Calculate time segments for all entries in a daily record.
    
    Args:
        record: DailyRecord with time entries
        
    Returns:
        Updated DailyRecord with calculated segments
    """
    total_norm = 0.0
    total_outside = 0.0
    
    for entry in record.entries:
        calculate_entry_segments(entry)
        total_norm += entry.hours_in_norm
        total_outside += entry.hours_outside_norm
    
    record.hours_in_norm = round(total_norm, 2)
    record.hours_outside_norm = round(total_outside, 2)
    
    return record


def process_records_with_segments(records: list[DailyRecord]) -> list[DailyRecord]:
    """
    Process all daily records and calculate time segments.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        Updated list with calculated time segments
    """
    for record in records:
        calculate_daily_segments(record)
    
    return records
