from datetime import date, datetime, time
from typing import Dict, List

from app.models.schemas import DailyRecord, DailyOutput, TimeEntry


# Call out payment amount
CALL_OUT_PAYMENT_AMOUNT = 750.0

# Call out qualifying time boundaries
CALL_OUT_MORNING_END = time(7, 0)  # Before 07:00
CALL_OUT_EVENING_START = time(15, 30)  # After or at 15:30

# Continuation: if gap between previous end and current start is <= this, not a call-out
CALL_OUT_MAX_CONTINUATION_GAP_MINUTES = 15

# Dummy date for time arithmetic (same-day entries only)
_DUMMY_DATE = date(2000, 1, 1)


def _gap_minutes(prev_end: time, curr_start: time) -> float:
    """Return minutes between prev_end and curr_start (same day). curr_start >= prev_end assumed."""
    end_dt = datetime.combine(_DUMMY_DATE, prev_end)
    start_dt = datetime.combine(_DUMMY_DATE, curr_start)
    return (start_dt - end_dt).total_seconds() / 60.0


def _is_continuation(entry: TimeEntry, sorted_entries: List[TimeEntry], i: int) -> bool:
    """
    True if this entry is a continuation of prior work (gap from previous end to this start <= 15 min).
    """
    start = entry.start_time
    # Immediately preceding: largest end_time among previous entries with end_time <= start
    candidates = [sorted_entries[j] for j in range(i) if sorted_entries[j].end_time <= start]
    if not candidates:
        return False
    latest_end = max(candidates, key=lambda e: e.end_time).end_time
    gap = _gap_minutes(latest_end, start)
    return gap <= CALL_OUT_MAX_CONTINUATION_GAP_MINUTES


def detect_call_out_eligibility(record: DailyRecord) -> bool:
    """
    Detect if a daily record qualifies for call out payment.

    A day qualifies if ANY time entry starts before 07:00 or at/after 15:30,
    and is NOT a continuation of prior work. An entry is continuation (not call-out)
    when the gap between the previous assignment's end and this entry's start is
    <= 15 minutes.

    Args:
        record: DailyRecord to check for call out eligibility

    Returns:
        True if the day qualifies for call out payment, False otherwise
    """
    sorted_entries = sorted(record.entries, key=lambda e: e.start_time)

    for i, entry in enumerate(sorted_entries):
        start = entry.start_time

        if start < CALL_OUT_MORNING_END:
            if not _is_continuation(entry, sorted_entries, i):
                return True
            continue

        if start >= CALL_OUT_EVENING_START:
            if not _is_continuation(entry, sorted_entries, i):
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
                    from app.services.overtime_calculator import recalculate_with_callout
                    output = recalculate_with_callout(output, records_by_date[date_key])
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

    An entry qualifies if it starts before 07:00 or at/after 15:30 and is NOT
    a continuation of prior work (gap between previous end and this start > 15 min).

    Args:
        record: DailyRecord to check for call out qualifying entries

    Returns:
        List of indices of qualifying entries in the record.entries list
    """
    sorted_entries = sorted(record.entries, key=lambda e: e.start_time)

    entry_to_index = {}
    for original_idx, entry in enumerate(record.entries):
        entry_to_index[id(entry)] = original_idx

    qualifying_indices = []

    for i, entry in enumerate(sorted_entries):
        start = entry.start_time

        if start < CALL_OUT_MORNING_END:
            if not _is_continuation(entry, sorted_entries, i):
                qualifying_indices.append(entry_to_index[id(entry)])
            continue

        if start >= CALL_OUT_EVENING_START:
            if not _is_continuation(entry, sorted_entries, i):
                qualifying_indices.append(entry_to_index[id(entry)])

    return qualifying_indices


def get_call_out_eligible_days(records: list[DailyRecord]) -> list[dict]:
    """
    Get a list of days that qualify for call out payment with details.
    Uses the same continuation rule: no call-out when gap from previous end
    to this start is <= 15 minutes.

    Args:
        records: List of DailyRecord objects

    Returns:
        List of dictionaries with date, worker, and qualifying times
    """
    eligible_days = []

    for record in records:
        if record.has_call_out_qualifying_time:
            sorted_entries = sorted(record.entries, key=lambda e: e.start_time)
            qualifying_times = []

            for i, entry in enumerate(sorted_entries):
                start = entry.start_time

                if start < CALL_OUT_MORNING_END:
                    if not _is_continuation(entry, sorted_entries, i):
                        qualifying_times.append(start.strftime("%H:%M"))
                elif start >= CALL_OUT_EVENING_START:
                    if not _is_continuation(entry, sorted_entries, i):
                        qualifying_times.append(start.strftime("%H:%M"))

            if qualifying_times:
                eligible_days.append({
                    "date": record.date.strftime("%d-%m-%Y"),
                    "worker": record.worker_name,
                    "qualifying_times": qualifying_times
                })

    return eligible_days
