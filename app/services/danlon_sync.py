"""
Helper module for syncing processed time registrations to Danløn.
This provides a simple interface to push your CSV data to Danløn as payparts.
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from app.services.danlon_api import get_danlon_api_service

logger = logging.getLogger(__name__)


class DanlonSyncResult:
    """Result object from syncing to Danløn."""
    
    def __init__(
        self,
        success: bool,
        created_count: int = 0,
        skipped_count: int = 0,
        error_count: int = 0,
        created_payparts: Optional[List[Dict]] = None,
        skipped_items: Optional[List[Dict]] = None,
        errors: Optional[List[Dict]] = None,
        message: str = ""
    ):
        self.success = success
        self.created_count = created_count
        self.skipped_count = skipped_count
        self.error_count = error_count
        self.created_payparts = created_payparts or []
        self.skipped_items = skipped_items or []
        self.errors = errors or []
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "message": self.message,
            "summary": {
                "created": self.created_count,
                "skipped": self.skipped_count,
                "errors": self.error_count
            },
            "created_payparts": self.created_payparts,
            "skipped_items": self.skipped_items,
            "errors": self.errors
        }


async def sync_time_registrations_to_danlon(
    user_id: str,
    company_id: str,
    time_registrations: List[Dict[str, Any]],
    employee_number_field: str = "employee_number",
    date_field: str = "date",
    hours_field: str = "hours",
    rate_field: str = "hourly_rate",
    pay_code_field: str = "pay_code",
    description_field: str = "description",
    reference_field: Optional[str] = None,
    skip_on_error: bool = True
) -> DanlonSyncResult:
    """
    Sync processed time registrations to Danløn as payparts.
    
    This is the main function to call when workers are ready to push
    time registrations to Danløn after comparing and validating.
    
    Args:
        user_id: The authenticated user ID
        company_id: Danløn company ID
        time_registrations: List of time registration dictionaries
        employee_number_field: Field name for employee number (default: "employee_number")
        date_field: Field name for date (default: "date")
        hours_field: Field name for hours (default: "hours")
        rate_field: Field name for hourly rate (default: "hourly_rate")
        pay_code_field: Field name for pay code (default: "pay_code")
        description_field: Field name for description (default: "description")
        reference_field: Optional field name for reference number
        skip_on_error: If True, skip invalid entries; if False, fail entire sync
        
    Returns:
        DanlonSyncResult object with sync results
        
    Example:
        ```python
        # After processing your CSV
        time_entries = [
            {
                "employee_number": "001",
                "date": "2024-02-15",
                "hours": 8.0,
                "hourly_rate": 200.0,
                "pay_code": "100",
                "description": "Regular work"
            }
        ]
        
        result = await sync_time_registrations_to_danlon(
            user_id="user123",
            company_id="danlon_company_id",
            time_registrations=time_entries
        )
        
        if result.success:
            print(f"Created {result.created_count} payparts")
        else:
            print(f"Sync failed: {result.message}")
        ```
    """
    try:
        logger.info(f"Starting Danløn sync for {len(time_registrations)} time registrations")
        
        # Get API service
        api = get_danlon_api_service(user_id, company_id)
        
        # Fetch employees and metadata
        logger.info("Fetching employees and metadata from Danløn...")
        employees = await api.get_employees(include_deleted=False)
        meta = await api.get_paypart_meta()
        
        # Create lookup maps
        employee_map = {}
        for emp in employees:
            # Map by employment number
            if emp.get("employment_number"):
                employee_map[str(emp["employment_number"])] = emp
            # Also map by CPR number if available
            if emp.get("cpr_number"):
                employee_map[emp["cpr_number"]] = emp
        
        pay_code_map = {str(code["code"]): code for code in meta["pay_codes"]}
        
        logger.info(f"Found {len(employees)} employees and {len(meta['pay_codes'])} pay codes")
        
        # Transform time registrations to payparts
        payparts = []
        skipped = []
        errors = []
        
        for idx, reg in enumerate(time_registrations):
            try:
                # Extract fields
                employee_number = str(reg.get(employee_number_field, "")).strip()
                date = reg.get(date_field, "")
                hours = float(reg.get(hours_field, 0))
                rate = float(reg.get(rate_field, 0))
                pay_code = str(reg.get(pay_code_field, "")).strip()
                description = reg.get(description_field, "")
                
                # Validate required fields
                if not employee_number:
                    skipped.append({
                        "index": idx,
                        "reason": "Missing employee number",
                        "data": reg
                    })
                    continue
                
                if not date:
                    skipped.append({
                        "index": idx,
                        "reason": "Missing date",
                        "data": reg
                    })
                    continue
                
                if hours <= 0:
                    skipped.append({
                        "index": idx,
                        "reason": "Invalid hours (must be > 0)",
                        "data": reg
                    })
                    continue
                
                # Find employee
                employee = employee_map.get(employee_number)
                if not employee:
                    skipped.append({
                        "index": idx,
                        "reason": f"Employee not found: {employee_number}",
                        "data": reg
                    })
                    continue
                
                # Find pay code
                pay_code_obj = pay_code_map.get(pay_code)
                if not pay_code_obj:
                    skipped.append({
                        "index": idx,
                        "reason": f"Pay code not found: {pay_code}",
                        "data": reg
                    })
                    continue
                
                # Create paypart object
                paypart = {
                    "employee_id": employee["id"],
                    "date": date,
                    "pay_code_id": pay_code_obj["id"],
                    "hours": hours,
                    "rate": rate,
                    "amount": hours * rate
                }
                
                # Add optional fields
                if description:
                    paypart["text"] = str(description)[:200]  # Limit description length
                
                if reference_field and reg.get(reference_field):
                    paypart["reference"] = str(reg[reference_field])
                
                payparts.append(paypart)
                
            except Exception as e:
                error_msg = f"Error processing entry {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    "index": idx,
                    "reason": error_msg,
                    "data": reg
                })
                
                if not skip_on_error:
                    return DanlonSyncResult(
                        success=False,
                        error_count=1,
                        errors=errors,
                        message=f"Sync failed: {error_msg}"
                    )
        
        # Check if we have any payparts to create
        if not payparts:
            message = "No valid payparts to create"
            logger.warning(message)
            return DanlonSyncResult(
                success=False,
                skipped_count=len(skipped),
                error_count=len(errors),
                skipped_items=skipped,
                errors=errors,
                message=message
            )
        
        # Create payparts in Danløn
        logger.info(f"Creating {len(payparts)} payparts in Danløn...")
        result = await api.create_payparts(payparts)
        
        created_payparts = result.get("payparts", [])
        created_count = len(created_payparts)
        
        logger.info(f"Successfully created {created_count} payparts")
        
        return DanlonSyncResult(
            success=True,
            created_count=created_count,
            skipped_count=len(skipped),
            error_count=len(errors),
            created_payparts=created_payparts,
            skipped_items=skipped,
            errors=errors,
            message=f"Successfully created {created_count} payparts"
        )
        
    except Exception as e:
        error_msg = f"Danløn sync failed: {str(e)}"
        logger.error(error_msg)
        return DanlonSyncResult(
            success=False,
            error_count=1,
            errors=[{"reason": error_msg}],
            message=error_msg
        )


async def check_danlon_connection(user_id: str, company_id: str) -> bool:
    """
    Check if a valid Danløn connection exists.
    
    Args:
        user_id: User identifier
        company_id: Danløn company ID
        
    Returns:
        True if connected and tokens are valid, False otherwise
    """
    try:
        api = get_danlon_api_service(user_id, company_id)
        company = await api.get_current_company()
        return True
    except Exception as e:
        logger.warning(f"Danløn connection check failed: {str(e)}")
        return False


async def get_danlon_company_info(
    user_id: str, 
    company_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get company information from Danløn.
    
    Args:
        user_id: User identifier
        company_id: Danløn company ID
        
    Returns:
        Company info dictionary or None if failed
    """
    try:
        api = get_danlon_api_service(user_id, company_id)
        company = await api.get_current_company()
        employees = await api.get_employees(include_deleted=False)
        meta = await api.get_paypart_meta()
        
        return {
            "company": company,
            "employee_count": len(employees),
            "employees": employees,
            "pay_codes": meta["pay_codes"],
            "absence_codes": meta["absence_codes"],
            "hour_types": meta["hour_types"]
        }
    except Exception as e:
        logger.error(f"Failed to get company info: {str(e)}")
        return None


# Convenience function for common field mappings
async def sync_csv_data_to_danlon(
    user_id: str,
    company_id: str,
    csv_data: List[Dict[str, Any]]
) -> DanlonSyncResult:
    """
    Convenience function for syncing CSV data with common field names.
    
    Supports common field name variations:
    - Employee: employee_number, employment_number, emp_number, employee_id
    - Date: date, work_date, registration_date
    - Hours: hours, total_hours, time
    - Rate: hourly_rate, rate, pay_rate
    - Pay Code: pay_code, paycode, code
    
    Args:
        user_id: User identifier
        company_id: Danløn company ID
        csv_data: List of dictionaries from CSV parsing
        
    Returns:
        DanlonSyncResult object
    """
    # Auto-detect field names
    if not csv_data:
        return DanlonSyncResult(
            success=False,
            message="No data provided"
        )
    
    sample = csv_data[0]
    
    # Find employee field
    employee_field = None
    for field in ["employee_number", "employment_number", "emp_number", "employee_id"]:
        if field in sample:
            employee_field = field
            break
    
    # Find date field
    date_field = None
    for field in ["date", "work_date", "registration_date"]:
        if field in sample:
            date_field = field
            break
    
    # Find hours field
    hours_field = None
    for field in ["hours", "total_hours", "time"]:
        if field in sample:
            hours_field = field
            break
    
    # Find rate field
    rate_field = None
    for field in ["hourly_rate", "rate", "pay_rate"]:
        if field in sample:
            rate_field = field
            break
    
    # Find pay code field
    pay_code_field = None
    for field in ["pay_code", "paycode", "code"]:
        if field in sample:
            pay_code_field = field
            break
    
    # Validate required fields were found
    missing = []
    if not employee_field:
        missing.append("employee number")
    if not date_field:
        missing.append("date")
    if not hours_field:
        missing.append("hours")
    if not rate_field:
        missing.append("rate")
    if not pay_code_field:
        missing.append("pay code")
    
    if missing:
        return DanlonSyncResult(
            success=False,
            message=f"Could not auto-detect required fields: {', '.join(missing)}"
        )
    
    # Call main sync function
    return await sync_time_registrations_to_danlon(
        user_id=user_id,
        company_id=company_id,
        time_registrations=csv_data,
        employee_number_field=employee_field,
        date_field=date_field,
        hours_field=hours_field,
        rate_field=rate_field,
        pay_code_field=pay_code_field,
        description_field="description",
        reference_field="reference"
    )
