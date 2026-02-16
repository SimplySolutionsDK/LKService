"""
Example integration endpoint showing how to sync time registrations to Danløn.
This demonstrates the complete workflow from CSV processing to paypart creation.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.services.danlon_api import get_danlon_api_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/danlon/example", tags=["Danløn Integration Examples"])


@router.post("/sync-payparts")
async def sync_payparts_example(
    company_id: str = Query(..., description="Danløn company ID"),
    user_id: Optional[str] = Query("demo_user", description="User ID")
):
    """
    Example endpoint showing how to sync time registrations to Danløn.
    
    This demonstrates:
    1. Getting employee and metadata from Danløn
    2. Transforming your time registration data to payparts
    3. Creating payparts in Danløn
    
    In production, you would:
    - Get user_id from authentication/session
    - Get time registration data from your database or CSV processing
    - Add error handling and validation
    - Store sync status and results
    """
    try:
        # Initialize the API service
        api = get_danlon_api_service(user_id, company_id)
        
        # Step 1: Get current company info
        logger.info("Fetching company information...")
        company = await api.get_current_company()
        logger.info(f"Connected to company: {company['name']} (ID: {company['id']})")
        
        # Step 2: Get employees
        logger.info("Fetching employees...")
        employees = await api.get_employees(include_deleted=False)
        logger.info(f"Found {len(employees)} employees")
        
        # Step 3: Get paypart metadata
        logger.info("Fetching paypart metadata...")
        meta = await api.get_paypart_meta()
        logger.info(f"Found {len(meta['pay_codes'])} pay codes")
        
        # Create lookup maps
        employee_map = {}
        for emp in employees:
            # Map by employment number for easy lookup
            if emp.get("employment_number"):
                employee_map[emp["employment_number"]] = emp
        
        pay_code_map = {code["code"]: code for code in meta["pay_codes"]}
        
        # Step 4: Example time registrations (in production, this comes from CSV or DB)
        # This is mock data - replace with your actual time registration data
        example_time_registrations = [
            {
                "employee_number": "001",  # Replace with actual employment number
                "date": "2024-02-15",
                "pay_code": "100",  # Regular hours
                "hours": 8.0,
                "hourly_rate": 200.0,
                "description": "Regular work day"
            },
            {
                "employee_number": "001",
                "date": "2024-02-16",
                "pay_code": "150",  # Overtime
                "hours": 2.0,
                "hourly_rate": 300.0,
                "description": "Overtime work"
            }
        ]
        
        # Step 5: Transform to payparts
        payparts = []
        skipped = []
        
        for reg in example_time_registrations:
            # Find employee
            employee = employee_map.get(reg["employee_number"])
            if not employee:
                skipped.append({
                    "reason": "Employee not found",
                    "data": reg
                })
                continue
            
            # Find pay code
            pay_code = pay_code_map.get(reg["pay_code"])
            if not pay_code:
                skipped.append({
                    "reason": "Pay code not found",
                    "data": reg
                })
                continue
            
            # Create paypart object
            paypart = {
                "employee_id": employee["id"],
                "date": reg["date"],
                "pay_code_id": pay_code["id"],
                "hours": reg["hours"],
                "rate": reg["hourly_rate"],
                "amount": reg["hours"] * reg["hourly_rate"],
                "text": reg.get("description", "")
            }
            payparts.append(paypart)
        
        # Step 6: Create payparts in Danløn
        if not payparts:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "No valid payparts to create",
                    "skipped": skipped,
                    "company": company
                },
                status_code=400
            )
        
        logger.info(f"Creating {len(payparts)} payparts...")
        result = await api.create_payparts(payparts)
        
        created_count = len(result.get("payparts", []))
        logger.info(f"Successfully created {created_count} payparts")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully created {created_count} payparts",
                "company": company,
                "summary": {
                    "total_processed": len(example_time_registrations),
                    "created": created_count,
                    "skipped": len(skipped)
                },
                "created_payparts": result["payparts"],
                "skipped_items": skipped
            }
        )
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync payparts: {str(e)}"
        )


@router.get("/company-info")
async def get_company_info(
    company_id: str = Query(..., description="Danløn company ID"),
    user_id: Optional[str] = Query("demo_user", description="User ID")
):
    """
    Get company information and metadata from Danløn.
    
    This is useful for:
    - Verifying connection
    - Getting available pay codes and hour types
    - Listing employees
    """
    try:
        api = get_danlon_api_service(user_id, company_id)
        
        # Get all relevant information
        company = await api.get_current_company()
        employees = await api.get_employees(include_deleted=False)
        meta = await api.get_paypart_meta()
        
        return JSONResponse(
            content={
                "company": company,
                "employees": {
                    "count": len(employees),
                    "list": employees[:10]  # First 10 employees
                },
                "metadata": {
                    "pay_codes": meta["pay_codes"],
                    "absence_codes": meta["absence_codes"],
                    "hour_types": meta["hour_types"]
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching company info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch company info: {str(e)}"
        )


@router.post("/test-single-paypart")
async def create_single_paypart_test(
    company_id: str = Query(..., description="Danløn company ID"),
    employee_id: str = Query(..., description="Danløn employee ID"),
    pay_code_id: str = Query(..., description="Pay code ID"),
    hours: float = Query(..., description="Number of hours"),
    rate: float = Query(..., description="Hourly rate"),
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query("demo_user", description="User ID")
):
    """
    Create a single test paypart.
    
    Useful for testing the integration with known IDs.
    """
    try:
        api = get_danlon_api_service(user_id, company_id)
        
        # Use today's date if not provided
        paypart_date = date or datetime.now().strftime("%Y-%m-%d")
        
        result = await api.create_paypart(
            employee_id=employee_id,
            date=paypart_date,
            pay_code_id=pay_code_id,
            hours=hours,
            rate=rate,
            amount=hours * rate,
            text="Test paypart created via API"
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Successfully created test paypart",
                "paypart": result
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating test paypart: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create paypart: {str(e)}"
        )
