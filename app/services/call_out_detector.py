from datetime import time
from typing import Dict

from app.models.schemas import DailyRecord, DailyOutput


# Call out payment amount
CALL_OUT_PAYMENT_AMOUNT = 750.0

# Call out qualifying time boundaries
CALL_OUT_MORNING_END = time(7, 0)  # Before 07:00
CALL_OUT_EVENING_START = time(15, 30)  # After or at 15:30

# Call out continuation check (for entries starting at 16:00+)
CALL_OUT_CONTINUATION_START = time(16, 0)  # Entries at/after 16:00 need continuation check
CALL_OUT_CONTINUATION_WINDOW_MINUTES = 30  # 30 minutes before 16:00 = 15:30


def detect_call_out_eligibility(record: DailyRecord) -> bool:
    """
    Detect if a daily record qualifies for call out payment.
    
    A day qualifies if ANY time entry starts before 07:00 or at/after 15:30,
    with the exception that entries starting at 16:00+ are NOT call-outs if 
    a previous entry ended within 30 minutes of 16:00 (i.e., at or after 15:30).
    
    Args:
        record: DailyRecord to check for call out eligibility
        
    Returns:
        True if the day qualifies for call out payment, False otherwise
    """
    # Sort entries by start time for reliable precedence checking
    sorted_entries = sorted(record.entries, key=lambda e: e.start_time)
    
    for i, entry in enumerate(sorted_entries):
        start = entry.start_time
        
        # Check if start time is before 07:00 (morning call-out, no continuation check)
        if start < CALL_OUT_MORNING_END:
            return True
        
        # Check if start time is at or after 15:30
        if start >= CALL_OUT_EVENING_START:
            # For entries starting at 16:00+, check for continuation
            if start >= CALL_OUT_CONTINUATION_START:
                # Check if any previous entry ended at or after 15:30
                has_recent_work = False
                for j in range(i):
                    prev_entry = sorted_entries[j]
                    if prev_entry.end_time >= CALL_OUT_EVENING_START:
                        has_recent_work = True
                        break
                
                # If there was recent work (ending at/after 15:30), this is continuation, not a call-out
                if has_recent_work:
                    continue
            
            # If we reach here, it's a call-out
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
    call_out_selections: Dict[str, bool],
    records: list[DailyRecord] = None
) -> list[DailyOutput]:
    """
    Apply call out payment to selected days and recalculate overtime with call-out rules.
    
    When a call-out is confirmed, special overtime rules apply:
    - 2-hour minimum for call-out qualifying time entries
    - All call-out overtime classified as OT 3
    
    Args:
        outputs: List of DailyOutput objects
        call_out_selections: Dictionary mapping date strings (DD-MM-YYYY) to boolean
                            (True if call out payment should be applied)
        records: Optional list of DailyRecord objects for overtime recalculation
        
    Returns:
        Updated list of DailyOutput objects with call out payment and adjusted overtime
    """
    # Create a lookup dict for records by date if provided
    records_by_date = {}
    if records:
        for record in records:
            date_key = record.date.strftime("%d-%m-%Y")
            records_by_date[date_key] = record
    
    for output in outputs:
        # Check if this date was selected for call out payment
        date_key = output.date  # Already in DD-MM-YYYY format
        
        if call_out_selections.get(date_key, False):
            # Only apply if the day actually qualifies
            if output.has_call_out_qualifying_time:
                output.call_out_payment = CALL_OUT_PAYMENT_AMOUNT
                output.call_out_applied = True
                
                # Recalculate overtime with call-out rules if we have the record
                if date_key in records_by_date:
                    from app.services.overtime_calculator import recalculate_overtime_with_callout
                    output = recalculate_overtime_with_callout(output, records_by_date[date_key])
            else:
                # Reset if somehow selected but doesn't qualify
                output.call_out_payment = 0.0
                output.call_out_applied = False
        else:
            # Not selected, ensure payment is 0
            output.call_out_payment = 0.0
            output.call_out_applied = False
    
    return outputs


def get_call_out_qualifying_entries(record: DailyRecord) -> list[int]:
    """
    Get indices of time entries that qualify for call-out on a given day.
    
    An entry qualifies if it starts before 07:00 or at/after 15:30,
    with the exception that entries starting at 16:00+ are NOT call-outs if 
    a previous entry ended within 30 minutes of 16:00 (i.e., at or after 15:30).
    
    Args:
        record: DailyRecord to check for call out qualifying entries
        
    Returns:
        List of indices of qualifying entries in the record.entries list
    """
    # Sort entries by start time for reliable precedence checking
    sorted_entries = sorted(record.entries, key=lambda e: e.start_time)
    
    # Map sorted entries back to original indices
    entry_to_index = {}
    for original_idx, entry in enumerate(record.entries):
        entry_to_index[id(entry)] = original_idx
    
    qualifying_indices = []
    
    for i, entry in enumerate(sorted_entries):
        start = entry.start_time
        
        # Check if start time is before 07:00 (morning call-out, no continuation check)
        if start < CALL_OUT_MORNING_END:
            qualifying_indices.append(entry_to_index[id(entry)])
            continue
        
        # Check if start time is at or after 15:30
        if start >= CALL_OUT_EVENING_START:
            # For entries starting at 16:00+, check for continuation
            if start >= CALL_OUT_CONTINUATION_START:
                # Check if any previous entry ended at or after 15:30
                has_recent_work = False
                for j in range(i):
                    prev_entry = sorted_entries[j]
                    if prev_entry.end_time >= CALL_OUT_EVENING_START:
                        has_recent_work = True
                        break
                
                # If there was recent work (ending at/after 15:30), this is continuation, not a call-out
                if has_recent_work:
                    continue
            
            # If we reach here, it's a call-out
            qualifying_indices.append(entry_to_index[id(entry)])
    
    return qualifying_indices


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
            # Sort entries by start time for consistent logic
            sorted_entries = sorted(record.entries, key=lambda e: e.start_time)
            
            # Collect qualifying time entries using the same continuation logic
            qualifying_times = []
            for i, entry in enumerate(sorted_entries):
                start = entry.start_time
                
                # Morning call-out (before 07:00)
                if start < CALL_OUT_MORNING_END:
                    qualifying_times.append(start.strftime("%H:%M"))
                # Evening call-out (at/after 15:30)
                elif start >= CALL_OUT_EVENING_START:
                    # For entries starting at 16:00+, check for continuation
                    if start >= CALL_OUT_CONTINUATION_START:
                        # Check if any previous entry ended at or after 15:30
                        has_recent_work = False
                        for j in range(i):
                            prev_entry = sorted_entries[j]
                            if prev_entry.end_time >= CALL_OUT_EVENING_START:
                                has_recent_work = True
                                break
                        
                        # Skip if continuation of work
                        if has_recent_work:
                            continue
                    
                    # This entry qualifies
                    qualifying_times.append(start.strftime("%H:%M"))
            
            # Only add to eligible_days if there are actual qualifying times
            if qualifying_times:
                eligible_days.append({
                    "date": record.date.strftime("%d-%m-%Y"),
                    "worker": record.worker_name,
                    "qualifying_times": qualifying_times
                })
    
    return eligible_days
