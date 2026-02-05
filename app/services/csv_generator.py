import csv
from io import StringIO
from typing import List
from datetime import datetime

from app.models.schemas import DailyOutput, WeeklySummary
from app.services.overtime_calculator import get_overtime_rates


def generate_daily_csv(outputs: List[DailyOutput]) -> str:
    """
    Generate CSV content from daily output records.
    
    Args:
        outputs: List of DailyOutput objects
        
    Returns:
        CSV content as string
    """
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
        "UgeTotal",
        "NormaleTimer",
        "Overtid1",
        "Overtid2",
        "Overtid3",
        "CallOutBetaling"
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
            "UgeTotal": f"{record.weekly_total:.2f}",
            "NormaleTimer": f"{record.normal_hours:.2f}",
            "Overtid1": f"{record.overtime_1:.2f}",
            "Overtid2": f"{record.overtime_2:.2f}",
            "Overtid3": f"{record.overtime_3:.2f}",
            "CallOutBetaling": f"{record.call_out_payment:.2f}"
        })
    
    return output.getvalue()


def generate_weekly_summary_csv(summaries: List[WeeklySummary]) -> str:
    """
    Generate CSV content from weekly summary records.
    
    Args:
        summaries: List of WeeklySummary objects
        
    Returns:
        CSV content as string
    """
    output = StringIO()
    
    fieldnames = [
        "Medarbejder",
        "År",
        "UgeNummer",
        "TotalTimer",
        "NormaleTimer",
        "Overtid1",
        "Overtid2",
        "Overtid3"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    
    for summary in summaries:
        writer.writerow({
            "Medarbejder": summary.worker_name,
            "År": summary.year,
            "UgeNummer": summary.week_number,
            "TotalTimer": f"{summary.total_hours:.2f}",
            "NormaleTimer": f"{summary.normal_hours:.2f}",
            "Overtid1": f"{summary.overtime_1:.2f}",
            "Overtid2": f"{summary.overtime_2:.2f}",
            "Overtid3": f"{summary.overtime_3:.2f}"
        })
    
    return output.getvalue()


def generate_combined_csv(outputs: List[DailyOutput], summaries: List[WeeklySummary]) -> str:
    """
    Generate a combined CSV with daily records and weekly summaries.
    
    Args:
        outputs: List of DailyOutput objects
        summaries: List of WeeklySummary objects
        
    Returns:
        CSV content as string with both daily and weekly data
    """
    daily_csv = generate_daily_csv(outputs)
    
    # Add a separator and weekly summary
    combined = daily_csv
    combined += "\n\n"
    combined += "UGENTLIG OPSUMMERING\n"
    combined += generate_weekly_summary_csv(summaries)
    
    return combined


def generate_detailed_daily_csv(outputs: List[DailyOutput]) -> str:
    """
    Generate detailed CSV with overtime breakdown, rates, and payments (DBR 2026).
    
    Args:
        outputs: List of DailyOutput objects
        
    Returns:
        CSV content as string with detailed overtime categories
    """
    output = StringIO()
    
    fieldnames = [
        "Medarbejder",
        "Dato",
        "Dag",
        "Dagtype",
        "TotalTimer",
        "NormaleTimer",
        # Weekday hourly thresholds
        "OT_Hvd_1-2_Timer",
        "OT_Hvd_1-2_Rate",
        "OT_Hvd_1-2_Betaling",
        "OT_Hvd_3-4_Timer",
        "OT_Hvd_3-4_Rate",
        "OT_Hvd_3-4_Betaling",
        "OT_Hvd_5+_Timer",
        "OT_Hvd_5+_Rate",
        "OT_Hvd_5+_Betaling",
        # Time-of-day scheduled
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
        # Saturday
        "OT_Lør_Dag_Timer",
        "OT_Lør_Dag_Rate",
        "OT_Lør_Dag_Betaling",
        "OT_Lør_Nat_Timer",
        "OT_Lør_Nat_Rate",
        "OT_Lør_Nat_Betaling",
        # Sunday
        "OT_Søn_Før12_Timer",
        "OT_Søn_Før12_Rate",
        "OT_Søn_Før12_Betaling",
        "OT_Søn_Efter12_Timer",
        "OT_Søn_Efter12_Rate",
        "OT_Søn_Efter12_Betaling",
        # Totals
        "OT_Total_Timer",
        "OT_Total_Betaling",
        "CallOutBetaling",
        "Total_Betaling"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    
    for record in outputs:
        # Parse date to get applicable rates
        date_obj = datetime.strptime(record.date, "%d-%m-%Y").date()
        rates = get_overtime_rates(date_obj)
        
        breakdown = record.overtime_breakdown
        
        # Calculate payments for each category
        pay_hvd_1_2 = breakdown.ot_weekday_hour_1_2 * rates['weekday_hour_1_2']
        pay_hvd_3_4 = breakdown.ot_weekday_hour_3_4 * rates['weekday_hour_3_4']
        pay_hvd_5_plus = breakdown.ot_weekday_hour_5_plus * rates['weekday_hour_5_plus']
        pay_hvd_dag = breakdown.ot_weekday_scheduled_day * rates['weekday_scheduled_day']
        pay_hvd_nat = breakdown.ot_weekday_scheduled_night * rates['weekday_scheduled_night']
        pay_fridag_dag = breakdown.ot_dayoff_day * rates['dayoff_day']
        pay_fridag_nat = breakdown.ot_dayoff_night * rates['dayoff_night']
        pay_lør_dag = breakdown.ot_saturday_day * rates['saturday_day']
        pay_lør_nat = breakdown.ot_saturday_night * rates['saturday_night']
        pay_søn_før12 = breakdown.ot_sunday_before_noon * rates['sunday_before_noon']
        pay_søn_efter12 = breakdown.ot_sunday_after_noon * rates['sunday_after_noon']
        
        # Total overtime hours and payment
        total_ot_hours = (
            breakdown.ot_weekday_hour_1_2 + breakdown.ot_weekday_hour_3_4 + 
            breakdown.ot_weekday_hour_5_plus + breakdown.ot_saturday_day + 
            breakdown.ot_saturday_night + breakdown.ot_sunday_before_noon + 
            breakdown.ot_sunday_after_noon + breakdown.ot_dayoff_day + 
            breakdown.ot_dayoff_night
        )
        total_ot_payment = (
            pay_hvd_1_2 + pay_hvd_3_4 + pay_hvd_5_plus + pay_hvd_dag + 
            pay_hvd_nat + pay_fridag_dag + pay_fridag_nat + pay_lør_dag + 
            pay_lør_nat + pay_søn_før12 + pay_søn_efter12
        )
        total_payment = total_ot_payment + record.call_out_payment
        
        writer.writerow({
            "Medarbejder": record.worker,
            "Dato": record.date,
            "Dag": record.day,
            "Dagtype": record.day_type,
            "TotalTimer": f"{record.total_hours:.2f}",
            "NormaleTimer": f"{record.normal_hours:.2f}",
            # Weekday hourly thresholds
            "OT_Hvd_1-2_Timer": f"{breakdown.ot_weekday_hour_1_2:.2f}",
            "OT_Hvd_1-2_Rate": f"{rates['weekday_hour_1_2']:.2f}",
            "OT_Hvd_1-2_Betaling": f"{pay_hvd_1_2:.2f}",
            "OT_Hvd_3-4_Timer": f"{breakdown.ot_weekday_hour_3_4:.2f}",
            "OT_Hvd_3-4_Rate": f"{rates['weekday_hour_3_4']:.2f}",
            "OT_Hvd_3-4_Betaling": f"{pay_hvd_3_4:.2f}",
            "OT_Hvd_5+_Timer": f"{breakdown.ot_weekday_hour_5_plus:.2f}",
            "OT_Hvd_5+_Rate": f"{rates['weekday_hour_5_plus']:.2f}",
            "OT_Hvd_5+_Betaling": f"{pay_hvd_5_plus:.2f}",
            # Time-of-day scheduled
            "OT_Hvd_Dag_Timer": f"{breakdown.ot_weekday_scheduled_day:.2f}",
            "OT_Hvd_Dag_Rate": f"{rates['weekday_scheduled_day']:.2f}",
            "OT_Hvd_Dag_Betaling": f"{pay_hvd_dag:.2f}",
            "OT_Hvd_Nat_Timer": f"{breakdown.ot_weekday_scheduled_night:.2f}",
            "OT_Hvd_Nat_Rate": f"{rates['weekday_scheduled_night']:.2f}",
            "OT_Hvd_Nat_Betaling": f"{pay_hvd_nat:.2f}",
            # Day off
            "OT_Fridag_Dag_Timer": f"{breakdown.ot_dayoff_day:.2f}",
            "OT_Fridag_Dag_Rate": f"{rates['dayoff_day']:.2f}",
            "OT_Fridag_Dag_Betaling": f"{pay_fridag_dag:.2f}",
            "OT_Fridag_Nat_Timer": f"{breakdown.ot_dayoff_night:.2f}",
            "OT_Fridag_Nat_Rate": f"{rates['dayoff_night']:.2f}",
            "OT_Fridag_Nat_Betaling": f"{pay_fridag_nat:.2f}",
            # Saturday
            "OT_Lør_Dag_Timer": f"{breakdown.ot_saturday_day:.2f}",
            "OT_Lør_Dag_Rate": f"{rates['saturday_day']:.2f}",
            "OT_Lør_Dag_Betaling": f"{pay_lør_dag:.2f}",
            "OT_Lør_Nat_Timer": f"{breakdown.ot_saturday_night:.2f}",
            "OT_Lør_Nat_Rate": f"{rates['saturday_night']:.2f}",
            "OT_Lør_Nat_Betaling": f"{pay_lør_nat:.2f}",
            # Sunday
            "OT_Søn_Før12_Timer": f"{breakdown.ot_sunday_before_noon:.2f}",
            "OT_Søn_Før12_Rate": f"{rates['sunday_before_noon']:.2f}",
            "OT_Søn_Før12_Betaling": f"{pay_søn_før12:.2f}",
            "OT_Søn_Efter12_Timer": f"{breakdown.ot_sunday_after_noon:.2f}",
            "OT_Søn_Efter12_Rate": f"{rates['sunday_after_noon']:.2f}",
            "OT_Søn_Efter12_Betaling": f"{pay_søn_efter12:.2f}",
            # Totals
            "OT_Total_Timer": f"{total_ot_hours:.2f}",
            "OT_Total_Betaling": f"{total_ot_payment:.2f}",
            "CallOutBetaling": f"{record.call_out_payment:.2f}",
            "Total_Betaling": f"{total_payment:.2f}"
        })
    
    return output.getvalue()


def generate_detailed_weekly_summary_csv(summaries: List[WeeklySummary]) -> str:
    """
    Generate detailed weekly summary CSV with overtime breakdown (DBR 2026).
    
    Args:
        summaries: List of WeeklySummary objects
        
    Returns:
        CSV content as string with detailed weekly overtime categories
    """
    output = StringIO()
    
    fieldnames = [
        "Medarbejder",
        "År",
        "UgeNummer",
        "TotalTimer",
        "NormaleTimer",
        "OT_Hvd_1-2_Timer",
        "OT_Hvd_3-4_Timer",
        "OT_Hvd_5+_Timer",
        "OT_Lør_Timer",
        "OT_Søn_Timer",
        "OT_Total_Timer"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    
    for summary in summaries:
        breakdown = summary.overtime_breakdown
        
        ot_lør_timer = breakdown.ot_saturday_day + breakdown.ot_saturday_night
        ot_søn_timer = breakdown.ot_sunday_before_noon + breakdown.ot_sunday_after_noon
        total_ot = (
            breakdown.ot_weekday_hour_1_2 + breakdown.ot_weekday_hour_3_4 + 
            breakdown.ot_weekday_hour_5_plus + ot_lør_timer + ot_søn_timer +
            breakdown.ot_dayoff_day + breakdown.ot_dayoff_night
        )
        
        writer.writerow({
            "Medarbejder": summary.worker_name,
            "År": summary.year,
            "UgeNummer": summary.week_number,
            "TotalTimer": f"{summary.total_hours:.2f}",
            "NormaleTimer": f"{summary.normal_hours:.2f}",
            "OT_Hvd_1-2_Timer": f"{breakdown.ot_weekday_hour_1_2:.2f}",
            "OT_Hvd_3-4_Timer": f"{breakdown.ot_weekday_hour_3_4:.2f}",
            "OT_Hvd_5+_Timer": f"{breakdown.ot_weekday_hour_5_plus:.2f}",
            "OT_Lør_Timer": f"{ot_lør_timer:.2f}",
            "OT_Søn_Timer": f"{ot_søn_timer:.2f}",
            "OT_Total_Timer": f"{total_ot:.2f}"
        })
    
    return output.getvalue()
