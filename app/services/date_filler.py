from datetime import date, timedelta
from typing import List
from collections import defaultdict

from app.models.schemas import DailyOutput, DayType, OvertimeBreakdown


def fill_missing_dates(outputs: List[DailyOutput]) -> List[DailyOutput]:
    """
    Fill in missing dates between first and last registration per worker.
    - Shows Mon-Fri by default (even without registrations)
    - Shows Sat/Sun only if they have actual registrations
    
    Args:
        outputs: List of DailyOutput records with actual registrations
        
    Returns:
        List of DailyOutput records with missing dates filled in
    """
    if not outputs:
        return outputs
    
    # Group outputs by worker name
    worker_outputs = defaultdict(list)
    for output in outputs:
        worker_outputs[output.worker].append(output)
    
    filled_outputs = []
    
    # Process each worker separately
    for worker_name, worker_records in worker_outputs.items():
        # Convert date strings to date objects and find min/max
        dates_with_data = []
        weekend_dates = set()
        
        for record in worker_records:
            # Parse date string (format: DD-MM-YYYY)
            date_parts = record.date.split('-')
            record_date = date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            dates_with_data.append(record_date)
            
            # Track weekend dates that have registrations
            if record.day_type in ['Saturday', 'Sunday']:
                weekend_dates.add(record_date)
        
        if not dates_with_data:
            continue
        
        min_date = min(dates_with_data)
        max_date = max(dates_with_data)
        
        # Create a map of existing dates for quick lookup
        existing_dates = {record.date: record for record in worker_records}
        
        # Generate all dates in range
        current_date = min_date
        while current_date <= max_date:
            date_str = current_date.strftime('%d-%m-%Y')
            
            # If we already have data for this date, use it
            if date_str in existing_dates:
                filled_outputs.append(existing_dates[date_str])
            else:
                # Determine if we should include this date
                weekday = current_date.weekday()  # 0=Monday, 6=Sunday
                is_weekend = weekday >= 5
                
                # Include if: weekday OR (weekend AND has registrations)
                if not is_weekend or current_date in weekend_dates:
                    # Create empty record for this date
                    day_name = current_date.strftime('%A')
                    
                    # Determine day type
                    if weekday == 5:  # Saturday
                        day_type = 'Saturday'
                    elif weekday == 6:  # Sunday
                        day_type = 'Sunday'
                    else:
                        day_type = 'Weekday'
                    
                    # Get week number
                    week_number = current_date.isocalendar()[1]
                    
                    # Create empty DailyOutput
                    empty_output = DailyOutput(
                        worker=worker_name,
                        date=date_str,
                        day=day_name,
                        day_type=day_type,
                        total_hours=0.0,
                        hours_norm_time=0.0,
                        hours_outside_norm=0.0,
                        week_number=week_number,
                        weekly_total=0.0,
                        normal_hours=0.0,
                        overtime_breakdown=OvertimeBreakdown(),
                        overtime_1=0.0,
                        overtime_2=0.0,
                        overtime_3=0.0,
                        has_call_out_qualifying_time=False,
                        call_out_payment=0.0,
                        call_out_applied=False,
                        entries=[]
                    )
                    filled_outputs.append(empty_output)
            
            current_date += timedelta(days=1)
    
    # Sort by worker name, then by date
    filled_outputs.sort(key=lambda x: (x.worker, _parse_date_for_sort(x.date)))
    
    return filled_outputs


def _parse_date_for_sort(date_str: str) -> date:
    """Helper to parse DD-MM-YYYY format date string for sorting."""
    parts = date_str.split('-')
    return date(int(parts[2]), int(parts[1]), int(parts[0]))
