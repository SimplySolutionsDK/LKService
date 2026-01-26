from collections import defaultdict
from typing import Dict, List, Tuple

from app.models.schemas import DailyRecord, DayType, EmployeeType, WeeklySummary, DailyOutput
from app.services.call_out_detector import detect_call_out_eligibility


# Weekly norm hours
WEEKLY_NORM_HOURS = 37.0

# Overtime thresholds
OVERTIME_1_THRESHOLD = 3.0  # First 3 hours of overtime


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
    Calculate overtime for a single week's records.
    
    According to Danish automotive industry rules:
    - Weekly norm: 37 hours
    - Overtime 1: First 3 hours beyond 37 (+35% for Svend, +50% for Funktionær)
    - Overtime 2: Hours beyond 40 (+100%)
    - Overtime 3: Sunday/holiday hours (+100%)
    
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
    weekly_overtime_1_used = 0.0
    weekly_overtime_2_used = 0.0
    weekly_overtime_3_total = 0.0
    
    daily_outputs: list[DailyOutput] = []
    
    for record in records:
        day_total = record.total_hours
        day_norm = 0.0
        day_ot1 = 0.0
        day_ot2 = 0.0
        day_ot3 = 0.0
        
        # Sunday hours are always Overtime 3
        if record.day_type == DayType.SUNDAY:
            day_ot3 = day_total
            weekly_overtime_3_total += day_total
        else:
            # Calculate how much of this day's hours fit into each bucket
            remaining_hours = day_total
            
            # First, fill up normal hours (up to 37 weekly)
            available_norm = WEEKLY_NORM_HOURS - weekly_norm_used
            if available_norm > 0 and remaining_hours > 0:
                norm_hours = min(remaining_hours, available_norm)
                day_norm = norm_hours
                weekly_norm_used += norm_hours
                remaining_hours -= norm_hours
            
            # Next, fill Overtime 1 (hours 37-40, i.e., first 3 overtime hours)
            if remaining_hours > 0:
                available_ot1 = OVERTIME_1_THRESHOLD - weekly_overtime_1_used
                if available_ot1 > 0:
                    ot1_hours = min(remaining_hours, available_ot1)
                    day_ot1 = ot1_hours
                    weekly_overtime_1_used += ot1_hours
                    remaining_hours -= ot1_hours
            
            # Remaining hours go to Overtime 2
            if remaining_hours > 0:
                day_ot2 = remaining_hours
                weekly_overtime_2_used += remaining_hours
        
        weekly_total += day_total
        
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
            overtime_1=round(day_ot1, 2),
            overtime_2=round(day_ot2, 2),
            overtime_3=round(day_ot3, 2),
            has_call_out_qualifying_time=has_call_out,
            call_out_payment=0.0,
            call_out_applied=False,
            entries=record.entries
        )
        daily_outputs.append(output)
    
    # Create weekly summary
    summary = WeeklySummary(
        worker_name=worker_name,
        week_number=week_number,
        year=year,
        total_hours=round(weekly_total, 2),
        normal_hours=round(weekly_norm_used, 2),
        overtime_1=round(weekly_overtime_1_used, 2),
        overtime_2=round(weekly_overtime_2_used, 2),
        overtime_3=round(weekly_overtime_3_total, 2)
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
