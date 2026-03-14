from collections import defaultdict
from datetime import date as date_type
from math import floor
from typing import Dict, List, Tuple

from app.models.schemas import DailyRecord, DayType, EmployeeType, PeriodSummary, DailyOutput, OvertimeBreakdown, AbsentType
from app.services.call_out_detector import detect_call_out_eligibility


# 14-day period norm hours (2 × 37h)
PERIOD_NORM_HOURS = 74.0

# Standard daily hours (used for crediting vacation/sick/holiday)
# Per Danish collective agreement:
# - Monday-Thursday: 7.5 hours each
# - Friday: 7.0 hours
# Total: (4 × 7.5) + 7.0 = 37.0 hours per week / 74.0 per 14-day period
STANDARD_DAILY_HOURS = 37.0 / 5.0  # 7.4 hours (legacy fallback)


def get_credited_hours_for_day(weekday: int) -> float:
    """
    Get credited hours for a day based on the weekday.

    Per Danish collective agreement:
    - Monday-Thursday (0-3): 7.5 hours
    - Friday (4): 7.0 hours
    - Weekend (5-6): 0.0 hours

    Args:
        weekday: Day of week (0=Monday, 6=Sunday)

    Returns:
        Credited hours for the day
    """
    if 0 <= weekday <= 3:   # Monday-Thursday
        return 7.5
    elif weekday == 4:       # Friday
        return 7.0
    else:                    # Weekend
        return 0.0


# -----------------------------------------------------------------------
# DBR Overtime Rates
# Weekend rate = flat OT3-level rate (same as weekday_hour_5_plus).
# Saturday and Sunday are no longer split into sub-categories.
# -----------------------------------------------------------------------

RATES_2025 = {
    'weekday_hour_1_2': 46.70,
    'weekday_hour_3_4': 74.55,
    'weekday_hour_5_plus': 139.50,
    'weekday_scheduled_day': 46.70,    # 06:00-18:00 with notice
    'weekday_scheduled_night': 139.50,  # 18:00-06:00 with notice
    'dayoff_day': 74.55,               # 06:00-18:00
    'dayoff_night': 139.50,            # 18:00-06:00
    'weekend': 139.50,                  # Flat OT3 rate for all Sat/Sun hours
    'insufficient_notice': 119.10,
    'lunch_break': 33.05,
}

RATES_2026 = {
    'weekday_hour_1_2': 48.10,
    'weekday_hour_3_4': 76.80,
    'weekday_hour_5_plus': 143.70,
    'weekday_scheduled_day': 48.10,
    'weekday_scheduled_night': 143.70,
    'dayoff_day': 76.80,
    'dayoff_night': 143.70,
    'weekend': 143.70,
    'insufficient_notice': 122.70,
    'lunch_break': 34.05,
}

RATES_2027 = {
    'weekday_hour_1_2': 49.55,
    'weekday_hour_3_4': 79.10,
    'weekday_hour_5_plus': 148.00,
    'weekday_scheduled_day': 49.55,
    'weekday_scheduled_night': 148.00,
    'dayoff_day': 79.10,
    'dayoff_night': 148.00,
    'weekend': 148.00,
    'insufficient_notice': 126.35,
    'lunch_break': 35.10,
}


def apply_credited_hours(records: list[DailyRecord]) -> list[DailyRecord]:
    """
    Apply credited hours for vacation, sick days, and public holidays.

    Days with absent_type set to VACATION, SICK, or PUBLIC_HOLIDAY will be
    credited with day-specific hours (7.5h Mon-Thu, 7.0h Fri) toward the
    period norm.
    """
    for record in records:
        if record.absent_type in [AbsentType.VACATION, AbsentType.SICK, AbsentType.PUBLIC_HOLIDAY, AbsentType.KURSUS]:
            weekday = record.date.weekday()
            record.credited_hours = get_credited_hours_for_day(weekday)
            record.is_day_off = True
    return records


def get_overtime_rates(calculation_date: date_type) -> Dict[str, float]:
    """Return applicable overtime rates for a given date."""
    if calculation_date >= date_type(2027, 3, 1):
        return RATES_2027
    elif calculation_date >= date_type(2026, 3, 1):
        return RATES_2026
    else:
        return RATES_2025


# -----------------------------------------------------------------------
# Period grouping
# -----------------------------------------------------------------------

def get_period_number(iso_week: int) -> int:
    """
    Map an ISO week number to a 0-based 14-day period index.

    Pairing: weeks 1+2 → period 0, weeks 3+4 → period 1, etc.
    Formula: floor((week - 1) / 2)
    """
    return floor((iso_week - 1) / 2)


def group_records_by_period(
    records: list[DailyRecord],
) -> Dict[Tuple[str, int, int], list[DailyRecord]]:
    """
    Group daily records by (worker_name, year, period_number).

    Returns dictionary sorted by key for deterministic processing.
    """
    grouped: Dict[Tuple[str, int, int], list[DailyRecord]] = defaultdict(list)

    for record in records:
        year = record.date.year
        period = get_period_number(record.week_number)
        key = (record.worker_name, year, period)
        grouped[key].append(record)

    for key in grouped:
        grouped[key].sort(key=lambda r: r.date)

    return grouped


# -----------------------------------------------------------------------
# Overtime breakdown helpers
# -----------------------------------------------------------------------

def apply_hourly_thresholds(
    total_overtime_hours: float,
) -> Tuple[float, float, float]:
    """
    Distribute overtime hours across the three tier thresholds for a period.

    Tiers (per 14-day period):
      OT1: first 2 hours
      OT2: hours 3-4
      OT3: hours 5+

    Returns:
        (hours_ot1, hours_ot2, hours_ot3)
    """
    remaining = total_overtime_hours

    hours_1_2 = min(remaining, 2.0)
    remaining = max(0.0, remaining - hours_1_2)

    hours_3_4 = min(remaining, 2.0)
    remaining = max(0.0, remaining - hours_3_4)

    hours_5_plus = remaining

    return hours_1_2, hours_3_4, hours_5_plus


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
        ot_weekend=a.ot_weekend + b.ot_weekend,
    )


def calculate_ot_values_from_breakdown(
    breakdown: OvertimeBreakdown,
) -> Tuple[float, float, float]:
    """
    Extract (ot1, ot2, ot3) from a breakdown.

    ot1  = weekday tier 1-2 hours
    ot2  = weekday tier 3-4 hours
    ot3  = weekday tier 5+ hours + weekend + day-off hours
    """
    ot1 = breakdown.ot_weekday_hour_1_2
    ot2 = breakdown.ot_weekday_hour_3_4
    ot3 = (
        breakdown.ot_weekday_hour_5_plus
        + breakdown.ot_weekend
        + breakdown.ot_dayoff_day
        + breakdown.ot_dayoff_night
    )
    return ot1, ot2, ot3


# -----------------------------------------------------------------------
# Per-day categorisation (weekday time-of-day + weekend)
# -----------------------------------------------------------------------

def categorize_day_entries_time_of_day(record: DailyRecord) -> OvertimeBreakdown:
    """
    Build a partial OvertimeBreakdown from a single day's entries.

    For weekdays: splits into scheduled_day / scheduled_night (or dayoff rates).
    For weekends: all hours go to ot_weekend.
    Weekday tier counts (ot_weekday_hour_*) are left at 0 here because
    those are assigned at the period level after summing all weekday hours.
    """
    from app.services.time_calculator import calculate_overtime_day_night_split

    day_breakdown = OvertimeBreakdown()

    if record.day_type in (DayType.SATURDAY, DayType.SUNDAY):
        for entry in record.entries:
            day_breakdown.ot_weekend += entry.total_hours
        # Also include credited hours for weekend (rare, but consistent)
        day_breakdown.ot_weekend += record.credited_hours
        return day_breakdown

    # Weekday — categorise by time of day (tier hours assigned at period level)
    for entry in record.entries:
        day_hours, night_hours = calculate_overtime_day_night_split(
            entry.start_time, entry.end_time
        )
        if record.is_day_off:
            day_breakdown.ot_dayoff_day += day_hours
            day_breakdown.ot_dayoff_night += night_hours
        else:
            day_breakdown.ot_weekday_scheduled_day += day_hours
            day_breakdown.ot_weekday_scheduled_night += night_hours

    return day_breakdown


# -----------------------------------------------------------------------
# Period calculation (main entry point per worker-period)
# -----------------------------------------------------------------------

def calculate_period_overtime(
    records: list[DailyRecord],
    employee_type: EmployeeType = EmployeeType.SVEND,
) -> Tuple[PeriodSummary, list[DailyOutput]]:
    """
    Calculate overtime for a single 14-day period.

    Rules:
    - Weekend hours (Sat/Sun) are always OT Weekend at flat OT3 rate.
      They do NOT count toward the 74h weekday norm.
    - Weekday total (including credited absence hours) is compared to 74h.
      Excess is classified into OT1 (first 2h), OT2 (next 2h), OT3 (rest).
    - Weekday time-of-day tracking (scheduled_day / scheduled_night) is
      maintained for detailed CSV / payment reporting, but tier assignment
      happens at the period level.
    """
    if not records:
        return None, []

    worker_name = records[0].worker_name
    year = records[0].date.year
    period_number = get_period_number(records[0].week_number)

    # Sort by date for period_start / period_end derivation
    sorted_records = sorted(records, key=lambda r: r.date)
    period_start = sorted_records[0].date.strftime("%d-%m-%Y")
    period_end = sorted_records[-1].date.strftime("%d-%m-%Y")

    # Accumulate totals
    period_total_hours = 0.0
    period_weekday_hours = 0.0   # Only weekday hours (used vs 74h norm)
    period_weekend_hours = 0.0   # Sat + Sun hours (always OT)

    # Per-day time-of-day breakdown (accumulated for the period)
    period_time_of_day_breakdown = OvertimeBreakdown()

    daily_outputs: list[DailyOutput] = []

    for record in sorted_records:
        day_total = record.total_hours + record.credited_hours

        if record.day_type in (DayType.SATURDAY, DayType.SUNDAY):
            period_total_hours += day_total
            period_weekend_hours += day_total
        else:
            period_total_hours += day_total
            period_weekday_hours += day_total

        # Build per-day time-of-day categorisation
        day_tod_breakdown = categorize_day_entries_time_of_day(record)
        period_time_of_day_breakdown = merge_overtime_breakdowns(
            period_time_of_day_breakdown, day_tod_breakdown
        )

        # Detect call out eligibility
        has_call_out = detect_call_out_eligibility(record)

        # Per-day normal hours: min(day_total, daily_norm) for weekdays, 0 for weekends
        daily_norm = get_credited_hours_for_day(record.date.weekday())
        day_norm_hours = min(day_total, daily_norm) if record.day_type == DayType.WEEKDAY else 0.0

        # Build per-day DailyOutput (weekend hours go into breakdown directly)
        day_breakdown = OvertimeBreakdown()
        if record.day_type in (DayType.SATURDAY, DayType.SUNDAY):
            day_breakdown.ot_weekend = day_total
        # Weekday tier values left at 0 — assigned at period level below

        output = DailyOutput(
            worker=worker_name,
            date=record.date.strftime("%d-%m-%Y"),
            day=record.day_name,
            day_type=record.day_type.value,
            total_hours=round(day_total, 2),
            hours_norm_time=round(record.hours_in_norm, 2),
            hours_outside_norm=round(record.hours_outside_norm, 2),
            week_number=record.week_number,
            period_number=period_number,
            normal_hours=round(day_norm_hours, 2),
            overtime_breakdown=day_breakdown,
            has_call_out_qualifying_time=has_call_out,
            call_out_payment=0.0,
            call_out_applied=False,
            entries=record.entries,
        )
        daily_outputs.append(output)

    # ------------------------------------------------------------------
    # Period-level overtime calculation
    # ------------------------------------------------------------------
    normal_hours = min(period_weekday_hours, PERIOD_NORM_HOURS)
    weekday_ot = max(0.0, period_weekday_hours - PERIOD_NORM_HOURS)

    # Distribute weekday overtime across tiers
    ot1, ot2, ot3_weekday = apply_hourly_thresholds(weekday_ot)

    # Build the final period breakdown
    period_breakdown = OvertimeBreakdown(
        ot_weekday_hour_1_2=round(ot1, 2),
        ot_weekday_hour_3_4=round(ot2, 2),
        ot_weekday_hour_5_plus=round(ot3_weekday, 2),
        ot_weekday_scheduled_day=round(period_time_of_day_breakdown.ot_weekday_scheduled_day, 2),
        ot_weekday_scheduled_night=round(period_time_of_day_breakdown.ot_weekday_scheduled_night, 2),
        ot_dayoff_day=round(period_time_of_day_breakdown.ot_dayoff_day, 2),
        ot_dayoff_night=round(period_time_of_day_breakdown.ot_dayoff_night, 2),
        ot_weekend=round(period_weekend_hours, 2),
    )

    period_ot1, period_ot2, period_ot3 = calculate_ot_values_from_breakdown(period_breakdown)

    summary = PeriodSummary(
        worker_name=worker_name,
        period_number=period_number,
        period_start=period_start,
        period_end=period_end,
        year=year,
        total_hours=round(period_total_hours, 2),
        weekday_hours=round(period_weekday_hours, 2),
        normal_hours=round(normal_hours, 2),
        overtime_breakdown=period_breakdown,
        overtime_1=round(period_ot1, 2),
        overtime_2=round(period_ot2, 2),
        overtime_3=round(period_ot3, 2),
    )

    return summary, daily_outputs


# -----------------------------------------------------------------------
# Process all records
# -----------------------------------------------------------------------

def process_all_records(
    records: list[DailyRecord],
    employee_type: EmployeeType = EmployeeType.SVEND,
) -> Tuple[list[PeriodSummary], list[DailyOutput]]:
    """
    Process all daily records and calculate overtime by 14-day period.

    Returns:
        (list of PeriodSummary, list of DailyOutput)
    """
    grouped = group_records_by_period(records)

    all_summaries: list[PeriodSummary] = []
    all_outputs: list[DailyOutput] = []

    for key in sorted(grouped.keys()):
        period_records = grouped[key]
        summary, outputs = calculate_period_overtime(period_records, employee_type)

        if summary:
            all_summaries.append(summary)
        all_outputs.extend(outputs)

    return all_summaries, all_outputs


# -----------------------------------------------------------------------
# Recalculate period summaries from DailyOutputs
# (used after absence marking / half sick day application)
# -----------------------------------------------------------------------

def recalculate_period_summaries(outputs: list[DailyOutput]) -> list[PeriodSummary]:
    """
    Recalculate period summaries from a flat list of DailyOutput objects.

    Used when daily records are updated (e.g. absence marking, half sick day).
    """
    grouped: Dict[Tuple[str, int, int], list[DailyOutput]] = defaultdict(list)

    for output in outputs:
        key = (output.worker, output.year if hasattr(output, 'year') else int(output.date.split('-')[2]), output.period_number)
        grouped[key].append(output)

    summaries: list[PeriodSummary] = []

    for (worker_name, year, period_number), period_outputs in sorted(grouped.items()):
        period_outputs_sorted = sorted(period_outputs, key=lambda o: o.date)

        total_hours = 0.0
        weekday_hours = 0.0
        weekend_hours = 0.0
        time_of_day_breakdown = OvertimeBreakdown()

        period_start = period_outputs_sorted[0].date
        period_end = period_outputs_sorted[-1].date

        for out in period_outputs_sorted:
            total_hours += out.total_hours
            if out.day_type in ('Saturday', 'Sunday'):
                weekend_hours += out.total_hours
            else:
                weekday_hours += out.total_hours

            time_of_day_breakdown = merge_overtime_breakdowns(
                time_of_day_breakdown, out.overtime_breakdown
            )

        normal_hours = min(weekday_hours, PERIOD_NORM_HOURS)
        weekday_ot = max(0.0, weekday_hours - PERIOD_NORM_HOURS)
        ot1, ot2, ot3_weekday = apply_hourly_thresholds(weekday_ot)

        period_breakdown = OvertimeBreakdown(
            ot_weekday_hour_1_2=round(ot1, 2),
            ot_weekday_hour_3_4=round(ot2, 2),
            ot_weekday_hour_5_plus=round(ot3_weekday, 2),
            ot_weekday_scheduled_day=round(time_of_day_breakdown.ot_weekday_scheduled_day, 2),
            ot_weekday_scheduled_night=round(time_of_day_breakdown.ot_weekday_scheduled_night, 2),
            ot_dayoff_day=round(time_of_day_breakdown.ot_dayoff_day, 2),
            ot_dayoff_night=round(time_of_day_breakdown.ot_dayoff_night, 2),
            ot_weekend=round(weekend_hours, 2),
        )

        period_ot1, period_ot2, period_ot3 = calculate_ot_values_from_breakdown(period_breakdown)

        summary = PeriodSummary(
            worker_name=worker_name,
            period_number=period_number,
            period_start=period_start,
            period_end=period_end,
            year=year,
            total_hours=round(total_hours, 2),
            weekday_hours=round(weekday_hours, 2),
            normal_hours=round(normal_hours, 2),
            overtime_breakdown=period_breakdown,
            overtime_1=round(period_ot1, 2),
            overtime_2=round(period_ot2, 2),
            overtime_3=round(period_ot3, 2),
        )
        summaries.append(summary)

    return summaries


# -----------------------------------------------------------------------
# Apply half sick day
# -----------------------------------------------------------------------

def apply_half_sick_day(record: DailyRecord) -> DailyRecord:
    """
    Top up a partially-worked day to the full daily norm with sick hours.

    For example: if a worker worked 4h on Monday (norm 7.5h), this adds
    3.5h of credited sick hours so the day counts as 7.5h for OT purposes.

    Args:
        record: DailyRecord to top up (must be a weekday with actual entries)

    Returns:
        Updated DailyRecord with credited_hours set to the top-up amount
    """
    daily_norm = get_credited_hours_for_day(record.date.weekday())
    if daily_norm == 0.0 or record.day_type != DayType.WEEKDAY:
        return record  # Weekend days cannot have half sick day top-up

    worked = record.total_hours
    top_up = max(0.0, daily_norm - worked)
    record.credited_hours = top_up
    record.absent_type = AbsentType.SICK
    return record


# -----------------------------------------------------------------------
# Call-out recalculation (adapted for period-based breakdown)
# -----------------------------------------------------------------------

def recalculate_with_callout(
    output: DailyOutput,
    daily_record: DailyRecord,
) -> DailyOutput:
    """
    Recalculate a daily output for a confirmed call-out day.

    Rules:
    - 2-hour minimum for call-out qualifying entries
    - All call-out overtime goes into ot_weekday_hour_5_plus (OT3) in the
      per-day breakdown; this propagates correctly when the period summary
      is recalculated from daily outputs.
    """
    from app.services.call_out_detector import get_call_out_qualifying_entries
    from app.services.time_calculator import calculate_overtime_day_night_split

    qualifying_indices = get_call_out_qualifying_entries(daily_record)
    if not qualifying_indices:
        return output

    callout_hours = 0.0
    callout_entries = []
    other_hours = 0.0

    for idx, entry in enumerate(daily_record.entries):
        if idx in qualifying_indices:
            callout_hours += entry.total_hours
            callout_entries.append(entry)
        else:
            other_hours += entry.total_hours

    original_callout_hours = callout_hours
    if callout_hours < 2.0:
        callout_hours = 2.0

    total_hours = callout_hours + other_hours
    daily_norm = get_credited_hours_for_day(daily_record.date.weekday())
    total_overtime = max(0.0, total_hours - daily_norm)

    new_breakdown = OvertimeBreakdown()

    if total_overtime == 0:
        output.total_hours = round(total_hours, 2)
        return output

    callout_overtime = min(callout_hours, total_overtime)
    other_overtime = max(0.0, total_overtime - callout_overtime)

    if callout_overtime > 0:
        total_callout_day = 0.0
        total_callout_night = 0.0
        for entry in callout_entries:
            d, n = calculate_overtime_day_night_split(entry.start_time, entry.end_time)
            total_callout_day += d
            total_callout_night += n

        if original_callout_hours > 0 and original_callout_hours < 2.0:
            scale = callout_hours / original_callout_hours
            total_callout_day *= scale
            total_callout_night *= scale

        if callout_hours > 0:
            ot_scale = callout_overtime / callout_hours
            day_ot = total_callout_day * ot_scale
            night_ot = total_callout_night * ot_scale
        else:
            day_ot = night_ot = 0.0

        if daily_record.day_type in (DayType.SATURDAY, DayType.SUNDAY):
            new_breakdown.ot_weekend = callout_overtime
        elif daily_record.is_day_off:
            new_breakdown.ot_dayoff_day = day_ot
            new_breakdown.ot_dayoff_night = night_ot
        else:
            # Call-out goes to tier 5+ (OT3) in weekday breakdown
            new_breakdown.ot_weekday_hour_5_plus = callout_overtime
            new_breakdown.ot_weekday_scheduled_day = day_ot
            new_breakdown.ot_weekday_scheduled_night = night_ot

    if other_overtime > 0 and daily_record.day_type == DayType.WEEKDAY and not daily_record.is_day_off:
        # Other weekday overtime keeps tier assignment deferred to period level
        # but we record time-of-day split
        for idx, entry in enumerate(daily_record.entries):
            if idx not in qualifying_indices:
                d, n = calculate_overtime_day_night_split(entry.start_time, entry.end_time)
                if other_hours > 0 and other_overtime < other_hours:
                    scale = other_overtime / other_hours
                    d *= scale
                    n *= scale
                new_breakdown.ot_weekday_scheduled_day += d
                new_breakdown.ot_weekday_scheduled_night += n

    output.total_hours = round(total_hours, 2)
    output.overtime_breakdown = new_breakdown
    return output
