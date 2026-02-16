"""
Test endpoints for Danløn integration - for demo environment testing only.
These endpoints allow manual token injection when the demo environment has no companies.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime, timedelta

from app.services.danlon_oauth import get_danlon_oauth_service
from app.database import get_db_session
from app.models.danlon_tokens import DanlonToken

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/danlon/test", tags=["Danløn Testing"])


class ManualTokenInput(BaseModel):
    """Manual token input for testing when demo environment has no companies."""
    access_token: str
    refresh_token: str
    company_id: str
    company_name: Optional[str] = "Demo Company"
    user_id: str = "demo_user"
    expires_in: int = 300  # 5 minutes default


@router.post("/inject-tokens")
async def inject_tokens_manually(token_input: ManualTokenInput):
    """
    Manually inject Danløn tokens into database for testing.
    
    Use this when the demo environment has no companies to select from.
    
    **How to use:**
    1. Complete OAuth flow up to the select-company page
    2. If no companies available, use Bruno or API calls to get tokens manually
    3. POST the tokens to this endpoint
    4. Tokens will be stored in database as if OAuth flow completed normally
    5. You can now test sync and other features
    
    **Example:**
    ```json
    {
      "access_token": "eyJhbGc...",
      "refresh_token": "eyJhbGc...",
      "company_id": "company-123",
      "company_name": "SimplySolutions Demo",
      "user_id": "demo_user",
      "expires_in": 300
    }
    ```
    """
    try:
        logger.info(f"Manual token injection requested for company_id: {token_input.company_id}")
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(seconds=token_input.expires_in)
        
        # Create or update token in database
        async with get_db_session() as session:
            # Check if token already exists for this user and company
            from sqlalchemy import select
            stmt = select(DanlonToken).where(
                DanlonToken.user_id == token_input.user_id,
                DanlonToken.company_id == token_input.company_id
            )
            result = await session.execute(stmt)
            existing_token = result.scalar_one_or_none()
            
            if existing_token:
                # Update existing token
                logger.info(f"Updating existing token for user {token_input.user_id}, company {token_input.company_id}")
                existing_token.access_token = token_input.access_token
                existing_token.refresh_token = token_input.refresh_token
                existing_token.expires_at = expires_at
                existing_token.company_name = token_input.company_name
                existing_token.updated_at = datetime.utcnow()
            else:
                # Create new token
                logger.info(f"Creating new token for user {token_input.user_id}, company {token_input.company_id}")
                new_token = DanlonToken(
                    user_id=token_input.user_id,
                    company_id=token_input.company_id,
                    company_name=token_input.company_name,
                    access_token=token_input.access_token,
                    refresh_token=token_input.refresh_token,
                    expires_at=expires_at
                )
                session.add(new_token)
            
            await session.commit()
        
        logger.info(f"✓ Tokens successfully injected into database")
        
        return {
            "success": True,
            "message": "Tokens successfully stored in database",
            "user_id": token_input.user_id,
            "company_id": token_input.company_id,
            "company_name": token_input.company_name,
            "expires_at": expires_at.isoformat(),
            "next_steps": [
                "Check connection status at /danlon/status",
                "Test sync functionality in Settings > Danløn Integration",
                "Or use /danlon/example/company-info endpoint"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to inject tokens: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to store tokens: {str(e)}")


@router.post("/refresh-injected-token")
async def refresh_injected_token(company_id: str, user_id: str = "demo_user"):
    """
    Refresh an injected token using the refresh_token stored in database.
    
    Use this to test token refresh functionality with manually injected tokens.
    """
    try:
        oauth_service = get_danlon_oauth_service()
        
        # Get the stored refresh token
        async with get_db_session() as session:
            from sqlalchemy import select
            stmt = select(DanlonToken).where(
                DanlonToken.user_id == user_id,
                DanlonToken.company_id == company_id
            )
            result = await session.execute(stmt)
            token_record = result.scalar_one_or_none()
            
            if not token_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"No tokens found for user {user_id} and company {company_id}"
                )
            
            # Use the OAuth service to refresh the token
            new_tokens = await oauth_service.refresh_access_token(token_record.refresh_token)
            
            # Update the token in database
            token_record.access_token = new_tokens["access_token"]
            if "refresh_token" in new_tokens:
                token_record.refresh_token = new_tokens["refresh_token"]
            token_record.expires_at = datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 300))
            token_record.updated_at = datetime.utcnow()
            
            await session.commit()
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "expires_at": token_record.expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")


@router.delete("/clear-tokens")
async def clear_test_tokens(company_id: Optional[str] = None, user_id: str = "demo_user"):
    """
    Clear test tokens from database.
    
    If company_id is provided, only clear tokens for that company.
    Otherwise, clear all tokens for the user.
    """
    try:
        async with get_db_session() as session:
            from sqlalchemy import select, delete
            
            if company_id:
                stmt = delete(DanlonToken).where(
                    DanlonToken.user_id == user_id,
                    DanlonToken.company_id == company_id
                )
                logger.info(f"Clearing tokens for user {user_id}, company {company_id}")
            else:
                stmt = delete(DanlonToken).where(DanlonToken.user_id == user_id)
                logger.info(f"Clearing all tokens for user {user_id}")
            
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            
        return {
            "success": True,
            "message": f"Cleared {deleted_count} token record(s)",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear tokens: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear tokens: {str(e)}")
