"""
Authentication service for external API access.
Handles token acquisition and caching.
"""
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class APIAuthService:
    """Manages authentication tokens for external API access."""
    
    def __init__(self):
        self.core_api_url = os.getenv("CORE_API_URL", "")
        self.api_auth_key = os.getenv("API_AUTH_KEY", "")
        self.apim_subscription_key = os.getenv("APIM_SUBSCRIPTION_KEY", "")
        
        # Token cache
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def get_token(self) -> str:
        """
        Get a valid bearer token, refreshing if necessary.
        
        Returns:
            Valid bearer token
            
        Raises:
            Exception if authentication fails
        """
        # Check if we have a cached token that's still valid
        if self._token and self._token_expires_at:
            # Refresh token if it expires in less than 5 minutes
            if datetime.now() < (self._token_expires_at - timedelta(minutes=5)):
                return self._token
        
        # Need to get a new token
        await self._refresh_token()
        
        if not self._token:
            raise Exception("Failed to obtain authentication token")
        
        return self._token
    
    async def _refresh_token(self) -> None:
        """Refresh the authentication token by calling the auth endpoint."""
        if not self.core_api_url or not self.api_auth_key:
            raise Exception("API authentication not configured. Set CORE_API_URL and API_AUTH_KEY environment variables.")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.core_api_url}/Authentication/apiaccess"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Note: The Ocp-Apim-Subscription-Key header is commented out in the Bruno file
            # Only add it if it's configured
            if self.apim_subscription_key:
                headers["Ocp-Apim-Subscription-Key"] = self.apim_subscription_key
            
            body = {
                "key": self.api_auth_key
            }
            
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if "token" not in data:
                raise Exception("No token in authentication response")
            
            self._token = data["token"]
            
            # Calculate expiry time
            if "expiresIn" in data:
                # expiresIn is in seconds
                expires_in = int(data["expiresIn"])
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            elif "validTo" in data:
                # Parse ISO datetime
                self._token_expires_at = datetime.fromisoformat(data["validTo"].replace('Z', '+00:00'))
            else:
                # Default to 1 hour if no expiry info
                self._token_expires_at = datetime.now() + timedelta(hours=1)
    
    def get_headers(self, token: str) -> Dict[str, str]:
        """
        Get the required headers for API requests.
        
        Args:
            token: Bearer token
            
        Returns:
            Dictionary of headers
        """
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        if self.apim_subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.apim_subscription_key
        
        return headers


# Singleton instance
_auth_service: Optional[APIAuthService] = None


def get_auth_service() -> APIAuthService:
    """Get the singleton authentication service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = APIAuthService()
    return _auth_service
