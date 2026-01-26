import re
from datetime import datetime, time, date
from typing import Optional
from io import StringIO

from app.models.schemas import TimeEntry, DailyRecord, DayType


# Danish day names to English mapping
DANISH_DAYS = {
    "mandag": ("Monday", DayType.WEEKDAY),
    "tirsdag": ("Tuesday", DayType.WEEKDAY),
    "onsdag": ("Wednesday", DayType.WEEKDAY),
    "torsdag": ("Thursday", DayType.WEEKDAY),
    "fredag": ("Friday", DayType.WEEKDAY),
    "lørdag": ("Saturday", DayType.SATURDAY),
    "søndag": ("Sunday", DayType.SUNDAY),
    # Handle encoding variants
    "l�rdag": ("Saturday", DayType.SATURDAY),
    "s�ndag": ("Sunday", DayType.SUNDAY),
}


def parse_danish_duration(duration_str: str) -> float:
    """
    Parse Danish duration format 'X Timer Y Minutter' to decimal hours.
    
    Examples:
        '1 Timer 30 Minutter' -> 1.5
        '0 Timer 45 Minutter' -> 0.75
    """
    if not duration_str or not duration_str.strip():
        return 0.0
    
    duration_str = duration_str.strip()
    
    # Pattern to match "X Timer Y Minutter"
    pattern = r"(\d+)\s*Timer\s*(\d+)\s*Minutter"
    match = re.search(pattern, duration_str, re.IGNORECASE)
    
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours + (minutes / 60.0)
    
    return 0.0


def parse_time(time_str: str) -> Optional[time]:
    """Parse time string 'HH:MM' to time object."""
    if not time_str or not time_str.strip():
        return None
    
    time_str = time_str.strip()
    
    try:
        parsed = datetime.strptime(time_str, "%H:%M")
        return parsed.time()
    except ValueError:
        return None


def parse_date_from_header(header: str) -> tuple[Optional[date], str, DayType]:
    """
    Parse day header like 'Mandag 12-01-2026' to extract date, day name, and day type.
    
    Returns:
        Tuple of (date, english_day_name, day_type)
    """
    header = header.strip().lower()
    
    for danish_day, (english_day, day_type) in DANISH_DAYS.items():
        if header.startswith(danish_day):
            # Extract the date part
            date_pattern = r"(\d{2})-(\d{2})-(\d{4})"
            match = re.search(date_pattern, header)
            
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                
                try:
                    parsed_date = date(year, month, day)
                    return parsed_date, english_day, day_type
                except ValueError:
                    pass
            
            return None, english_day, day_type
    
    return None, "", DayType.WEEKDAY


def extract_case_number(activity: str) -> tuple[str, Optional[str]]:
    """
    Extract case number from activity string.
    
    Examples:
        'Arbejdskort Sag Nr. 33511' -> ('Arbejdskort', '33511')
        'Aktivitet: Rengøring' -> ('Rengøring', None)
    """
    activity = activity.strip()
    
    # Pattern for work card case numbers
    case_pattern = r"Arbejdskort\s+Sag\s+Nr\.\s*(\d+)"
    match = re.search(case_pattern, activity, re.IGNORECASE)
    
    if match:
        return "Arbejdskort", match.group(1)
    
    # Pattern for other activities
    activity_pattern = r"Aktivitet:\s*(.+)"
    match = re.search(activity_pattern, activity, re.IGNORECASE)
    
    if match:
        return match.group(1).strip(), None
    
    return activity, None


def is_day_header(line: str) -> bool:
    """Check if line is a day header (e.g., 'Mandag 12-01-2026')."""
    line_lower = line.strip().lower()
    
    for danish_day in DANISH_DAYS.keys():
        if line_lower.startswith(danish_day):
            return True
    
    return False


def is_column_header(line: str) -> bool:
    """Check if line is a column header row."""
    return "aktivitet:" in line.lower() and "start tid:" in line.lower()


def is_daily_total(line: str) -> bool:
    """Check if line is a daily total row."""
    return "total tid for dagen:" in line.lower()


def is_grand_total(line: str) -> bool:
    """Check if line is the grand total row."""
    return "total tid i alt:" in line.lower()


def parse_csv_content(content: str) -> list[DailyRecord]:
    """
    Parse the CSV content and extract all daily records.
    
    Args:
        content: Raw CSV file content as string
        
    Returns:
        List of DailyRecord objects
    """
    records: list[DailyRecord] = []
    
    # Split content into lines
    lines = content.strip().split("\n")
    
    if len(lines) < 3:
        return records
    
    # Line 2 contains the worker name (line 1 is "Tidsregistrering")
    worker_name = lines[1].split(";")[0].strip()
    
    current_date: Optional[date] = None
    current_day_name = ""
    current_day_type = DayType.WEEKDAY
    current_entries: list[TimeEntry] = []
    
    for line in lines[2:]:
        # Skip empty lines
        if not line.strip() or line.strip() == ";;;;;":
            continue
        
        # Check if this is a day header
        if is_day_header(line):
            # Save previous day's records if any
            if current_date and current_entries:
                week_num = current_date.isocalendar()[1]
                total_hours = sum(e.total_hours for e in current_entries)
                hours_in_norm = sum(e.hours_in_norm for e in current_entries)
                hours_outside = sum(e.hours_outside_norm for e in current_entries)
                
                record = DailyRecord(
                    worker_name=worker_name,
                    date=current_date,
                    day_name=current_day_name,
                    day_type=current_day_type,
                    week_number=week_num,
                    entries=current_entries,
                    total_hours=total_hours,
                    hours_in_norm=hours_in_norm,
                    hours_outside_norm=hours_outside
                )
                records.append(record)
            
            # Parse new day header
            current_date, current_day_name, current_day_type = parse_date_from_header(line)
            current_entries = []
            continue
        
        # Skip column headers and total rows
        if is_column_header(line) or is_daily_total(line) or is_grand_total(line):
            continue
        
        # Skip footer lines
        if "fordelt p" in line.lower() or line.strip().endswith("1/1"):
            continue
        
        # Parse time entry
        parts = line.split(";")
        
        if len(parts) >= 5 and parts[0].strip():
            activity_str = parts[0].strip()
            start_time_str = parts[1].strip() if len(parts) > 1 else ""
            end_time_str = parts[3].strip() if len(parts) > 3 else ""
            duration_str = parts[4].strip() if len(parts) > 4 else ""
            
            start_time = parse_time(start_time_str)
            end_time = parse_time(end_time_str)
            total_hours = parse_danish_duration(duration_str)
            
            if start_time and end_time and total_hours > 0:
                activity_name, case_number = extract_case_number(activity_str)
                
                entry = TimeEntry(
                    activity=activity_name,
                    case_number=case_number,
                    start_time=start_time,
                    end_time=end_time,
                    total_hours=total_hours,
                    hours_in_norm=0.0,
                    hours_outside_norm=0.0
                )
                current_entries.append(entry)
    
    # Save last day's records
    if current_date and current_entries:
        week_num = current_date.isocalendar()[1]
        total_hours = sum(e.total_hours for e in current_entries)
        hours_in_norm = sum(e.hours_in_norm for e in current_entries)
        hours_outside = sum(e.hours_outside_norm for e in current_entries)
        
        record = DailyRecord(
            worker_name=worker_name,
            date=current_date,
            day_name=current_day_name,
            day_type=current_day_type,
            week_number=week_num,
            entries=current_entries,
            total_hours=total_hours,
            hours_in_norm=hours_in_norm,
            hours_outside_norm=hours_outside
        )
        records.append(record)
    
    return records


def parse_csv_file(file_content: bytes) -> list[DailyRecord]:
    """
    Parse a CSV file from bytes content, handling encoding.
    
    Args:
        file_content: Raw bytes content of the CSV file
        
    Returns:
        List of DailyRecord objects
    """
    # Try different encodings
    encodings = ["utf-8", "windows-1252", "iso-8859-1", "cp1252"]
    
    content = None
    for encoding in encodings:
        try:
            content = file_content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        # Fallback: decode with errors ignored
        content = file_content.decode("utf-8", errors="ignore")
    
    return parse_csv_content(content)
