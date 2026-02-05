from collections import defaultdict
from datetime import date as date_type
from typing import Dict, List, Tuple

from app.models.schemas import DailyRecord, DayType, EmployeeType, WeeklySummary, DailyOutput, OvertimeBreakdown, AbsentType
from app.services.call_out_detector import detect_call_out_eligibility


# Weekly norm hours
WEEKLY_NORM_HOURS = 37.0

# Standard daily hours (used for crediting vacation/sick/holiday)
STANDARD_DAILY_HOURS = WEEKLY_NORM_HOURS / 5.0  # 7.4 hours

# Overtime thresholds
OVERTIME_1_THRESHOLD = 3.0  # First 3 hours of overtime (legacy)

# DBR 2026 Overtime Rates (Dansk Bilbrancheråd Collective Agreement)
# Rates effective May 1, 2025 - February 28, 2026
RATES_2025 = {
    'weekday_hour_1_2': 46.70,
    'weekday_hour_3_4': 74.55,
    'weekday_hour_5_plus': 139.50,
    'weekday_scheduled_day': 46.70,  # 06:00-18:00 with notice
    'weekday_scheduled_night': 139.50,  # 18:00-06:00 with notice
    'dayoff_day': 74.55,  # 06:00-18:00
    'dayoff_night': 139.50,  # 18:00-06:00
    'saturday_day': 74.55,  # 06:00-18:00
    'saturday_night': 139.50,  # 18:00-06:00
    'sunday_before_noon': 92.95,  # Before 12:00
    'sunday_after_noon': 139.50,  # After 12:00
    'insufficient_notice': 119.10,
    'lunch_break': 33.05
}

# Rates effective March 1, 2026 - February 28, 2027
RATES_2026 = {
    'weekday_hour_1_2': 48.10,
    'weekday_hour_3_4': 76.80,
    'weekday_hour_5_plus': 143.70,
    'weekday_scheduled_day': 48.10,  # 06:00-18:00 with notice
    'weekday_scheduled_night': 143.70,  # 18:00-06:00 with notice
    'dayoff_day': 76.80,  # 06:00-18:00
    'dayoff_night': 143.70,  # 18:00-06:00
    'saturday_day': 76.80,  # 06:00-18:00
    'saturday_night': 143.70,  # 18:00-06:00
    'sunday_before_noon': 95.75,  # Before 12:00
    'sunday_after_noon': 143.70,  # After 12:00
    'insufficient_notice': 122.70,
    'lunch_break': 34.05
}

# Rates effective March 1, 2027 onwards
RATES_2027 = {
    'weekday_hour_1_2': 49.55,
    'weekday_hour_3_4': 79.10,
    'weekday_hour_5_plus': 148.00,
    'weekday_scheduled_day': 49.55,  # 06:00-18:00 with notice
    'weekday_scheduled_night': 148.00,  # 18:00-06:00 with notice
    'dayoff_day': 79.10,  # 06:00-18:00
    'dayoff_night': 148.00,  # 18:00-06:00
    'saturday_day': 79.10,  # 06:00-18:00
    'saturday_night': 148.00,  # 18:00-06:00
    'sunday_before_noon': 98.60,  # Before 12:00
    'sunday_after_noon': 148.00,  # After 12:00
    'insufficient_notice': 126.35,
    'lunch_break': 35.10
}


def apply_credited_hours(records: list[DailyRecord]) -> list[DailyRecord]:
    """
    Apply credited hours for vacation, sick days, and public holidays.
    
    Days with absent_type set to VACATION, SICK, or PUBLIC_HOLIDAY will be
    credited with the standard daily hours (7.4) toward the weekly norm.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        Updated list with credited hours applied
    """
    for record in records:
        if record.absent_type in [AbsentType.VACATION, AbsentType.SICK, AbsentType.PUBLIC_HOLIDAY]:
            # Credit standard daily hours for absence
            record.credited_hours = STANDARD_DAILY_HOURS
            record.is_day_off = True  # Mark as day off for rate purposes if they work
    
    return records


def get_overtime_rates(calculation_date: date_type) -> Dict[str, float]:
    """
    Get applicable overtime rates based on the calculation date.
    
    Args:
        calculation_date: Date for which to calculate overtime rates
        
    Returns:
        Dictionary of overtime rates applicable for the given date
    """
    if calculation_date >= date_type(2027, 3, 1):
        return RATES_2027
    elif calculation_date >= date_type(2026, 3, 1):
        return RATES_2026
    else:
        return RATES_2025


def categorize_entry_overtime(
    entry_start: 'time',
    entry_end: 'time',
    entry_hours: float,
    day_type: DayType,
    is_day_off: bool,
    weekly_ot_hours_used: float
) -> OvertimeBreakdown:
    """
    Categorize overtime hours for a single time entry based on DBR 2026 rules.
    
    Args:
        entry_start: Start time of the entry
        entry_end: End time of the entry
        entry_hours: Total hours in the entry
        day_type: Type of day (Weekday, Saturday, Sunday)
        is_day_off: Whether this is a scheduled day off
        weekly_ot_hours_used: Cumulative overtime hours already used this week
        
    Returns:
        OvertimeBreakdown with categorized hours
    """
    from app.services.time_calculator import (
        calculate_overtime_day_night_split,
        calculate_sunday_noon_split
    )
    from datetime import time as time_type
    
    breakdown = OvertimeBreakdown()
    
    # Sunday has special handling
    if day_type == DayType.SUNDAY:
        before_noon, after_noon = calculate_sunday_noon_split(entry_start, entry_end)
        breakdown.ot_sunday_before_noon = before_noon
        breakdown.ot_sunday_after_noon = after_noon
        return breakdown
    
    # Saturday uses day-off rates
    if day_type == DayType.SATURDAY:
        day_hours, night_hours = calculate_overtime_day_night_split(entry_start, entry_end)
        breakdown.ot_saturday_day = day_hours
        breakdown.ot_saturday_night = night_hours
        return breakdown
    
    # Weekday handling - split by day/night
    day_hours, night_hours = calculate_overtime_day_night_split(entry_start, entry_end)
    
    if is_day_off:
        # Day off uses different rates
        breakdown.ot_dayoff_day = day_hours
        breakdown.ot_dayoff_night = night_hours
    else:
        # Regular weekday - use scheduled rates
        breakdown.ot_weekday_scheduled_day = day_hours
        breakdown.ot_weekday_scheduled_night = night_hours
    
    return breakdown


def apply_hourly_thresholds(
    total_overtime_hours: float,
    weekly_ot_hours_used: float
) -> Tuple[float, float, float]:
    """
    Apply hourly cumulative thresholds to overtime hours.
    
    Args:
        total_overtime_hours: Total overtime hours to categorize
        weekly_ot_hours_used: Cumulative overtime hours already used this week
        
    Returns:
        Tuple of (hours_in_1_2, hours_in_3_4, hours_in_5_plus)
    """
    hours_1_2 = 0.0
    hours_3_4 = 0.0
    hours_5_plus = 0.0
    
    remaining = total_overtime_hours
    current_ot_count = weekly_ot_hours_used
    
    # Fill 1st and 2nd hour threshold (0-2 hours)
    if current_ot_count < 2.0 and remaining > 0:
        available = 2.0 - current_ot_count
        allocated = min(remaining, available)
        hours_1_2 = allocated
        remaining -= allocated
        current_ot_count += allocated
    
    # Fill 3rd and 4th hour threshold (2-4 hours)
    if current_ot_count < 4.0 and remaining > 0:
        available = 4.0 - current_ot_count
        allocated = min(remaining, available)
        hours_3_4 = allocated
        remaining -= allocated
        current_ot_count += allocated
    
    # Everything else goes to 5+ threshold
    if remaining > 0:
        hours_5_plus = remaining
    
    return hours_1_2, hours_3_4, hours_5_plus


def categorize_day_overtime(
    record: DailyRecord,
    weekly_norm_used: float,
    weekly_ot_hours_used: float
) -> Tuple[OvertimeBreakdown, float, float]:
    """
    Categorize all overtime for a single day's work.
    
    Args:
        record: DailyRecord with time entries
        weekly_norm_used: Normal hours already used this week
        weekly_ot_hours_used: Overtime hours already used this week
        
    Returns:
        Tuple of (OvertimeBreakdown, norm_hours_this_day, ot_hours_this_day)
    """
    day_breakdown = OvertimeBreakdown()
    
    # Include both actual work hours and credited hours (vacation/sick/holiday)
    day_total = record.total_hours + record.credited_hours
    
    # Calculate normal hours for this day
    available_norm = WEEKLY_NORM_HOURS - weekly_norm_used
    norm_hours = min(day_total, max(0, available_norm))
    ot_hours = max(0, day_total - norm_hours)
    
    # If no overtime, return early
    if ot_hours == 0:
        return day_breakdown, norm_hours, 0.0
    
    # If this is a credited day with no actual work, categorize overtime using hourly thresholds
    if record.total_hours == 0 and record.credited_hours > 0:
        # Apply hourly cumulative thresholds for credited overtime
        ot_1_2, ot_3_4, ot_5_plus = apply_hourly_thresholds(ot_hours, weekly_ot_hours_used)
        day_breakdown.ot_weekday_hour_1_2 = ot_1_2
        day_breakdown.ot_weekday_hour_3_4 = ot_3_4
        day_breakdown.ot_weekday_hour_5_plus = ot_5_plus
        return day_breakdown, norm_hours, ot_hours
    
    # For weekdays that are not day-off, apply hourly thresholds
    # AND categorize by time of day
    if record.day_type == DayType.WEEKDAY and not record.is_day_off:
        # Apply hourly cumulative thresholds
        ot_1_2, ot_3_4, ot_5_plus = apply_hourly_thresholds(ot_hours, weekly_ot_hours_used)
        day_breakdown.ot_weekday_hour_1_2 = ot_1_2
        day_breakdown.ot_weekday_hour_3_4 = ot_3_4
        day_breakdown.ot_weekday_hour_5_plus = ot_5_plus
        
        # Also categorize by time of day for each overtime entry
        # We need to split entries to get day/night breakdown
        for entry in record.entries:
            entry_breakdown = categorize_entry_overtime(
                entry.start_time,
                entry.end_time,
                entry.total_hours,
                record.day_type,
                record.is_day_off,
                weekly_ot_hours_used
            )
            # Add to day breakdown (time-of-day categorization)
            day_breakdown.ot_weekday_scheduled_day += entry_breakdown.ot_weekday_scheduled_day
            day_breakdown.ot_weekday_scheduled_night += entry_breakdown.ot_weekday_scheduled_night
    else:
        # For Saturday, Sunday, or day-off, categorize each entry
        for entry in record.entries:
            entry_breakdown = categorize_entry_overtime(
                entry.start_time,
                entry.end_time,
                entry.total_hours,
                record.day_type,
                record.is_day_off,
                weekly_ot_hours_used
            )
            
            # Accumulate into day breakdown
            day_breakdown.ot_weekday_scheduled_day += entry_breakdown.ot_weekday_scheduled_day
            day_breakdown.ot_weekday_scheduled_night += entry_breakdown.ot_weekday_scheduled_night
            day_breakdown.ot_dayoff_day += entry_breakdown.ot_dayoff_day
            day_breakdown.ot_dayoff_night += entry_breakdown.ot_dayoff_night
            day_breakdown.ot_saturday_day += entry_breakdown.ot_saturday_day
            day_breakdown.ot_saturday_night += entry_breakdown.ot_saturday_night
            day_breakdown.ot_sunday_before_noon += entry_breakdown.ot_sunday_before_noon
            day_breakdown.ot_sunday_after_noon += entry_breakdown.ot_sunday_after_noon
    
    return day_breakdown, norm_hours, ot_hours


def merge_overtime_breakdowns(a: OvertimeBreakdown, b: OvertimeBreakdown) -> OvertimeBreakdown:
    """Merge two overtime breakdowns by adding all fields."""
    return OvertimeBreakdown(
        ot_weekday_hour_1_2=a.ot_weekday_hour_1_2 + b.ot_weekday_hour_1_2,
        ot_weekday_hour_3_4=a.ot_weekday_hour_3_4 + b.ot_weekday_hour_3_4,
        ot_weekday_hour_5_plus=a.ot_weekday_hour_5_plus + b.ot_weekday_hour_5_plus,
        ot_weekday_scheduled_day=a.ot_weekday_scheduled_day + b.ot_weekday_scheduled_day,
        ot_weekday_scheduled_night=a.ot_weekday_scheduled_night + b.ot_weekday_scheduled_night,
        ot_dayoff_day=a.ot_dayoff_day + b.ot_dayoff_day,
        ot_dayoff_night=a.ot_dayoff_night + b.ot_dayoff_night,
        ot_saturday_day=a.ot_saturday_day + b.ot_saturday_day,
        ot_saturday_night=a.ot_saturday_night + b.ot_saturday_night,
        ot_sunday_before_noon=a.ot_sunday_before_noon + b.ot_sunday_before_noon,
        ot_sunday_after_noon=a.ot_sunday_after_noon + b.ot_sunday_after_noon
    )


def calculate_legacy_overtime_values(breakdown: OvertimeBreakdown) -> Tuple[float, float, float]:
    """
    Calculate legacy overtime_1/2/3 values from new breakdown for backward compatibility.
    
    Maps new categories to old 3-tier system:
    - overtime_1: 1st/2nd hour threshold
    - overtime_2: 3rd/4th hour threshold
    - overtime_3: 5th+ hour threshold + all weekend/special rates
    
    Args:
        breakdown: OvertimeBreakdown with detailed categorization
        
    Returns:
        Tuple of (overtime_1, overtime_2, overtime_3)
    """
    ot1 = breakdown.ot_weekday_hour_1_2
    ot2 = breakdown.ot_weekday_hour_3_4
    ot3 = (breakdown.ot_weekday_hour_5_plus +
           breakdown.ot_saturday_day + breakdown.ot_saturday_night +
           breakdown.ot_sunday_before_noon + breakdown.ot_sunday_after_noon +
           breakdown.ot_dayoff_day + breakdown.ot_dayoff_night)
    
    return ot1, ot2, ot3


def group_records_by_week(records: list[DailyRecord]) -> Dict[Tuple[str, int, int], list[DailyRecord]]:
    """
    Group daily records by worker and ISO week.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        Dictionary keyed by (worker_name, year, week_number) with list of records
    """
    grouped: Dict[Tuple[str, int, int], list[DailyRecord]] = defaultdict(list)
    
    for record in records:
        year = record.date.year
        week = record.week_number
        key = (record.worker_name, year, week)
        grouped[key].append(record)
    
    # Sort records within each week by date
    for key in grouped:
        grouped[key].sort(key=lambda r: r.date)
    
    return grouped


def calculate_weekly_overtime(
    records: list[DailyRecord],
    employee_type: EmployeeType = EmployeeType.SVEND
) -> Tuple[WeeklySummary, list[DailyOutput]]:
    """
    Calculate overtime for a single week's records according to DBR 2026 rules.
    
    According to Danish automotive industry collective agreement (DBR 2026):
    - Weekly norm: 37 hours
    - Weekday overtime: Hourly thresholds (1st/2nd at lower rate, 3rd/4th, 5th+)
    - Time-of-day: 06:00-18:00 vs 18:00-06:00 rates
    - Saturday: Uses day-off rates, split by time of day
    - Sunday: Split at 12:00 for different rates
    
    Args:
        records: List of DailyRecord objects for a single week
        employee_type: Type of employee for rate calculation
        
    Returns:
        Tuple of (WeeklySummary, list of DailyOutput for each day)
    """
    if not records:
        return None, []
    
    worker_name = records[0].worker_name
    year = records[0].date.year
    week_number = records[0].week_number
    
    # Initialize tracking variables
    weekly_total = 0.0
    weekly_norm_used = 0.0
    weekly_ot_hours_used = 0.0
    weekly_breakdown = OvertimeBreakdown()
    
    daily_outputs: list[DailyOutput] = []
    
    for record in records:
        day_total = record.total_hours
        
        # Categorize this day's overtime
        day_breakdown, day_norm, day_ot = categorize_day_overtime(
            record,
            weekly_norm_used,
            weekly_ot_hours_used
        )
        
        # Update weekly totals
        weekly_total += day_total
        weekly_norm_used += day_norm
        weekly_ot_hours_used += day_ot
        weekly_breakdown = merge_overtime_breakdowns(weekly_breakdown, day_breakdown)
        
        # Calculate legacy overtime values for this day
        day_ot1, day_ot2, day_ot3 = calculate_legacy_overtime_values(day_breakdown)
        
        # Detect call out eligibility for this day
        has_call_out = detect_call_out_eligibility(record)
        
        # Create daily output record
        output = DailyOutput(
            worker=worker_name,
            date=record.date.strftime("%d-%m-%Y"),
            day=record.day_name,
            day_type=record.day_type.value,
            total_hours=round(day_total, 2),
            hours_norm_time=round(record.hours_in_norm, 2),
            hours_outside_norm=round(record.hours_outside_norm, 2),
            week_number=week_number,
            weekly_total=round(weekly_total, 2),
            normal_hours=round(day_norm, 2),
            overtime_breakdown=day_breakdown,
            overtime_1=round(day_ot1, 2),
            overtime_2=round(day_ot2, 2),
            overtime_3=round(day_ot3, 2),
            has_call_out_qualifying_time=has_call_out,
            call_out_payment=0.0,
            call_out_applied=False,
            entries=record.entries
        )
        daily_outputs.append(output)
    
    # Calculate legacy overtime values for weekly summary
    week_ot1, week_ot2, week_ot3 = calculate_legacy_overtime_values(weekly_breakdown)
    
    # Create weekly summary
    summary = WeeklySummary(
        worker_name=worker_name,
        week_number=week_number,
        year=year,
        total_hours=round(weekly_total, 2),
        normal_hours=round(weekly_norm_used, 2),
        overtime_breakdown=weekly_breakdown,
        overtime_1=round(week_ot1, 2),
        overtime_2=round(week_ot2, 2),
        overtime_3=round(week_ot3, 2)
    )
    
    return summary, daily_outputs


def process_all_records(
    records: list[DailyRecord],
    employee_type: EmployeeType = EmployeeType.SVEND
) -> Tuple[list[WeeklySummary], list[DailyOutput]]:
    """
    Process all daily records and calculate overtime for each week.
    
    Args:
        records: List of all DailyRecord objects
        employee_type: Type of employee for rate calculation
        
    Returns:
        Tuple of (list of WeeklySummary, list of DailyOutput)
    """
    # Group records by worker and week
    grouped = group_records_by_week(records)
    
    all_summaries: list[WeeklySummary] = []
    all_outputs: list[DailyOutput] = []
    
    # Process each week
    for key in sorted(grouped.keys()):
        week_records = grouped[key]
        summary, outputs = calculate_weekly_overtime(week_records, employee_type)
        
        if summary:
            all_summaries.append(summary)
        all_outputs.extend(outputs)
    
    return all_summaries, all_outputs


def recalculate_weekly_summaries(outputs: list[DailyOutput]) -> list[WeeklySummary]:
    """
    Recalculate weekly summaries from daily outputs.
    Used when daily hours are updated (e.g., absence marking).
    
    Args:
        outputs: List of DailyOutput objects
        
    Returns:
        List of WeeklySummary objects
    """
    # Group by worker and week
    grouped: Dict[Tuple[str, int, int], list[DailyOutput]] = defaultdict(list)
    
    for output in outputs:
        # Parse year from date string (DD-MM-YYYY)
        date_parts = output.date.split('-')
        year = int(date_parts[2])
        key = (output.worker, year, output.week_number)
        grouped[key].append(output)
    
    summaries: list[WeeklySummary] = []
    
    # Process each week
    for (worker_name, year, week_number), week_outputs in sorted(grouped.items()):
        # Calculate weekly totals
        weekly_total = 0.0
        weekly_norm_used = 0.0
        weekly_ot_hours = 0.0
        weekly_breakdown = OvertimeBreakdown()
        
        for output in week_outputs:
            weekly_total += output.total_hours
            weekly_norm_used += output.normal_hours
            
            # Sum up overtime from breakdown
            ot_from_breakdown = (
                output.overtime_breakdown.ot_weekday_hour_1_2 +
                output.overtime_breakdown.ot_weekday_hour_3_4 +
                output.overtime_breakdown.ot_weekday_hour_5_plus +
                output.overtime_breakdown.ot_saturday_day +
                output.overtime_breakdown.ot_saturday_night +
                output.overtime_breakdown.ot_sunday_before_noon +
                output.overtime_breakdown.ot_sunday_after_noon
            )
            weekly_ot_hours += ot_from_breakdown
            
            # Merge overtime breakdowns
            weekly_breakdown = merge_overtime_breakdowns(weekly_breakdown, output.overtime_breakdown)
        
        # Calculate legacy overtime values
        week_ot1, week_ot2, week_ot3 = calculate_legacy_overtime_values(weekly_breakdown)
        
        summary = WeeklySummary(
            worker_name=worker_name,
            week_number=week_number,
            year=year,
            total_hours=round(weekly_total, 2),
            normal_hours=round(weekly_norm_used, 2),
            overtime_breakdown=weekly_breakdown,
            overtime_1=round(week_ot1, 2),
            overtime_2=round(week_ot2, 2),
            overtime_3=round(week_ot3, 2)
        )
        summaries.append(summary)
    
    return summaries
