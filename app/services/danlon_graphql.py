"""
Danlon GraphQL client service.
Handles GraphQL queries and mutations to the Danlon API.
"""
import os
import httpx
from typing import Dict, Any, List, Optional

from app.services.danlon_auth import get_danlon_auth_service


class DanlonGraphQLService:
    """Client for interacting with Danlon's GraphQL API."""
    
    def __init__(self):
        self.graphql_endpoint = os.getenv("DANLON_GRAPHQL_ENDPOINT", "")
        self.auth_service = get_danlon_auth_service()
    
    async def _execute_query(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query or mutation string
            variables: Optional variables for the query
            
        Returns:
            Response data from GraphQL endpoint
            
        Raises:
            Exception: If GraphQL endpoint is not configured or request fails
        """
        if not self.graphql_endpoint:
            raise Exception("DANLON_GRAPHQL_ENDPOINT not configured")
        
        # Get valid access token
        access_token = await self.auth_service.get_valid_access_token()
        
        # Build request payload
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        
        # Execute GraphQL request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.graphql_endpoint,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_messages = [err.get("message", str(err)) for err in result["errors"]]
                raise Exception(f"GraphQL errors: {', '.join(error_messages)}")
            
            return result.get("data", {})
    
    async def get_current_company(self) -> Dict[str, Any]:
        """
        Get the current company associated with the connection.
        
        Returns:
            Company object with id and name
        """
        query = "{current_company{id, name}}"
        result = await self._execute_query(query)
        return result.get("current_company", {})
    
    async def get_companies(self) -> List[Dict[str, Any]]:
        """
        Get all companies accessible to the user.
        
        Returns:
            List of company objects with id and name
        """
        query = "{companies{id, name}}"
        result = await self._execute_query(query)
        return result.get("companies", [])
    
    async def get_employees(self) -> List[Dict[str, Any]]:
        """
        Get all employees across all companies.
        
        Returns:
            List of employee objects
        """
        query = "{companies{employees{name, birth_date}}}"
        result = await self._execute_query(query)
        
        # Flatten employees from all companies
        employees = []
        for company in result.get("companies", []):
            employees.extend(company.get("employees", []))
        
        return employees
    
    async def get_pay_parts(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Get available pay parts for a company.
        
        Args:
            company_id: Company ID to fetch pay parts for
            
        Returns:
            List of pay part objects with code and company info
        """
        query = """
        query($company_id: ID!) {
            pay_parts(company_id: $company_id) {
                code
                company { id }
            }
        }
        """
        variables = {"company_id": company_id}
        result = await self._execute_query(query, variables)
        return result.get("pay_parts", [])
    
    async def submit_pay_parts(
        self, 
        company_id: str, 
        pay_lines: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Submit pay parts (salary lines) to Danlon.
        
        This is a placeholder for the actual mutation.
        The exact mutation schema will need to be confirmed from Danlon's API documentation.
        
        Args:
            company_id: Company ID to submit pay lines for
            pay_lines: List of pay line objects with employee info and amounts
            
        Returns:
            Result of the mutation
        """
        # NOTE: This mutation is a placeholder and needs to be adjusted
        # based on actual Danlon GraphQL schema for pay part submission
        mutation = """
        mutation($company_id: ID!, $pay_lines: [PayLineInput!]!) {
            create_pay_lines(company_id: $company_id, pay_lines: $pay_lines) {
                success
                message
                created_count
            }
        }
        """
        
        variables = {
            "company_id": company_id,
            "pay_lines": pay_lines
        }
        
        result = await self._execute_query(mutation, variables)
        return result.get("create_pay_lines", {})


# Singleton instance
_graphql_service: Optional[DanlonGraphQLService] = None


def get_danlon_graphql_service() -> DanlonGraphQLService:
    """Get the singleton Danlon GraphQL service instance."""
    global _graphql_service
    if _graphql_service is None:
        _graphql_service = DanlonGraphQLService()
    return _graphql_service
