"""
Danløn OAuth2 callback endpoints for connection/disconnection flow.
"""
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from typing import Optional, Any, Dict, List
import logging
import base64
from datetime import datetime

from sqlalchemy import select
from app.database import async_session_maker
from app.models.danlon_pay_code_mapping import DanlonPayCodeMapping
from app.models.danlon_employee_mapping import DanlonEmployeeMapping
from app.services.danlon_oauth import get_danlon_oauth_service
from app.services.danlon_api import get_danlon_api_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/danlon", tags=["Danløn OAuth"])


@router.get("/connect")
async def connect_landing(
    request: Request,
    return_uri: Optional[str] = Query(None, description="Return URI if initiated from Danløn")
):
    """
    Landing page for initiating Danløn connection.
    
    This is Step 1 in the connection flow.
    
    Flow:
    - If return_uri is present, user initiated from Danløn's integration page
    - If not present, user is initiating from our app
    - Either way, we redirect to Danløn's OAuth2 server for authorization
    
    Query Parameters:
    - return_uri: Optional URI to return to after successful connection (from Danløn)
    """
    logger.info(f"Connect landing page accessed. return_uri: {return_uri}")
    
    # TODO: Check if user is logged in to your application
    # If not logged in, redirect to login and preserve return_uri
    # For now, we'll assume user is logged in
    
    oauth_service = get_danlon_oauth_service()
    
    # Generate authorization URL (Step 2)
    auth_url = oauth_service.get_authorization_url(return_uri=return_uri)
    
    logger.info(f"Redirecting to Danløn authorization: {auth_url}")
    
    # Redirect user to Danløn's OAuth2 server
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code from OAuth2"),
    return_uri: Optional[str] = Query(None, description="Return URI to preserve through flow"),
    error: Optional[str] = Query(None, description="Error from OAuth2"),
    error_description: Optional[str] = Query(None, description="Error description")
):
    """
    OAuth2 callback endpoint - receives authorization code from Danløn.
    
    This is Step 3 in the connection flow.
    
    After user consents on Danløn, they are redirected here with an authorization code.
    We then:
    1. Exchange code for temporary access token (Step 4)
    2. Redirect to select-company page (Step 6)
    
    Query Parameters:
    - code: Authorization code to exchange for token
    - return_uri: Return URI if connection was initiated from Danløn
    - error: Error code if authorization failed
    - error_description: Human-readable error description
    """
    # Check for errors
    if error:
        logger.error(f"OAuth2 error: {error} - {error_description}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Connection Failed</title></head>
                <body>
                    <h1>Connection to Danløn Failed</h1>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                    <p><a href="/">Return to Home</a></p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    logger.info(f"OAuth callback received. code: {code[:20]}..., return_uri: {return_uri}")
    
    oauth_service = get_danlon_oauth_service()
    
    # Build the exact redirect_uri that was used in the authorization request
    redirect_uri = str(request.url_for("oauth_callback"))
    if return_uri:
        redirect_uri = f"{redirect_uri}?return_uri={return_uri}"
    
    try:
        # Step 4: Exchange code for temporary access token
        temp_access_token, temp_refresh_token = await oauth_service.exchange_code_for_temp_token(
            code=code,
            redirect_uri=redirect_uri
        )
        
        logger.info("Successfully obtained temporary tokens")

        # Step 6: Build the select-company URL
        select_company_url = oauth_service.get_select_company_url(
            temp_access_token=temp_access_token,
            return_uri=return_uri
        )

        # Persist a pending session so the frontend can recover if the
        # automatic redirect from Danløn never arrives (demo environment).
        user_id = "demo_user"
        await oauth_service.create_pending_session(
            user_id=user_id,
            select_company_url=select_company_url,
            temp_access_token=temp_access_token,
            temp_refresh_token=temp_refresh_token,
        )

        logger.info(f"Redirecting to select-company: {select_company_url}")
        return RedirectResponse(url=select_company_url)
        
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Connection Error</title></head>
                <body>
                    <h1>Error Processing Connection</h1>
                    <p>{str(e)}</p>
                    <p><a href="/danlon/connect">Try Again</a></p>
                </body>
            </html>
            """,
            status_code=500
        )


@router.get("/success")
async def success_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Code for final token exchange"),
    company_id: Optional[str] = Query(None, description="Selected company ID (base64)"),
    return_uri: Optional[str] = Query(None, description="Return URI if initiated from Danløn")
):
    """
    Success callback after company selection.
    
    This is Step 7-9 in the connection flow.
    
    After user selects a company (or auto-selected if only one), we:
    1. Receive code and company_id from Danløn (Step 7)
    2. Exchange code for final tokens (Step 8)
    3. Persist the tokens (Step 9)
    4. Redirect user appropriately (Step 10)
    
    Query Parameters:
    - code: Code to exchange for final access and refresh tokens
    - company_id: Base64-encoded company ID
    - return_uri: Return URI if connection was initiated from Danløn
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")
    
    logger.info(f"Success callback received. code: {code[:20]}..., company_id: {company_id}")
    
    oauth_service = get_danlon_oauth_service()
    
    try:
        # Step 8: Exchange code for final tokens
        token_data = await oauth_service.exchange_code_for_final_tokens(code=code)
        
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 300)
        
        # Decode company_id if provided
        decoded_company_id = None
        if company_id:
            try:
                decoded_company_id = base64.b64decode(company_id).decode('utf-8')
                logger.info(f"Decoded company_id: {decoded_company_id}")
            except Exception as e:
                logger.warning(f"Failed to decode company_id: {e}")
        
        # If company_id not provided, query the API to get it
        if not decoded_company_id:
            try:
                result = await oauth_service.query_graphql(
                    access_token=access_token,
                    query="{current_company{id}}"
                )
                decoded_company_id = result["data"]["current_company"]["id"]
                logger.info(f"Fetched company_id from API: {decoded_company_id}")
            except Exception as e:
                logger.error(f"Failed to fetch company_id: {e}")
                decoded_company_id = "unknown"
        
        # Step 9: Persist tokens
        # TODO: Replace with actual user_id from session/auth
        user_id = "demo_user"  # This should come from your authentication system
        
        await oauth_service.store_tokens(
            user_id=user_id,
            company_id=decoded_company_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in
        )
        
        logger.info(f"Successfully stored tokens for user {user_id}, company {decoded_company_id}")

        # Clean up the pending session now that we have final tokens
        await oauth_service.delete_pending_session(user_id)

        # Step 10: Redirect based on where connection was initiated
        if return_uri:
            # Connection was initiated from Danløn, redirect back
            logger.info(f"Redirecting back to Danløn: {return_uri}")
            return RedirectResponse(url=return_uri)
        else:
            # Connection was initiated from our app — redirect to the frontend with a success flag
            frontend_url = oauth_service.frontend_base_url
            redirect_target = f"{frontend_url}?danlon_connected=true"
            logger.info(f"Redirecting to frontend: {redirect_target}")
            return RedirectResponse(url=redirect_target)
        
    except Exception as e:
        logger.error(f"Success callback error: {str(e)}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Connection Error</title></head>
                <body>
                    <h1>Error Completing Connection</h1>
                    <p>{str(e)}</p>
                    <p><a href="/danlon/connect">Try Again</a></p>
                </body>
            </html>
            """,
            status_code=500
        )


@router.get("/revoke")
async def revoke_callback(
    request: Request,
    return_uri: Optional[str] = Query(None, description="Return URI to redirect after cleanup")
):
    """
    Revoke callback - called when user disconnects from Danløn side.
    
    This is Scenario 1 of the disconnect flow.
    
    When a user disconnects from Danløn's integration page:
    1. Danløn revokes the tokens on OAuth2 server
    2. Danløn redirects user here
    3. We clean up locally (delete tokens, disable services)
    4. We redirect back to return_uri
    
    Query Parameters:
    - return_uri: URI to redirect user back to after cleanup
    """
    logger.info(f"Revoke callback received. return_uri: {return_uri}")
    
    # TODO: Get actual user_id from session
    user_id = "demo_user"
    
    oauth_service = get_danlon_oauth_service()
    
    # Clean up all tokens for this user
    # In production, this would query database for all companies associated with user
    # For now, we'll just clear the in-memory storage
    # oauth_service.delete_tokens(user_id, company_id)
    
    logger.info(f"Cleaned up tokens for user {user_id}")
    
    # Redirect back to Danløn if return_uri provided
    if return_uri:
        logger.info(f"Redirecting back to: {return_uri}")
        return RedirectResponse(url=return_uri)
    else:
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Disconnected from Danløn</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            max-width: 600px;
                            margin: 50px auto;
                            padding: 20px;
                            background: #f5f5f5;
                        }
                        .card {
                            background: white;
                            border-radius: 8px;
                            padding: 30px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }
                        h1 {
                            color: #e74c3c;
                        }
                        a {
                            display: inline-block;
                            background: #2c5aa0;
                            color: white;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 4px;
                            margin-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Disconnected from Danløn</h1>
                        <p>Your connection to Danløn has been removed. All tokens have been cleaned up.</p>
                        <p>You can reconnect at any time.</p>
                        <a href="/">Return to Home</a>
                    </div>
                </body>
            </html>
            """
        )


@router.post("/disconnect")
async def disconnect(
    request: Request,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None
):
    """
    Disconnect endpoint - initiated from our application.
    
    This is Scenario 2 of the disconnect flow.
    
    When a user wants to disconnect from our app:
    1. We revoke the token on Danløn's OAuth2 server
    2. We delete our local tokens
    3. We return success
    
    Body (JSON):
    - user_id: Optional user ID (defaults to demo_user)
    - company_id: Optional company ID (required if specified)
    """
    # TODO: Get user_id from session/authentication
    if not user_id:
        user_id = "demo_user"
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    
    logger.info(f"Disconnect requested for user {user_id}, company {company_id}")
    
    oauth_service = get_danlon_oauth_service()
    
    # Get stored tokens
    tokens = await oauth_service.get_tokens(user_id, company_id)
    if not tokens:
        raise HTTPException(status_code=404, detail="No connection found for this user/company")
    
    try:
        # Revoke the refresh token on Danløn's OAuth2 server
        await oauth_service.revoke_token(tokens["refresh_token"])
        
        # Delete local tokens
        await oauth_service.delete_tokens(user_id, company_id)
        
        logger.info(f"Successfully disconnected user {user_id}, company {company_id}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Successfully disconnected from Danløn"
            }
        )
        
    except Exception as e:
        logger.error(f"Disconnect error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


@router.post("/token/refresh")
async def refresh_token_endpoint(
    request: Request,
    user_id: Optional[str] = None,
    company_id: Optional[str] = None
):
    """
    Refresh access token endpoint.
    
    Returns a valid access token, refreshing if necessary.
    Use this before making API calls to ensure you have a valid token.
    
    Body (JSON):
    - user_id: Optional user ID (defaults to demo_user)
    - company_id: Company ID to get token for
    
    Returns:
    - access_token: Valid access token
    - expires_in: Seconds until expiration
    """
    # TODO: Get user_id from session/authentication
    if not user_id:
        user_id = "demo_user"
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    
    oauth_service = get_danlon_oauth_service()
    
    try:
        access_token = await oauth_service.get_valid_access_token(user_id, company_id)
        
        if not access_token:
            raise HTTPException(
                status_code=404, 
                detail="No valid tokens found. Please connect to Danløn first."
            )
        
        return JSONResponse(
            content={
                "access_token": access_token,
                "expires_in": 300  # 5 minutes
            }
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")


@router.get("/status")
async def connection_status(
    user_id: Optional[str] = None,
    company_id: Optional[str] = None
):
    """
    Check connection status for a user/company.
    
    Query Parameters:
    - user_id: Optional user ID (defaults to demo_user)
    - company_id: Optional company ID
    
    Returns:
    - connected: Boolean indicating if tokens exist
    - company_id: Company ID if connected
    - expires_at: Token expiration time
    """
    if not user_id:
        user_id = "demo_user"
    
    oauth_service = get_danlon_oauth_service()

    if company_id:
        tokens = await oauth_service.get_tokens(user_id, company_id)
        if tokens:
            return JSONResponse(
                content={
                    "connected": True,
                    "user_id": user_id,
                    "company_id": company_id,
                    "company_name": tokens.get("company_name"),
                    "expires_at": tokens["expires_at"].isoformat(),
                    "created_at": tokens["created_at"].isoformat()
                }
            )
    else:
        # No company_id specified — return the first connection found for this user
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            first = all_tokens[0]
            return JSONResponse(
                content={
                    "connected": True,
                    "user_id": user_id,
                    "company_id": first["company_id"],
                    "company_name": first.get("company_name"),
                    "expires_at": first["expires_at"].isoformat(),
                    "created_at": first["created_at"].isoformat()
                }
            )

    return JSONResponse(
        content={
            "connected": False,
            "user_id": user_id,
            "company_id": company_id
        }
    )


@router.get("/pending")
async def pending_session(user_id: Optional[str] = None):
    """
    Return any active pending OAuth session for the user.

    The frontend calls this after navigating back from the OAuth flow
    to discover whether a company-selection redirect is still outstanding.

    Returns:
    - pending: True if there is an active pending session
    - select_company_url: The Danløn select-company URL the user should visit
    - expires_at: When the pending session expires
    """
    if not user_id:
        user_id = "demo_user"

    oauth_service = get_danlon_oauth_service()
    session_data = await oauth_service.get_pending_session(user_id)

    if session_data:
        return JSONResponse(content={
            "pending": True,
            "session_id": session_data["session_id"],
            "select_company_url": session_data["select_company_url"],
            "expires_at": session_data["expires_at"].isoformat(),
        })

    return JSONResponse(content={"pending": False})


@router.post("/complete")
async def complete_connection(request: Request):
    """
    Manual completion endpoint — used when the automatic redirect from Danløn
    did not arrive (e.g. demo environment limitations).

    Accepts JSON body with ONE of the following combinations:

    Option A — exchange a code returned by the select-company page:
        { "code": "<code from redirect URL>" }

    Option B — enter tokens directly (fully manual):
        {
            "access_token": "...",
            "refresh_token": "...",
            "company_id": "...",
            "company_name": "..."   // optional
        }
    """
    user_id = "demo_user"
    body = await request.json()

    oauth_service = get_danlon_oauth_service()

    if "code" in body and body["code"]:
        # Option A: exchange code via code2token
        code = body["code"].strip()
        logger.info(f"Manual complete: exchanging code for user {user_id}")
        try:
            token_data = await oauth_service.exchange_code_for_final_tokens(code=code)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Code exchange failed: {e}")

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 300)

        # Try to fetch company_id from API
        decoded_company_id = body.get("company_id", "").strip() or None
        if not decoded_company_id:
            try:
                result = await oauth_service.query_graphql(
                    access_token=access_token,
                    query="{current_company{id}}"
                )
                decoded_company_id = result["data"]["current_company"]["id"]
            except Exception as e:
                logger.warning(f"Could not fetch company_id: {e}")
                decoded_company_id = "unknown"

        company_name = body.get("company_name", "").strip() or None

    elif "access_token" in body and "refresh_token" in body:
        # Option B: fully manual token entry
        access_token = body["access_token"].strip()
        refresh_token = body["refresh_token"].strip()
        expires_in = int(body.get("expires_in", 300))
        decoded_company_id = body.get("company_id", "").strip() or "manual"
        company_name = body.get("company_name", "").strip() or None
        logger.info(f"Manual complete: storing provided tokens for user {user_id}")

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'code' or both 'access_token' and 'refresh_token'."
        )

    await oauth_service.store_tokens(
        user_id=user_id,
        company_id=decoded_company_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        company_name=company_name,
    )
    await oauth_service.delete_pending_session(user_id)

    logger.info(f"Manual complete: stored tokens for user {user_id}, company {decoded_company_id}")

    return JSONResponse(content={
        "success": True,
        "company_id": decoded_company_id,
        "company_name": company_name,
    })


# ---------------------------------------------------------------------------
# Pay-parts meta & mapping
# ---------------------------------------------------------------------------

@router.get("/payparts-meta")
async def get_payparts_meta(
    company_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Fetch the payPartsMeta list from Danløn for the connected company.

    Returns the available pay-part codes together with which fields
    (units, rate, amount) are allowed for each code.
    When the Danløn API is unreachable (demo environment without a live
    connection) the demo defaults are returned instead.
    """
    if not user_id:
        user_id = "demo_user"

    # Resolve company_id from the stored connection if not provided
    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn")

    try:
        api = get_danlon_api_service(user_id, company_id)
        meta = await api.get_pay_parts_meta()
        return JSONResponse(content={"pay_parts_meta": meta})
    except Exception as e:
        logger.warning(f"Could not fetch payPartsMeta from Danløn ({e}); returning demo defaults")
        # Return the known demo pay parts so the frontend can still render the mapping UI
        return JSONResponse(content={
            "pay_parts_meta": [
                {"code": "T1", "description": "Timeløn 1", "unitsAllowed": True, "rateAllowed": False, "amountAllowed": True},
                {"code": "T2", "description": "Timeløn 2", "unitsAllowed": True, "rateAllowed": True, "amountAllowed": True},
                {"code": "T3", "description": "Timeløn 3", "unitsAllowed": False, "rateAllowed": False, "amountAllowed": False},
            ],
            "source": "demo_fallback",
        })


@router.get("/paycode-mapping")
async def get_paycode_mapping(
    company_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Return the saved pay-code mapping for normal / overtime / callout.
    If no mapping has been saved yet, the demo defaults (T1/T2/T3) are returned.
    """
    if not user_id:
        user_id = "demo_user"

    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        return JSONResponse(content={
            "normal_code": "T1",
            "overtime_code": "T2",
            "callout_code": "T3",
            "is_default": True,
        })

    async with async_session_maker() as session:
        stmt = select(DanlonPayCodeMapping).where(
            DanlonPayCodeMapping.user_id == user_id,
            DanlonPayCodeMapping.company_id == company_id,
        )
        result = await session.execute(stmt)
        mapping = result.scalar_one_or_none()

    if mapping:
        return JSONResponse(content={
            "normal_code": mapping.normal_code,
            "overtime_code": mapping.overtime_code,
            "callout_code": mapping.callout_code,
            "is_default": False,
        })

    return JSONResponse(content={
        "normal_code": "T1",
        "overtime_code": "T2",
        "callout_code": "T3",
        "is_default": True,
    })


@router.put("/paycode-mapping")
async def save_paycode_mapping(request: Request):
    """
    Save the pay-code mapping for normal / overtime / callout.

    Body (JSON):
        {
            "normal_code":   "T1",
            "overtime_code": "T2",
            "callout_code":  "T3",
            "company_id":    "<optional>",
            "user_id":       "<optional>"
        }
    """
    body = await request.json()
    user_id = body.get("user_id") or "demo_user"
    company_id = body.get("company_id") or None

    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn")

    normal_code = body.get("normal_code", "T1").strip()
    overtime_code = body.get("overtime_code", "T2").strip()
    callout_code = body.get("callout_code", "T3").strip()

    async with async_session_maker() as session:
        stmt = select(DanlonPayCodeMapping).where(
            DanlonPayCodeMapping.user_id == user_id,
            DanlonPayCodeMapping.company_id == company_id,
        )
        result = await session.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            mapping.normal_code = normal_code
            mapping.overtime_code = overtime_code
            mapping.callout_code = callout_code
            mapping.updated_at = datetime.utcnow()
        else:
            mapping = DanlonPayCodeMapping(
                user_id=user_id,
                company_id=company_id,
                normal_code=normal_code,
                overtime_code=overtime_code,
                callout_code=callout_code,
            )
            session.add(mapping)

        await session.commit()

    logger.info(f"Saved pay-code mapping for user {user_id}, company {company_id}: "
                f"normal={normal_code}, overtime={overtime_code}, callout={callout_code}")

    return JSONResponse(content={
        "success": True,
        "normal_code": normal_code,
        "overtime_code": overtime_code,
        "callout_code": callout_code,
    })


# ---------------------------------------------------------------------------
# Employee mapping endpoints
# ---------------------------------------------------------------------------

@router.get("/employees")
async def get_danlon_employees(
    user_id: Optional[str] = Query(default="demo_user"),
    company_id: Optional[str] = Query(default=None),
):
    """
    Return the list of employees registered in Danløn for the connected company.
    Used to populate the employee-mapping dropdown.
    """
    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn. Please connect first.")

    api = get_danlon_api_service(user_id, company_id)
    try:
        employees = await api.get_employees(include_deleted=False)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch employees from Danløn: {e}")

    return JSONResponse(content={"employees": employees})


@router.get("/employee-mapping")
async def get_employee_mapping(
    user_id: Optional[str] = Query(default="demo_user"),
    company_id: Optional[str] = Query(default=None),
):
    """
    Return saved FTZ → Danløn employee mappings (explicit + fallback) for this user/company.
    """
    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn. Please connect first.")

    async with async_session_maker() as session:
        stmt = select(DanlonEmployeeMapping).where(
            DanlonEmployeeMapping.user_id == user_id,
            DanlonEmployeeMapping.company_id == company_id,
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    mappings = []
    fallback = None
    for row in rows:
        if row.is_fallback:
            fallback = {
                "danlon_employee_id": row.danlon_employee_id,
                "danlon_employee_name": row.danlon_employee_name,
            }
        else:
            mappings.append({
                "ftz_employee_name": row.ftz_employee_name,
                "danlon_employee_id": row.danlon_employee_id,
                "danlon_employee_name": row.danlon_employee_name,
            })

    return JSONResponse(content={"mappings": mappings, "fallback": fallback})


@router.put("/employee-mapping")
async def save_employee_mapping(
    request: Request,
    user_id: Optional[str] = Query(default="demo_user"),
    company_id: Optional[str] = Query(default=None),
):
    """
    Save FTZ → Danløn employee mappings for this user/company.

    Body:
    {
      "mappings": [
        { "ftz_employee_name": "...", "danlon_employee_id": "...", "danlon_employee_name": "..." }
      ],
      "fallback": { "danlon_employee_id": "...", "danlon_employee_name": "..." } | null
    }
    """
    body = await request.json()
    new_mappings: List[Dict[str, Any]] = body.get("mappings", [])
    fallback_data: Optional[Dict[str, Any]] = body.get("fallback")

    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn. Please connect first.")

    async with async_session_maker() as session:
        # Delete all existing rows for this user/company
        from sqlalchemy import delete as sa_delete
        await session.execute(
            sa_delete(DanlonEmployeeMapping).where(
                DanlonEmployeeMapping.user_id == user_id,
                DanlonEmployeeMapping.company_id == company_id,
            )
        )

        # Insert explicit mappings
        for m in new_mappings:
            ftz_name = (m.get("ftz_employee_name") or "").strip()
            danlon_id = (m.get("danlon_employee_id") or "").strip()
            danlon_name = (m.get("danlon_employee_name") or "").strip()
            if ftz_name and danlon_id:
                session.add(DanlonEmployeeMapping(
                    user_id=user_id,
                    company_id=company_id,
                    ftz_employee_name=ftz_name,
                    danlon_employee_id=danlon_id,
                    danlon_employee_name=danlon_name,
                    is_fallback=False,
                ))

        # Insert fallback row if provided
        if fallback_data and fallback_data.get("danlon_employee_id"):
            session.add(DanlonEmployeeMapping(
                user_id=user_id,
                company_id=company_id,
                ftz_employee_name=None,
                danlon_employee_id=fallback_data["danlon_employee_id"],
                danlon_employee_name=fallback_data.get("danlon_employee_name", ""),
                is_fallback=True,
            ))

        await session.commit()

    logger.info(
        f"Saved employee mapping for user {user_id}, company {company_id}: "
        f"{len(new_mappings)} explicit, fallback={'yes' if fallback_data else 'no'}"
    )

    return JSONResponse(content={"success": True})


# ---------------------------------------------------------------------------
# Sync processed time-registration data to Danløn as payparts
# ---------------------------------------------------------------------------

def _sum_overtime(breakdown: Dict[str, Any]) -> float:
    """Return total overtime hours by summing all breakdown categories."""
    return sum(
        breakdown.get(k, 0.0) or 0.0
        for k in (
            "ot_weekday_hour_1_2",
            "ot_weekday_hour_3_4",
            "ot_weekday_hour_5_plus",
            "ot_weekday_scheduled_day",
            "ot_weekday_scheduled_night",
            "ot_dayoff_day",
            "ot_dayoff_night",
            "ot_saturday_day",
            "ot_saturday_night",
            "ot_sunday_before_noon",
            "ot_sunday_after_noon",
        )
    )


@router.post("/sync/{session_id}")
async def sync_to_danlon(
    session_id: str,
    user_id: Optional[str] = Query(default="demo_user"),
    company_id: Optional[str] = Query(default=None),
):
    """
    Sync a processed preview session to Danløn as payparts.

    Reads the cached preview data produced by POST /api/preview, maps each
    day row to one or more payparts (normal hours, overtime, call-out) using
    the saved pay-code mapping, matches workers by name to Danløn employees,
    and submits everything via createPayParts.

    Path parameter:
    - session_id: Session ID returned by POST /api/preview

    Query parameters:
    - user_id:    Defaults to "demo_user"
    - company_id: Optional — resolved from stored connection if omitted
    """
    # Import here to avoid circular imports at module load time
    from app.routers.upload import preview_cache

    # ------------------------------------------------------------------
    # 1. Resolve cached preview data
    # ------------------------------------------------------------------
    if session_id not in preview_cache:
        raise HTTPException(
            status_code=404,
            detail="Preview session not found. Please upload / fetch data first.",
        )

    cached = preview_cache[session_id]
    outputs: List[Any] = cached.get("outputs", [])

    if not outputs:
        raise HTTPException(status_code=400, detail="No processed data in session.")

    # ------------------------------------------------------------------
    # 2. Resolve company_id from stored connection if not provided
    # ------------------------------------------------------------------
    if not company_id:
        oauth_service = get_danlon_oauth_service()
        all_tokens = await oauth_service.get_all_tokens_for_user(user_id)
        if all_tokens:
            company_id = all_tokens[0]["company_id"]

    if not company_id:
        raise HTTPException(status_code=400, detail="Not connected to Danløn. Please connect first.")

    # ------------------------------------------------------------------
    # 3. Load pay-code mapping and employee mapping
    # ------------------------------------------------------------------
    async with async_session_maker() as session:
        stmt = select(DanlonPayCodeMapping).where(
            DanlonPayCodeMapping.user_id == user_id,
            DanlonPayCodeMapping.company_id == company_id,
        )
        result = await session.execute(stmt)
        mapping = result.scalar_one_or_none()

        emp_stmt = select(DanlonEmployeeMapping).where(
            DanlonEmployeeMapping.user_id == user_id,
            DanlonEmployeeMapping.company_id == company_id,
        )
        emp_result = await session.execute(emp_stmt)
        emp_mapping_rows = emp_result.scalars().all()

    normal_code = mapping.normal_code if mapping else "T1"
    overtime_code = mapping.overtime_code if mapping else "T2"
    callout_code = mapping.callout_code if mapping else "T3"

    # Build case-insensitive FTZ name → Danløn employee id lookup from saved mappings
    employee_id_by_ftz_name: Dict[str, str] = {}
    fallback_employee_id: Optional[str] = None
    for emp_row in emp_mapping_rows:
        if emp_row.is_fallback:
            fallback_employee_id = emp_row.danlon_employee_id
        elif emp_row.ftz_employee_name:
            employee_id_by_ftz_name[emp_row.ftz_employee_name.lower()] = emp_row.danlon_employee_id

    logger.info(
        f"Sync: codes normal={normal_code}, overtime={overtime_code}, callout={callout_code}; "
        f"employee mappings={len(employee_id_by_ftz_name)}, fallback={'yes' if fallback_employee_id else 'no'}"
    )

    # ------------------------------------------------------------------
    # 4. Fetch Danløn employees and build name → id map
    # ------------------------------------------------------------------
    api = get_danlon_api_service(user_id, company_id)

    try:
        employees = await api.get_employees(include_deleted=False)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch employees from Danløn: {e}")

    # Build case-insensitive name → employee lookup
    employee_by_name: Dict[str, Dict[str, Any]] = {}
    for emp in employees:
        full_name = emp.get("name", "").strip()
        if full_name:
            employee_by_name[full_name.lower()] = emp
        # Also index by domainId for potential future use
        if emp.get("domainId"):
            employee_by_name[str(emp["domainId"]).lower()] = emp

    # Build id → employee lookup for resolving mapped/fallback IDs
    employee_by_id: Dict[str, Dict[str, Any]] = {
        emp["id"]: emp for emp in employees if emp.get("id")
    }

    # ------------------------------------------------------------------
    # 5. Build payparts list from DailyOutput rows
    # ------------------------------------------------------------------
    payparts: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    unmatched_workers: set = set()

    for row in outputs:
        row_dict = row.model_dump() if hasattr(row, "model_dump") else dict(row)

        worker_name: str = row_dict.get("worker", "").strip()
        date_str: str = row_dict.get("date", "")
        normal_hours: float = float(row_dict.get("normal_hours", 0.0) or 0.0)
        breakdown = row_dict.get("overtime_breakdown", {}) or {}
        total_overtime: float = round(_sum_overtime(breakdown), 4)
        call_out_applied: bool = bool(row_dict.get("call_out_applied", False))
        call_out_payment: float = float(row_dict.get("call_out_payment", 0.0) or 0.0)

        # Skip days with no relevant data
        if normal_hours <= 0 and total_overtime <= 0 and not call_out_applied:
            continue

        # Resolve Danløn employee — three-step lookup:
        # 1. Name match against Danløn employee list
        employee = employee_by_name.get(worker_name.lower())
        employee_id: Optional[str] = employee["id"] if employee else None

        # 2. Explicit mapping table lookup (FTZ name → Danløn employee id)
        if not employee_id:
            mapped_id = employee_id_by_ftz_name.get(worker_name.lower())
            if mapped_id:
                employee_id = mapped_id

        # 3. Fallback employee (catches all remaining unmatched workers)
        if not employee_id and fallback_employee_id:
            employee_id = fallback_employee_id

        if not employee_id:
            unmatched_workers.add(worker_name)
            skipped.append({
                "worker": worker_name,
                "date": date_str,
                "reason": f"No matching Danløn employee found for '{worker_name}'",
            })
            continue

        # Normal hours paypart
        if normal_hours > 0:
            payparts.append({
                "employeeId": employee_id,
                "code": normal_code,
                "units": round(normal_hours, 4),
            })

        # Overtime paypart
        if total_overtime > 0:
            payparts.append({
                "employeeId": employee_id,
                "code": overtime_code,
                "units": total_overtime,
            })

        # Call-out paypart (fixed amount, no units)
        if call_out_applied and call_out_payment > 0:
            payparts.append({
                "employeeId": employee_id,
                "code": callout_code,
                "amount": round(call_out_payment, 2),
            })

    if not payparts:
        return JSONResponse(
            content={
                "success": False,
                "message": "No payparts to submit. Check that employees match Danløn and data contains hours.",
                "summary": {"created": 0, "skipped": len(skipped), "errors": 0},
                "skipped_items": skipped,
                "errors": [],
                "unmatched_workers": list(unmatched_workers),
            }
        )

    # ------------------------------------------------------------------
    # 6. Submit to Danløn
    # ------------------------------------------------------------------
    try:
        danlon_result = await api.create_payparts(payparts)
    except Exception as e:
        logger.error(f"Danløn createPayParts failed: {e}")
        raise HTTPException(status_code=502, detail=f"Danløn API error: {e}")

    created = danlon_result.get("createdPayParts", [])
    logger.info(f"Sync complete: {len(created)} payparts created, {len(skipped)} skipped")

    return JSONResponse(content={
        "success": True,
        "message": f"Successfully created {len(created)} paypart(s) in Danløn",
        "summary": {
            "created": len(created),
            "skipped": len(skipped),
            "errors": 0,
        },
        "created_payparts": created,
        "skipped_items": skipped,
        "errors": [],
        "unmatched_workers": list(unmatched_workers),
    })
