"""
Danlon OAuth2 integration router.
Implements the 10-step connection flow and 2-scenario disconnect flow.
"""
import os
import base64
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional

from app.services.danlon_auth import get_danlon_auth_service
from app.services.danlon_token_store import get_token_store
from app.services.danlon_graphql import get_danlon_graphql_service


router = APIRouter(prefix="/danlon", tags=["danlon"])


@router.get("/connect")
async def connect(return_uri: Optional[str] = Query(None)):
    """
    Landing page for Danlon connection (Steps 1-2).
    
    Redirects the user to Danlon's OAuth2 authorization page.
    If return_uri is provided, it will be carried through the flow.
    
    Args:
        return_uri: Optional URI to redirect to after successful connection
    """
    auth_service = get_danlon_auth_service()
    
    # Build callback URL
    app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{app_base_url}/danlon/callback"
    
    # Build authorization URL
    auth_url = auth_service.build_authorize_url(redirect_uri, return_uri)
    
    # Redirect user's browser to Danlon OAuth2 server
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    return_uri: Optional[str] = Query(None)
):
    """
    OAuth2 callback endpoint (Steps 3-5).
    
    Receives authorization code from Danlon, exchanges it for temporary tokens,
    and redirects to marketplace for company selection.
    
    Args:
        code: Authorization code from OAuth2 server
        error: Error message if authorization failed
        return_uri: Optional return URI to carry through flow
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth2 error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")
    
    auth_service = get_danlon_auth_service()
    
    try:
        # Build the same redirect_uri used in authorization
        app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        redirect_uri = f"{app_base_url}/danlon/callback"
        
        # Include return_uri in redirect_uri if it was provided
        if return_uri:
            redirect_uri = f"{redirect_uri}?return_uri={return_uri}"
        
        # Exchange code for temporary token (Step 4)
        token_response = await auth_service.exchange_code_for_token(code, redirect_uri)
        
        # Base64 encode the temporary access token for marketplace
        temp_access_token = token_response.get("access_token", "")
        encoded_token = base64.b64encode(temp_access_token.encode()).decode()
        
        # Build success callback URL
        success_url = f"{app_base_url}/danlon/success"
        if return_uri:
            success_url = f"{success_url}?return_uri={return_uri}"
        
        # Redirect to marketplace select-company page (Step 6)
        marketplace_endpoint = os.getenv("DANLON_MARKETPLACE_ENDPOINT", "")
        if not marketplace_endpoint:
            raise HTTPException(
                status_code=500, 
                detail="DANLON_MARKETPLACE_ENDPOINT not configured"
            )
        
        marketplace_url = (
            f"{marketplace_endpoint}/select-company"
            f"?token={encoded_token}"
            f"&return_uri={success_url}"
        )
        
        return RedirectResponse(url=marketplace_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")


@router.get("/success")
async def success(
    code: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    return_uri: Optional[str] = Query(None)
):
    """
    Success callback from marketplace (Steps 7-9).
    
    Exchanges marketplace code for final tokens and persists them.
    
    Args:
        code: Marketplace code associated with final tokens
        company_id: Base64-encoded company ID selected by user
        return_uri: Optional return URI to redirect to after success
    """
    if not code:
        raise HTTPException(status_code=400, detail="No marketplace code received")
    
    auth_service = get_danlon_auth_service()
    token_store = get_token_store()
    
    try:
        # Exchange marketplace code for final tokens (Step 8)
        token_response = await auth_service.exchange_marketplace_code(code)
        
        # Decode company ID if provided
        decoded_company_id = ""
        if company_id:
            try:
                decoded_company_id = base64.b64decode(company_id).decode()
            except Exception:
                decoded_company_id = company_id  # Use as-is if decode fails
        
        # Persist tokens (Step 9)
        token_store.save_tokens(
            access_token=token_response.get("access_token", ""),
            refresh_token=token_response.get("refresh_token", ""),
            company_id=decoded_company_id,
            expires_in=token_response.get("expires_in")
        )
        
        # Redirect to return_uri or show success message (Step 10)
        if return_uri:
            return RedirectResponse(url=return_uri, status_code=302)
        else:
            # Redirect to frontend success page
            app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
            return RedirectResponse(url=f"{app_base_url}/?danlon_connected=true", status_code=302)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete connection: {str(e)}"
        )


@router.get("/disconnect")
async def disconnect(return_uri: Optional[str] = Query(None)):
    """
    Disconnect endpoint called by Danlon (Scenario 1).
    
    Danlon has already revoked the token on their side.
    We clean up our stored tokens and redirect back.
    
    Args:
        return_uri: URI to redirect to after cleanup
    """
    token_store = get_token_store()
    
    # Clean up stored tokens
    token_store.delete_tokens()
    
    # Redirect back to return_uri
    if return_uri:
        return RedirectResponse(url=return_uri, status_code=302)
    else:
        # Redirect to frontend
        app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        return RedirectResponse(url=f"{app_base_url}/?danlon_disconnected=true", status_code=302)


@router.post("/revoke")
async def revoke():
    """
    Revoke Danlon connection from our application (Scenario 2).
    
    Revokes the token with Danlon's OAuth2 server and cleans up stored tokens.
    
    Returns:
        JSON response with success status
    """
    auth_service = get_danlon_auth_service()
    token_store = get_token_store()
    
    # Get stored tokens
    stored = token_store.get_tokens()
    if not stored or "refresh_token" not in stored:
        raise HTTPException(status_code=400, detail="No Danlon connection to revoke")
    
    try:
        # Revoke token with OAuth2 server
        await auth_service.revoke_token(stored["refresh_token"])
        
        # Clean up stored tokens
        token_store.delete_tokens()
        
        return JSONResponse(content={
            "success": True,
            "message": "Danlon connection revoked successfully"
        })
        
    except Exception as e:
        # Even if revocation fails, clean up local tokens
        token_store.delete_tokens()
        raise HTTPException(
            status_code=500,
            detail=f"Token revocation failed: {str(e)}"
        )


@router.get("/status")
async def status():
    """
    Get current Danlon connection status.
    
    Returns:
        JSON with connection status, company_id, and timestamps
    """
    auth_service = get_danlon_auth_service()
    status_info = auth_service.get_connection_status()
    
    return JSONResponse(content=status_info)


@router.post("/submit-hours/{session_id}")
async def submit_hours(session_id: str):
    """
    Submit confirmed hours to Danlon as pay parts.
    
    Takes the cached preview data, maps overtime breakdown to Danlon pay part codes,
    and submits via GraphQL.
    
    Args:
        session_id: Session ID of cached preview data
        
    Returns:
        JSON with submission result
    """
    # Import here to avoid circular dependency
    from app.routers.upload import preview_cache
    
    # Check if Danlon is connected
    token_store = get_token_store()
    if not token_store.has_tokens():
        raise HTTPException(
            status_code=400,
            detail="Not connected to Danlon. Please connect first."
        )
    
    # Get cached preview data
    if session_id not in preview_cache:
        raise HTTPException(
            status_code=404,
            detail="Preview session not found. Please upload files again."
        )
    
    cached = preview_cache[session_id]
    outputs = cached.get("outputs", [])
    
    if not outputs:
        raise HTTPException(
            status_code=400,
            detail="No data to submit"
        )
    
    try:
        graphql_service = get_danlon_graphql_service()
        
        # Get company ID from stored tokens
        stored_tokens = token_store.get_tokens()
        company_id = stored_tokens.get("company_id", "")
        
        if not company_id:
            raise HTTPException(
                status_code=400,
                detail="No company ID associated with Danlon connection"
            )
        
        # TODO: This mapping needs to be configured per customer
        # For now, we'll create a basic structure showing how to map overtime to pay parts
        
        # Group hours by worker
        worker_hours = {}
        for output in outputs:
            worker = output.worker
            if worker not in worker_hours:
                worker_hours[worker] = {
                    "normal_hours": 0.0,
                    "ot_weekday_hour_1_2": 0.0,
                    "ot_weekday_hour_3_4": 0.0,
                    "ot_weekday_hour_5_plus": 0.0,
                    "ot_saturday_day": 0.0,
                    "ot_saturday_night": 0.0,
                    "ot_sunday_before_noon": 0.0,
                    "ot_sunday_after_noon": 0.0,
                }
            
            worker_hours[worker]["normal_hours"] += output.normal_hours
            breakdown = output.overtime_breakdown
            worker_hours[worker]["ot_weekday_hour_1_2"] += breakdown.ot_weekday_hour_1_2
            worker_hours[worker]["ot_weekday_hour_3_4"] += breakdown.ot_weekday_hour_3_4
            worker_hours[worker]["ot_weekday_hour_5_plus"] += breakdown.ot_weekday_hour_5_plus
            worker_hours[worker]["ot_saturday_day"] += breakdown.ot_saturday_day
            worker_hours[worker]["ot_saturday_night"] += breakdown.ot_saturday_night
            worker_hours[worker]["ot_sunday_before_noon"] += breakdown.ot_sunday_before_noon
            worker_hours[worker]["ot_sunday_after_noon"] += breakdown.ot_sunday_after_noon
        
        # Build pay lines
        # NOTE: Pay part codes need to be configured based on customer's Danlon setup
        pay_lines = []
        
        for worker, hours in worker_hours.items():
            # Add normal hours
            if hours["normal_hours"] > 0:
                pay_lines.append({
                    "employee_name": worker,
                    "pay_part_code": "NORMAL",  # Needs real code
                    "amount": hours["normal_hours"],
                    "unit": "hours"
                })
            
            # Add overtime categories
            ot_mapping = {
                "ot_weekday_hour_1_2": "OT_WEEKDAY_1_2",
                "ot_weekday_hour_3_4": "OT_WEEKDAY_3_4",
                "ot_weekday_hour_5_plus": "OT_WEEKDAY_5_PLUS",
                "ot_saturday_day": "OT_SATURDAY_DAY",
                "ot_saturday_night": "OT_SATURDAY_NIGHT",
                "ot_sunday_before_noon": "OT_SUNDAY_BEFORE_NOON",
                "ot_sunday_after_noon": "OT_SUNDAY_AFTER_NOON",
            }
            
            for key, code in ot_mapping.items():
                if hours[key] > 0:
                    pay_lines.append({
                        "employee_name": worker,
                        "pay_part_code": code,  # Needs real codes from config
                        "amount": hours[key],
                        "unit": "hours"
                    })
        
        # Submit to Danlon
        result = await graphql_service.submit_pay_parts(company_id, pay_lines)
        
        return JSONResponse(content={
            "success": True,
            "message": "Hours submitted to Danlon successfully",
            "submitted_count": len(pay_lines),
            "workers_count": len(worker_hours),
            "danlon_result": result
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit hours: {str(e)}"
        )
