"""
Danløn OAuth2 service for handling authentication and token management.
Implements the complete OAuth2 authorization code flow with PKCE.
"""
import os
import base64
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.danlon_tokens import DanlonToken

logger = logging.getLogger(__name__)


class DanlonOAuthService:
    """Manages OAuth2 authentication flow and token lifecycle for Danløn API."""
    
    def __init__(self):
        # Environment-based configuration
        self.environment = os.getenv("DANLON_ENVIRONMENT", "demo")  # "demo" or "prod"
        
        # Client credentials
        self.client_id = os.getenv("DANLON_CLIENT_ID", "partner-showcase")
        self.client_secret = os.getenv("DANLON_CLIENT_SECRET", "")
        
        # Base URLs - different for demo vs prod
        if self.environment == "prod":
            self.auth_base = "https://auth.lessor.dk/auth/realms/danlon"
            self.marketplace_base = "https://danlon.lessor.dk"
            self.graphql_url = "https://api.danlon.dk/graphql"
        else:  # demo
            self.auth_base = "https://auth.lessor.dk/auth/realms/danlon-integration-demo"
            self.marketplace_base = "https://danlon-integration-demo.lessor.dk"
            self.graphql_url = "https://api-demo.danlon.dk/graphql"
        
        # OAuth2 endpoints
        self.auth_url = f"{self.auth_base}/protocol/openid-connect/auth"
        self.token_url = f"{self.auth_base}/protocol/openid-connect/token"
        self.revoke_url = f"{self.auth_base}/protocol/openid-connect/revoke"
        
        # Marketplace endpoints
        self.select_company_url = f"{self.marketplace_base}/select-company"
        self.code2token_url = f"{self.marketplace_base}/code2token"
        
        # OAuth2 settings
        self.scope = "openid email offline_access"
        
        # Callback URLs - should be set via environment or defaults to localhost
        self.app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        self.redirect_uri = f"{self.app_base_url}/danlon/callback"
        self.success_uri = f"{self.app_base_url}/danlon/success"
    
    def get_authorization_url(self, return_uri: Optional[str] = None) -> str:
        """
        Generate the OAuth2 authorization URL to redirect the user to Danløn.
        
        This is Step 2 in the connection flow.
        
        Args:
            return_uri: Optional URI to return to after connection (used when initiated from Danløn)
            
        Returns:
            Full authorization URL to redirect user to
        """
        redirect_uri = self.redirect_uri
        if return_uri:
            redirect_uri = f"{self.redirect_uri}?return_uri={return_uri}"
        
        params = {
            "client_id": self.client_id,
            "scope": self.scope,
            "response_type": "code",
            "redirect_uri": redirect_uri
        }
        
        url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"Generated authorization URL for client_id: {self.client_id}")
        return url
    
    async def exchange_code_for_temp_token(
        self, 
        code: str, 
        redirect_uri: str
    ) -> Tuple[str, str]:
        """
        Exchange authorization code for temporary access and refresh tokens.
        
        This is Step 4 in the connection flow (called code2token in docs, but this is the first exchange).
        
        Args:
            code: Authorization code from OAuth2 callback
            redirect_uri: The exact redirect_uri used in the authorization request
            
        Returns:
            Tuple of (access_token, refresh_token)
            
        Raises:
            Exception if token exchange fails
        """
        if not self.client_secret:
            raise Exception("DANLON_CLIENT_SECRET environment variable not set")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
            
            logger.info(f"Exchanging code for temporary token with redirect_uri: {redirect_uri}")
            
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to exchange code for token: {response.text}")
            
            token_data = response.json()
            
            if "access_token" not in token_data:
                raise Exception("No access_token in response")
            
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token", "")
            
            logger.info("Successfully exchanged code for temporary tokens")
            return access_token, refresh_token
    
    def get_select_company_url(
        self, 
        temp_access_token: str, 
        return_uri: Optional[str] = None
    ) -> str:
        """
        Generate the select-company URL to redirect user to.
        
        This is Step 6 in the connection flow.
        
        Args:
            temp_access_token: Temporary access token from step 4
            return_uri: Optional URI to include in the flow
            
        Returns:
            Full select-company URL
        """
        # Base64 encode the temporary access token
        encoded_token = base64.b64encode(temp_access_token.encode()).decode()
        
        params = {
            "token": encoded_token,
            "return_uri": self.success_uri
        }
        
        if return_uri:
            params["return_uri"] = f"{self.success_uri}?return_uri={return_uri}"
        
        url = f"{self.select_company_url}?{urlencode(params)}"
        logger.info("Generated select-company URL")
        return url
    
    async def exchange_code_for_final_tokens(
        self, 
        code: str
    ) -> Dict[str, Any]:
        """
        Exchange the code from select-company for final access and refresh tokens.
        
        This is Step 8 in the connection flow - the code2token endpoint call.
        
        Args:
            code: Code returned from select-company page
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception if exchange fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.code2token_url}?code={code}"
            
            logger.info("Exchanging code for final tokens via code2token endpoint")
            
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.error(f"code2token failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get final tokens: {response.text}")
            
            token_data = response.json()
            
            if "access_token" not in token_data or "refresh_token" not in token_data:
                raise Exception("Missing tokens in code2token response")
            
            logger.info("Successfully obtained final tokens")
            return token_data
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using the refresh token.
        
        This should be called regularly as access tokens expire after 5 minutes.
        
        Args:
            refresh_token: Long-lived refresh token
            
        Returns:
            Dictionary containing new access_token, refresh_token (may be rotated), expires_in
            
        Raises:
            Exception if refresh fails
        """
        if not self.client_secret:
            raise Exception("DANLON_CLIENT_SECRET environment variable not set")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
            
            logger.info("Refreshing access token")
            
            response = await client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to refresh token: {response.text}")
            
            token_data = response.json()
            
            if "access_token" not in token_data:
                raise Exception("No access_token in refresh response")
            
            logger.info("Successfully refreshed access token")
            return token_data
    
    async def revoke_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token (disconnect).
        
        This is Step 5 - Scenario 2 (user disconnects from your app).
        
        Args:
            refresh_token: The refresh token to revoke
            
        Returns:
            True if revocation successful
            
        Raises:
            Exception if revocation fails
        """
        if not self.client_secret:
            raise Exception("DANLON_CLIENT_SECRET environment variable not set")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "token": refresh_token
            }
            
            logger.info("Revoking refresh token")
            
            response = await client.post(
                self.revoke_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token revocation failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to revoke token: {response.text}")
            
            logger.info("Successfully revoked refresh token")
            return True
    
    async def query_graphql(
        self, 
        access_token: str, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Danløn API.
        
        Args:
            access_token: Valid access token
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response data
            
        Raises:
            Exception if query fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            
            logger.info("Executing GraphQL query")
            
            response = await client.post(
                self.graphql_url,
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"GraphQL query failed: {response.status_code} - {response.text}")
                raise Exception(f"GraphQL query failed: {response.text}")
            
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                raise Exception(f"GraphQL errors: {data['errors']}")
            
            logger.info("GraphQL query successful")
            return data
    
    # Token storage methods (database-backed)
    
    async def store_tokens(
        self, 
        user_id: str, 
        company_id: str,
        access_token: str, 
        refresh_token: str,
        expires_in: int = 300,
        company_name: Optional[str] = None
    ) -> None:
        """
        Store tokens for a user/company in the database.
        
        Args:
            user_id: User identifier
            company_id: Danløn company ID
            access_token: Access token
            refresh_token: Refresh token
            expires_in: Token expiry in seconds (default 300 = 5 minutes)
            company_name: Optional company name for display
        """
        async with async_session_maker() as session:
            try:
                # Check if token already exists
                stmt = select(DanlonToken).where(
                    DanlonToken.user_id == user_id,
                    DanlonToken.company_id == company_id
                )
                result = await session.execute(stmt)
                existing_token = result.scalar_one_or_none()
                
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                if existing_token:
                    # Update existing token
                    existing_token.access_token = access_token
                    existing_token.refresh_token = refresh_token
                    existing_token.expires_at = expires_at
                    existing_token.updated_at = datetime.utcnow()
                    if company_name:
                        existing_token.company_name = company_name
                    logger.info(f"Updated tokens for user {user_id}, company {company_id}")
                else:
                    # Create new token
                    new_token = DanlonToken(
                        user_id=user_id,
                        company_id=company_id,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        company_name=company_name,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_token)
                    logger.info(f"Created new tokens for user {user_id}, company {company_id}")
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store tokens: {e}")
                raise
    
    async def get_tokens(self, user_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve tokens for a user/company from the database.
        
        Args:
            user_id: User identifier
            company_id: Danløn company ID
            
        Returns:
            Token data or None if not found
        """
        async with async_session_maker() as session:
            try:
                stmt = select(DanlonToken).where(
                    DanlonToken.user_id == user_id,
                    DanlonToken.company_id == company_id
                )
                result = await session.execute(stmt)
                token = result.scalar_one_or_none()
                
                if token:
                    return {
                        "access_token": token.access_token,
                        "refresh_token": token.refresh_token,
                        "company_id": token.company_id,
                        "company_name": token.company_name,
                        "expires_at": token.expires_at,
                        "created_at": token.created_at
                    }
                return None
                
            except Exception as e:
                logger.error(f"Failed to get tokens: {e}")
                return None
    
    async def delete_tokens(self, user_id: str, company_id: str) -> None:
        """
        Delete tokens for a user/company from the database.
        
        Args:
            user_id: User identifier
            company_id: Danløn company ID
        """
        async with async_session_maker() as session:
            try:
                stmt = delete(DanlonToken).where(
                    DanlonToken.user_id == user_id,
                    DanlonToken.company_id == company_id
                )
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Deleted tokens for user {user_id}, company {company_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete tokens: {e}")
                raise
    
    async def get_valid_access_token(
        self, 
        user_id: str, 
        company_id: str
    ) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            user_id: User identifier
            company_id: Danløn company ID
            
        Returns:
            Valid access token or None if no tokens stored
        """
        tokens = await self.get_tokens(user_id, company_id)
        if not tokens:
            return None
        
        # Check if token is still valid (with 1 minute buffer)
        if datetime.utcnow() < (tokens["expires_at"] - timedelta(minutes=1)):
            return tokens["access_token"]
        
        # Token expired, refresh it
        try:
            new_tokens = await self.refresh_access_token(tokens["refresh_token"])
            
            # Store new tokens
            await self.store_tokens(
                user_id=user_id,
                company_id=company_id,
                access_token=new_tokens["access_token"],
                refresh_token=new_tokens.get("refresh_token", tokens["refresh_token"]),
                expires_in=new_tokens.get("expires_in", 300),
                company_name=tokens.get("company_name")
            )
            
            return new_tokens["access_token"]
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return None


# Singleton instance
_danlon_oauth_service: Optional[DanlonOAuthService] = None


def get_danlon_oauth_service() -> DanlonOAuthService:
    """Get the singleton Danløn OAuth service instance."""
    global _danlon_oauth_service
    if _danlon_oauth_service is None:
        _danlon_oauth_service = DanlonOAuthService()
    return _danlon_oauth_service
