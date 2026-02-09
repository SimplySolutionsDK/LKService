"""
Danlon OAuth2 authentication service.
Manages the OAuth2 lifecycle including authorization, token exchange, refresh, and revocation.
"""
import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.services.danlon_token_store import get_token_store


class DanlonAuthService:
    """Manages Danlon OAuth2 authentication lifecycle."""
    
    def __init__(self):
        self.oauth_server_root = os.getenv("DANLON_OAUTH_SERVER_ROOT", "https://auth.lessor.dk")
        self.realm = os.getenv("DANLON_OAUTH_REALM", "danlon-integration-demo")
        self.client_id = os.getenv("DANLON_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("DANLON_OAUTH_CLIENT_SECRET", "")
        self.scope = os.getenv("DANLON_OAUTH_SCOPE", "openid email offline_access")
        self.marketplace_endpoint = os.getenv("DANLON_MARKETPLACE_ENDPOINT", "")
        
        self.token_store = get_token_store()
        
        # Cache for access token and expiry
        self._cached_access_token: Optional[str] = None
        self._cached_token_expires_at: Optional[datetime] = None
    
    def get_oauth2_url(self, endpoint: str) -> str:
        """
        Build OAuth2 endpoint URL.
        
        Args:
            endpoint: The OpenID Connect endpoint (e.g., 'auth', 'token', 'revoke')
            
        Returns:
            Full URL to the OAuth2 endpoint
        """
        return f"{self.oauth_server_root}/auth/realms/{self.realm}/protocol/openid-connect/{endpoint}"
    
    def build_authorize_url(self, redirect_uri: str, return_uri: Optional[str] = None) -> str:
        """
        Build the OAuth2 authorization URL (Step 2).
        
        Args:
            redirect_uri: Callback URL where OAuth2 server will redirect after consent
            return_uri: Optional return URI to pass through the flow
            
        Returns:
            Full authorization URL to redirect the user's browser to
        """
        # Include return_uri in redirect_uri as a query parameter if provided
        final_redirect_uri = redirect_uri
        if return_uri:
            separator = "&" if "?" in redirect_uri else "?"
            final_redirect_uri = f"{redirect_uri}{separator}return_uri={return_uri}"
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": self.scope,
            "redirect_uri": final_redirect_uri,
        }
        
        auth_url = self.get_oauth2_url("auth")
        return f"{auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(
        self, 
        code: str, 
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for temporary access token (Step 4).
        
        Args:
            code: Authorization code from OAuth2 callback
            redirect_uri: Same redirect_uri used in authorization request
            
        Returns:
            Token response with access_token, refresh_token, expires_in
            
        Raises:
            httpx.HTTPError: If token exchange fails
        """
        token_url = self.get_oauth2_url("token")
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def exchange_marketplace_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange marketplace code for final tokens (Step 8).
        
        Args:
            code: Code from marketplace select-company callback
            
        Returns:
            Final token response with access_token, refresh_token
            
        Raises:
            httpx.HTTPError: If code exchange fails
        """
        if not self.marketplace_endpoint:
            raise ValueError("DANLON_MARKETPLACE_ENDPOINT not configured")
        
        code2token_url = f"{self.marketplace_endpoint}/code2token/{code}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(code2token_url)
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Token response with new access_token (and possibly new refresh_token)
            
        Raises:
            httpx.HTTPError: If token refresh fails
        """
        token_url = self.get_oauth2_url("token")
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def revoke_token(self, refresh_token: str) -> None:
        """
        Revoke refresh token (Scenario 2 disconnect).
        
        Args:
            refresh_token: Refresh token to revoke
            
        Raises:
            httpx.HTTPError: If token revocation fails
        """
        revoke_url = self.get_oauth2_url("revoke")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token": refresh_token,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                revoke_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
    
    async def get_valid_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token ready to use
            
        Raises:
            Exception: If no tokens are stored or refresh fails
        """
        # Check if we have a cached token that's still valid
        if self._cached_access_token and self._cached_token_expires_at:
            # Refresh if expires in less than 5 minutes
            if datetime.now() < (self._cached_token_expires_at - timedelta(minutes=5)):
                return self._cached_access_token
        
        # Get stored tokens
        stored = self.token_store.get_tokens()
        if not stored or "refresh_token" not in stored:
            raise Exception("No Danlon tokens stored. Please connect to Danlon first.")
        
        # Refresh the access token
        token_response = await self.refresh_access_token(stored["refresh_token"])
        
        # Update cache
        self._cached_access_token = token_response["access_token"]
        if "expires_in" in token_response:
            expires_in = int(token_response["expires_in"])
            self._cached_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Update stored tokens if refresh token was rotated
        if "refresh_token" in token_response:
            self.token_store.save_tokens(
                access_token=token_response["access_token"],
                refresh_token=token_response["refresh_token"],
                company_id=stored.get("company_id", ""),
                expires_in=token_response.get("expires_in")
            )
        
        return self._cached_access_token
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status.
        
        Returns:
            Dictionary with connected status, company_id, and timestamps
        """
        stored = self.token_store.get_tokens()
        
        if not stored or "refresh_token" not in stored:
            return {
                "connected": False,
                "company_id": None,
                "connected_at": None,
            }
        
        return {
            "connected": True,
            "company_id": stored.get("company_id"),
            "connected_at": stored.get("connected_at"),
        }


# Singleton instance
_auth_service: Optional[DanlonAuthService] = None


def get_danlon_auth_service() -> DanlonAuthService:
    """Get the singleton Danlon auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = DanlonAuthService()
    return _auth_service
