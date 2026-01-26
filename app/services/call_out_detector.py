from datetime import time
from typing import Dict

from app.models.schemas import DailyRecord, DailyOutput


# Call out payment amount
CALL_OUT_PAYMENT_AMOUNT = 750.0

# Call out qualifying time boundaries
CALL_OUT_MORNING_END = time(7, 0)  # Before 07:00
CALL_OUT_EVENING_START = time(15, 30)  # After or at 15:30


def detect_call_out_eligibility(record: DailyRecord) -> bool:
    """
    Detect if a daily record qualifies for call out payment.
    
    A day qualifies if ANY time entry starts before 07:00 or at/after 15:30.
    
    Args:
        record: DailyRecord to check for call out eligibility
        
    Returns:
        True if the day qualifies for call out payment, False otherwise
    """
    for entry in record.entries:
        start = entry.start_time
        
        # Check if start time is before 07:00
        if start < CALL_OUT_MORNING_END:
            return True
        
        # Check if start time is at or after 15:30
        if start >= CALL_OUT_EVENING_START:
            return True
    
    return False


def mark_call_out_eligibility(records: list[DailyRecord]) -> list[DailyRecord]:
    """
    Mark all daily records with call out eligibility flag.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        Updated list of DailyRecord objects with has_call_out_qualifying_time set
    """
    for record in records:
        record.has_call_out_qualifying_time = detect_call_out_eligibility(record)
    
    return records


def apply_call_out_payment(
    outputs: list[DailyOutput],
    call_out_selections: Dict[str, bool]
) -> list[DailyOutput]:
    """
    Apply call out payment to selected days.
    
    Args:
        outputs: List of DailyOutput objects
        call_out_selections: Dictionary mapping date strings (DD-MM-YYYY) to boolean
                            (True if call out payment should be applied)
        
    Returns:
        Updated list of DailyOutput objects with call out payment applied
    """
    for output in outputs:
        # Check if this date was selected for call out payment
        date_key = output.date  # Already in DD-MM-YYYY format
        
        if call_out_selections.get(date_key, False):
            # Only apply if the day actually qualifies
            if output.has_call_out_qualifying_time:
                output.call_out_payment = CALL_OUT_PAYMENT_AMOUNT
                output.call_out_applied = True
            else:
                # Reset if somehow selected but doesn't qualify
                output.call_out_payment = 0.0
                output.call_out_applied = False
        else:
            # Not selected, ensure payment is 0
            output.call_out_payment = 0.0
            output.call_out_applied = False
    
    return outputs


def get_call_out_eligible_days(records: list[DailyRecord]) -> list[dict]:
    """
    Get a list of days that qualify for call out payment with details.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        List of dictionaries with date, worker, and qualifying times
    """
    eligible_days = []
    
    for record in records:
        if record.has_call_out_qualifying_time:
            # Collect qualifying time entries
            qualifying_times = []
            for entry in record.entries:
                if (entry.start_time < CALL_OUT_MORNING_END or 
                    entry.start_time >= CALL_OUT_EVENING_START):
                    qualifying_times.append(entry.start_time.strftime("%H:%M"))
            
            eligible_days.append({
                "date": record.date.strftime("%d-%m-%Y"),
                "worker": record.worker_name,
                "qualifying_times": qualifying_times
            })
    
    return eligible_days
