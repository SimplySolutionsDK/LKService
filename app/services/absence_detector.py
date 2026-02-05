"""
Service for detecting and marking vacation, sick days, and public holidays.
"""

from app.models.schemas import DailyRecord, AbsentType


# Danish terms for different types of absence
VACATION_KEYWORDS = [
    "ferie",
    "vacation",
    "afspadsering",
    "fridag",
    "afspadsering"
]

SICK_KEYWORDS = [
    "syg",
    "sygdom",
    "sick",
    "barns sygedag",
    "barns 1. sygedag",
    "barns 2. sygedag"
]

HOLIDAY_KEYWORDS = [
    "helligdag",
    "holiday",
    "public holiday",
    "fridag",
    "juledag",
    "nytårsdag",
    "påske",
    "pinse",
    "store bededag",
    "kr. himmelfartsdag",
    "grundlovsdag"
]


def detect_absence_from_activity(record: DailyRecord) -> AbsentType:
    """
    Detect absence type from activity names in time entries.
    
    Checks if any time entry contains keywords indicating vacation,
    sick leave, or public holidays.
    
    Args:
        record: DailyRecord with time entries
        
    Returns:
        AbsentType indicating the type of absence detected
    """
    for entry in record.entries:
        activity_lower = entry.activity.lower()
        
        # Check for vacation keywords
        for keyword in VACATION_KEYWORDS:
            if keyword in activity_lower:
                return AbsentType.VACATION
        
        # Check for sick leave keywords
        for keyword in SICK_KEYWORDS:
            if keyword in activity_lower:
                return AbsentType.SICK
        
        # Check for public holiday keywords
        for keyword in HOLIDAY_KEYWORDS:
            if keyword in activity_lower:
                return AbsentType.PUBLIC_HOLIDAY
    
    return AbsentType.NONE


def mark_absence_types(records: list[DailyRecord]) -> list[DailyRecord]:
    """
    Mark absence types for all records based on activity keywords.
    
    Args:
        records: List of DailyRecord objects
        
    Returns:
        Updated list with absent_type field populated
    """
    for record in records:
        if record.absent_type == AbsentType.NONE:
            record.absent_type = detect_absence_from_activity(record)
    
    return records
