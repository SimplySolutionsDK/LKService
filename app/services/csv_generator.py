import csv
from io import StringIO
from typing import List
from datetime import datetime

from app.models.schemas import DailyOutput, PeriodSummary
from app.services.overtime_calculator import get_overtime_rates


def generate_daily_csv(outputs: List[DailyOutput]) -> str:
    """Generate CSV content from daily output records."""
    output = StringIO()

    fieldnames = [
        "Medarbejder",
        "Dato",
        "Dag",
        "Dagtype",
        "TotalTimer",
        "TimerNormtid",
        "TimerUdenforNorm",
        "UgeNummer",
        "PeriodeNummer",
        "NormaleTimer",
        "OT_Weekend",
        "CallOutBetaling",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for record in outputs:
        writer.writerow({
            "Medarbejder": record.worker,
            "Dato": record.date,
            "Dag": record.day,
            "Dagtype": record.day_type,
            "TotalTimer": f"{record.total_hours:.2f}",
            "TimerNormtid": f"{record.hours_norm_time:.2f}",
            "TimerUdenforNorm": f"{record.hours_outside_norm:.2f}",
            "UgeNummer": record.week_number,
            "PeriodeNummer": record.period_number,
            "NormaleTimer": f"{record.normal_hours:.2f}",
            "OT_Weekend": f"{record.overtime_breakdown.ot_weekend:.2f}",
            "CallOutBetaling": f"{record.call_out_payment:.2f}",
        })

    return output.getvalue()


def generate_period_summary_csv(summaries: List[PeriodSummary]) -> str:
    """Generate CSV content from 14-day period summary records."""
    output = StringIO()

    fieldnames = [
        "Medarbejder",
        "År",
        "PeriodeNummer",
        "PeriodeStart",
        "PeriodeSlut",
        "TotalTimer",
        "HverdageTimer",
        "NormaleTimer",
        "Overtid1",
        "Overtid2",
        "Overtid3",
        "OT_Weekend",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for summary in summaries:
        otb = summary.overtime_breakdown
        writer.writerow({
            "Medarbejder": summary.worker_name,
            "År": summary.year,
            "PeriodeNummer": summary.period_number,
            "PeriodeStart": summary.period_start,
            "PeriodeSlut": summary.period_end,
            "TotalTimer": f"{summary.total_hours:.2f}",
            "HverdageTimer": f"{summary.weekday_hours:.2f}",
            "NormaleTimer": f"{summary.normal_hours:.2f}",
            "Overtid1": f"{summary.overtime_1:.2f}",
            "Overtid2": f"{summary.overtime_2:.2f}",
            "Overtid3": f"{summary.overtime_3:.2f}",
            "OT_Weekend": f"{otb.ot_weekend:.2f}",
        })

    return output.getvalue()


def generate_combined_csv(outputs: List[DailyOutput], summaries: List[PeriodSummary]) -> str:
    """Generate a combined CSV with daily records and period summaries."""
    daily_csv = generate_daily_csv(outputs)
    combined = daily_csv
    combined += "\n\n"
    combined += "14-DAGES PERIODE OPSUMMERING\n"
    combined += generate_period_summary_csv(summaries)
    return combined


def generate_detailed_daily_csv(outputs: List[DailyOutput]) -> str:
    """
    Generate detailed CSV with overtime breakdown, rates, and payments (DBR 2026).

    Weekday OT tiers (OT1/OT2/OT3) are a period-level concept, so they appear
    in the detailed period summary CSV, not here. Daily detail focuses on
    weekend hours and time-of-day breakdowns for weekdays.
    """
    output = StringIO()

    fieldnames = [
        "Medarbejder",
        "Dato",
        "Dag",
        "Dagtype",
        "TotalTimer",
        "NormaleTimer",
        "HalvSygTimer",
        # Time-of-day scheduled work
        "OT_Hvd_Dag_Timer",
        "OT_Hvd_Dag_Rate",
        "OT_Hvd_Dag_Betaling",
        "OT_Hvd_Nat_Timer",
        "OT_Hvd_Nat_Rate",
        "OT_Hvd_Nat_Betaling",
        # Day off
        "OT_Fridag_Dag_Timer",
        "OT_Fridag_Dag_Rate",
        "OT_Fridag_Dag_Betaling",
        "OT_Fridag_Nat_Timer",
        "OT_Fridag_Nat_Rate",
        "OT_Fridag_Nat_Betaling",
        # Weekend (flat OT3 rate)
        "OT_Weekend_Timer",
        "OT_Weekend_Rate",
        "OT_Weekend_Betaling",
        # Totals
        "CallOutBetaling",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for record in outputs:
        date_obj = datetime.strptime(record.date, "%d-%m-%Y").date()
        rates = get_overtime_rates(date_obj)

        bd = record.overtime_breakdown

        pay_hvd_dag = bd.ot_weekday_scheduled_day * rates['weekday_scheduled_day']
        pay_hvd_nat = bd.ot_weekday_scheduled_night * rates['weekday_scheduled_night']
        pay_fridag_dag = bd.ot_dayoff_day * rates['dayoff_day']
        pay_fridag_nat = bd.ot_dayoff_night * rates['dayoff_night']
        pay_weekend = bd.ot_weekend * rates['weekend']

        writer.writerow({
            "Medarbejder": record.worker,
            "Dato": record.date,
            "Dag": record.day,
            "Dagtype": record.day_type,
            "TotalTimer": f"{record.total_hours:.2f}",
            "NormaleTimer": f"{record.normal_hours:.2f}",
            "HalvSygTimer": f"{record.half_sick_hours:.2f}",
            "OT_Hvd_Dag_Timer": f"{bd.ot_weekday_scheduled_day:.2f}",
            "OT_Hvd_Dag_Rate": f"{rates['weekday_scheduled_day']:.2f}",
            "OT_Hvd_Dag_Betaling": f"{pay_hvd_dag:.2f}",
            "OT_Hvd_Nat_Timer": f"{bd.ot_weekday_scheduled_night:.2f}",
            "OT_Hvd_Nat_Rate": f"{rates['weekday_scheduled_night']:.2f}",
            "OT_Hvd_Nat_Betaling": f"{pay_hvd_nat:.2f}",
            "OT_Fridag_Dag_Timer": f"{bd.ot_dayoff_day:.2f}",
            "OT_Fridag_Dag_Rate": f"{rates['dayoff_day']:.2f}",
            "OT_Fridag_Dag_Betaling": f"{pay_fridag_dag:.2f}",
            "OT_Fridag_Nat_Timer": f"{bd.ot_dayoff_night:.2f}",
            "OT_Fridag_Nat_Rate": f"{rates['dayoff_night']:.2f}",
            "OT_Fridag_Nat_Betaling": f"{pay_fridag_nat:.2f}",
            "OT_Weekend_Timer": f"{bd.ot_weekend:.2f}",
            "OT_Weekend_Rate": f"{rates['weekend']:.2f}",
            "OT_Weekend_Betaling": f"{pay_weekend:.2f}",
            "CallOutBetaling": f"{record.call_out_payment:.2f}",
        })

    return output.getvalue()


def generate_detailed_period_summary_csv(summaries: List[PeriodSummary]) -> str:
    """
    Generate detailed period summary CSV with overtime breakdown and rates (DBR 2026).
    """
    output = StringIO()

    fieldnames = [
        "Medarbejder",
        "År",
        "PeriodeNummer",
        "PeriodeStart",
        "PeriodeSlut",
        "HverdageTimer",
        "NormaleTimer",
        "OT1_Timer",
        "OT1_Rate",
        "OT1_Betaling",
        "OT2_Timer",
        "OT2_Rate",
        "OT2_Betaling",
        "OT3_Hvd_Timer",
        "OT3_Hvd_Rate",
        "OT3_Hvd_Betaling",
        "OT_Weekend_Timer",
        "OT_Weekend_Rate",
        "OT_Weekend_Betaling",
        "OT_Fridag_Dag_Timer",
        "OT_Fridag_Nat_Timer",
        "OT_Total_Timer",
        "OT_Total_Betaling",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for summary in summaries:
        # Use the start date of the period to pick rates
        date_obj = datetime.strptime(summary.period_start, "%d-%m-%Y").date()
        rates = get_overtime_rates(date_obj)

        bd = summary.overtime_breakdown

        pay_ot1 = bd.ot_weekday_hour_1_2 * rates['weekday_hour_1_2']
        pay_ot2 = bd.ot_weekday_hour_3_4 * rates['weekday_hour_3_4']
        pay_ot3_hvd = bd.ot_weekday_hour_5_plus * rates['weekday_hour_5_plus']
        pay_weekend = bd.ot_weekend * rates['weekend']
        pay_fridag_dag = bd.ot_dayoff_day * rates['dayoff_day']
        pay_fridag_nat = bd.ot_dayoff_night * rates['dayoff_night']

        total_ot_hours = (
            bd.ot_weekday_hour_1_2 + bd.ot_weekday_hour_3_4 +
            bd.ot_weekday_hour_5_plus + bd.ot_weekend +
            bd.ot_dayoff_day + bd.ot_dayoff_night
        )
        total_ot_payment = pay_ot1 + pay_ot2 + pay_ot3_hvd + pay_weekend + pay_fridag_dag + pay_fridag_nat

        writer.writerow({
            "Medarbejder": summary.worker_name,
            "År": summary.year,
            "PeriodeNummer": summary.period_number,
            "PeriodeStart": summary.period_start,
            "PeriodeSlut": summary.period_end,
            "HverdageTimer": f"{summary.weekday_hours:.2f}",
            "NormaleTimer": f"{summary.normal_hours:.2f}",
            "OT1_Timer": f"{bd.ot_weekday_hour_1_2:.2f}",
            "OT1_Rate": f"{rates['weekday_hour_1_2']:.2f}",
            "OT1_Betaling": f"{pay_ot1:.2f}",
            "OT2_Timer": f"{bd.ot_weekday_hour_3_4:.2f}",
            "OT2_Rate": f"{rates['weekday_hour_3_4']:.2f}",
            "OT2_Betaling": f"{pay_ot2:.2f}",
            "OT3_Hvd_Timer": f"{bd.ot_weekday_hour_5_plus:.2f}",
            "OT3_Hvd_Rate": f"{rates['weekday_hour_5_plus']:.2f}",
            "OT3_Hvd_Betaling": f"{pay_ot3_hvd:.2f}",
            "OT_Weekend_Timer": f"{bd.ot_weekend:.2f}",
            "OT_Weekend_Rate": f"{rates['weekend']:.2f}",
            "OT_Weekend_Betaling": f"{pay_weekend:.2f}",
            "OT_Fridag_Dag_Timer": f"{bd.ot_dayoff_day:.2f}",
            "OT_Fridag_Nat_Timer": f"{bd.ot_dayoff_night:.2f}",
            "OT_Total_Timer": f"{total_ot_hours:.2f}",
            "OT_Total_Betaling": f"{total_ot_payment:.2f}",
        })

    return output.getvalue()
