import csv
from io import StringIO
from typing import List

from app.models.schemas import DailyOutput, WeeklySummary


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
