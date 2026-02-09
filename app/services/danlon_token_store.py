"""
Token storage service for Danlon OAuth2 tokens.
Interface-first design allows swapping file-based storage for database later.
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class TokenStore(ABC):
    """Abstract base class for token storage."""
    
    @abstractmethod
    def save_tokens(
        self,
        access_token: str,
        refresh_token: str,
        company_id: str,
        expires_in: Optional[int] = None
    ) -> None:
        """Save OAuth2 tokens and company information."""
        pass
    
    @abstractmethod
    def get_tokens(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored tokens.
        
        Returns:
            Dictionary with keys: access_token, refresh_token, company_id, 
            connected_at, expires_in (optional)
            Returns None if no tokens are stored.
        """
        pass
    
    @abstractmethod
    def delete_tokens(self) -> None:
        """Delete all stored tokens."""
        pass
    
    @abstractmethod
    def has_tokens(self) -> bool:
        """Check if tokens are currently stored."""
        pass


class FileTokenStore(TokenStore):
    """File-based token storage using JSON."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize file-based token store.
        
        Args:
            storage_path: Path to JSON file for storage. 
                         Defaults to 'danlon_tokens.json' in workspace root.
        """
        if storage_path is None:
            # Default to workspace root
            base_dir = Path(__file__).resolve().parent.parent.parent
            storage_path = str(base_dir / "danlon_tokens.json")
        
        self.storage_path = storage_path
    
    def save_tokens(
        self,
        access_token: str,
        refresh_token: str,
        company_id: str,
        expires_in: Optional[int] = None
    ) -> None:
        """Save tokens to JSON file."""
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "company_id": company_id,
            "connected_at": datetime.now().isoformat(),
        }
        
        if expires_in is not None:
            data["expires_in"] = expires_in
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def get_tokens(self) -> Optional[Dict[str, Any]]:
        """Load tokens from JSON file."""
        if not os.path.exists(self.storage_path):
            return None
        
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def delete_tokens(self) -> None:
        """Delete the token storage file."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
    
    def has_tokens(self) -> bool:
        """Check if token file exists and is valid."""
        tokens = self.get_tokens()
        return tokens is not None and "refresh_token" in tokens


# Singleton instance
_token_store: Optional[TokenStore] = None


def get_token_store() -> TokenStore:
    """Get the singleton token store instance."""
    global _token_store
    if _token_store is None:
        _token_store = FileTokenStore()
    return _token_store
