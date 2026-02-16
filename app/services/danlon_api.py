"""
Danløn API service for business operations (create payparts, query employees, etc.).
This service uses the OAuth service to handle authentication automatically.
"""
from typing import List, Dict, Any, Optional
import logging

from app.services.danlon_oauth import get_danlon_oauth_service

logger = logging.getLogger(__name__)


class DanlonAPIService:
    """
    High-level service for Danløn API operations.
    Automatically handles token refresh and authentication.
    """
    
    def __init__(self, user_id: str, company_id: str):
        """
        Initialize the API service for a specific user and company.
        
        Args:
            user_id: User identifier
            company_id: Danløn company ID
        """
        self.user_id = user_id
        self.company_id = company_id
        self.oauth_service = get_danlon_oauth_service()
    
    async def _execute_query(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query with automatic token handling.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response data
            
        Raises:
            Exception if query fails or tokens are invalid
        """
        # Get a valid access token (will refresh if needed)
        access_token = await self.oauth_service.get_valid_access_token(
            self.user_id, 
            self.company_id
        )
        
        if not access_token:
            raise Exception(
                f"No valid access token for user {self.user_id}, company {self.company_id}. "
                "Please connect to Danløn first."
            )
        
        # Execute the query
        return await self.oauth_service.query_graphql(
            access_token=access_token,
            query=query,
            variables=variables
        )
    
    async def get_current_company(self) -> Dict[str, Any]:
        """
        Get the current company details.
        
        Returns:
            Company data including id, name, etc.
        """
        query = """
        {
            current_company {
                id
                name
                vat_number
            }
        }
        """
        
        result = await self._execute_query(query)
        return result["data"]["current_company"]
    
    async def get_companies(self, company_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get details for specific companies by IDs.
        
        Args:
            company_ids: List of company IDs
            
        Returns:
            List of company objects
        """
        query = """
        query GetCompanies($ids: [ID!]!) {
            companies(ids: $ids) {
                id
                name
                vat_number
            }
        }
        """
        
        result = await self._execute_query(query, variables={"ids": company_ids})
        return result["data"]["companies"]
    
    async def get_employees(
        self, 
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all employees for the company.
        
        Args:
            include_deleted: Whether to include deleted employees
            
        Returns:
            List of employee objects
        """
        query = """
        query GetEmployees($includeDeleted: Boolean!) {
            current_company {
                employees(includeDeleted: $includeDeleted) {
                    id
                    first_name
                    last_name
                    cpr_number
                    email
                    employment_number
                }
            }
        }
        """
        
        result = await self._execute_query(
            query, 
            variables={"includeDeleted": include_deleted}
        )
        return result["data"]["current_company"]["employees"]
    
    async def get_paypart_meta(self) -> Dict[str, Any]:
        """
        Get metadata for creating payparts (pay codes, absence codes, etc.).
        
        Returns:
            Metadata object with pay_codes, absence_codes, hour_types
        """
        query = """
        {
            current_company {
                meta {
                    pay_codes {
                        id
                        name
                        code
                    }
                    absence_codes {
                        id
                        name
                        code
                    }
                    hour_types {
                        id
                        name
                    }
                }
            }
        }
        """
        
        result = await self._execute_query(query)
        return result["data"]["current_company"]["meta"]
    
    async def create_payparts(
        self, 
        payparts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create payparts (time registrations) for employees.
        
        This is the main function to call when workers are ready to import
        their time registrations to Danløn.
        
        Args:
            payparts: List of paypart objects to create
            
        Example paypart object:
            {
                "employee_id": "123",
                "date": "2024-02-15",
                "pay_code_id": "456",
                "hours": 8.0,
                "rate": 200.0,
                "amount": 1600.0,
                "hour_type_id": "789",  # optional
                "text": "Regular work",  # optional
                "reference": "REF-001"  # optional
            }
            
        Returns:
            Result object with created payparts
            
        Raises:
            Exception if creation fails
        """
        mutation = """
        mutation CreatePayParts($input: CreatePayPartsInput!) {
            createPayParts(input: $input) {
                payparts {
                    id
                    employee_id
                    date
                    pay_code_id
                    hours
                    rate
                    amount
                }
                errors {
                    message
                    field
                }
            }
        }
        """
        
        variables = {
            "input": {
                "payparts": payparts
            }
        }
        
        logger.info(f"Creating {len(payparts)} payparts for company {self.company_id}")
        
        result = await self._execute_query(mutation, variables=variables)
        
        # Check for errors in the response
        if "errors" in result["data"]["createPayParts"]:
            errors = result["data"]["createPayParts"]["errors"]
            if errors:
                error_messages = [f"{e.get('field', 'unknown')}: {e.get('message', 'unknown error')}" for e in errors]
                raise Exception(f"Failed to create payparts: {', '.join(error_messages)}")
        
        created_count = len(result["data"]["createPayParts"]["payparts"])
        logger.info(f"Successfully created {created_count} payparts")
        
        return result["data"]["createPayParts"]
    
    async def create_paypart(
        self,
        employee_id: str,
        date: str,
        pay_code_id: str,
        hours: float,
        rate: float,
        amount: float,
        hour_type_id: Optional[str] = None,
        text: Optional[str] = None,
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a single paypart (convenience method).
        
        Args:
            employee_id: Danløn employee ID
            date: Date in YYYY-MM-DD format
            pay_code_id: Pay code ID
            hours: Number of hours
            rate: Hourly rate
            amount: Total amount (hours * rate)
            hour_type_id: Optional hour type ID
            text: Optional description text
            reference: Optional reference number
            
        Returns:
            Created paypart object
        """
        paypart = {
            "employee_id": employee_id,
            "date": date,
            "pay_code_id": pay_code_id,
            "hours": hours,
            "rate": rate,
            "amount": amount
        }
        
        if hour_type_id:
            paypart["hour_type_id"] = hour_type_id
        if text:
            paypart["text"] = text
        if reference:
            paypart["reference"] = reference
        
        result = await self.create_payparts([paypart])
        return result["payparts"][0] if result["payparts"] else None


def get_danlon_api_service(user_id: str, company_id: str) -> DanlonAPIService:
    """
    Get a Danløn API service instance for a specific user and company.
    
    Args:
        user_id: User identifier
        company_id: Danløn company ID
        
    Returns:
        DanlonAPIService instance
    """
    return DanlonAPIService(user_id=user_id, company_id=company_id)
