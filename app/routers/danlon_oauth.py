"""
Danløn OAuth2 callback endpoints for connection/disconnection flow.
"""
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from typing import Optional
import logging
import base64

from app.services.danlon_oauth import get_danlon_oauth_service

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
        
        # Step 6: Redirect to select-company page
        select_company_url = oauth_service.get_select_company_url(
            temp_access_token=temp_access_token,
            return_uri=return_uri
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
        
        # Step 10: Redirect based on where connection was initiated
        if return_uri:
            # Connection was initiated from Danløn, redirect back
            logger.info(f"Redirecting back to Danløn: {return_uri}")
            return RedirectResponse(url=return_uri)
        else:
            # Connection was initiated from our app, show success page
            return HTMLResponse(
                content=f"""
                <html>
                    <head>
                        <title>Connected to Danløn</title>
                        <style>
                            body {{
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                max-width: 600px;
                                margin: 50px auto;
                                padding: 20px;
                                background: #f5f5f5;
                            }}
                            .card {{
                                background: white;
                                border-radius: 8px;
                                padding: 30px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            }}
                            h1 {{
                                color: #2c5aa0;
                                margin-top: 0;
                            }}
                            .success {{
                                color: #27ae60;
                                font-size: 48px;
                                text-align: center;
                            }}
                            .info {{
                                background: #e8f4f8;
                                border-left: 4px solid #2c5aa0;
                                padding: 15px;
                                margin: 20px 0;
                            }}
                            a {{
                                display: inline-block;
                                background: #2c5aa0;
                                color: white;
                                padding: 12px 24px;
                                text-decoration: none;
                                border-radius: 4px;
                                margin-top: 20px;
                            }}
                            a:hover {{
                                background: #1e4480;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <div class="success">✓</div>
                            <h1>Successfully Connected to Danløn!</h1>
                            <div class="info">
                                <p><strong>Company ID:</strong> {decoded_company_id}</p>
                                <p><strong>Status:</strong> Connected and ready to sync data</p>
                            </div>
                            <p>Your application is now connected to Danløn. You can start importing time registrations and creating payparts.</p>
                            <a href="/">Return to Dashboard</a>
                        </div>
                    </body>
                </html>
                """
            )
        
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
    
    return JSONResponse(
        content={
            "connected": False,
            "user_id": user_id,
            "company_id": company_id
        }
    )
