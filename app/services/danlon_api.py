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
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all employees for the company via companiesExt.

        Args:
            include_deleted: Whether to include inactive employees

        Returns:
            List of employee objects with keys: id, name, active, domainId, email
        """
        query = """
        query GetCompanyEmployees($companyIds: [ID!]!) {
            companiesExt(input: {companyIds: $companyIds}) {
                companies {
                    employees {
                        employees {
                            id
                            active
                            domainId
                            name
                            email
                        }
                    }
                }
            }
        }
        """

        result = await self._execute_query(
            query,
            variables={"companyIds": [self.company_id]},
        )
        companies = result["data"]["companiesExt"]["companies"]
        if not companies:
            return []
        employees: List[Dict[str, Any]] = companies[0]["employees"]["employees"]
        if not include_deleted:
            employees = [e for e in employees if e.get("active", True)]
        return employees
    
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

    async def get_pay_parts_meta(self) -> List[Dict[str, Any]]:
        """
        Fetch the payPartsMeta list from Danløn.

        Each item describes a valid pay part code and which fields
        (units, rate, amount) are allowed for that code.

        Returns:
            List of dicts with keys: code, description, unitsAllowed,
            rateAllowed, amountAllowed
        """
        query = """
        query GetPayPartsMeta {
            payPartsMeta {
                payPartsMeta {
                    code
                    description
                    unitsAllowed
                    rateAllowed
                    amountAllowed
                }
            }
        }
        """

        result = await self._execute_query(query)
        return result["data"]["payPartsMeta"]["payPartsMeta"]
    
    async def create_payparts(
        self,
        payparts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create payparts (time registrations) for employees.

        This is the main function to call when workers are ready to import
        their time registrations to Danløn.

        Args:
            payparts: List of paypart objects to create.

        Each paypart must have:
            {
                "employeeId": "<danlon employee ID>",
                "code":       "T1",          # pay part code
                "units":      8.0,           # optional - hours/units
                "rate":       200.0,         # optional - rate per unit
                "amount":     1600.0         # optional - total amount
            }
            Include only the fields allowed by the pay code's unitsAllowed /
            rateAllowed / amountAllowed flags.

        Returns:
            {"createdPayParts": [...]}

        Raises:
            Exception if the mutation returns GraphQL errors or HTTP errors.
        """
        # Build pay-parts list literal for inline GraphQL (avoids variable
        # type-name issues reported with some Danløn environments).
        # Danløn's schema types units, rate, and amount as Int.
        # Hours are stored as centesimal units (1 hour = 100), preserving
        # fractional precision without decimals: 7.5 h → 750.
        # Monetary amounts are rounded to nearest whole DKK.
        def _paypart_to_gql(pp: Dict[str, Any]) -> str:
            fields = [f'employeeId: "{pp["employeeId"]}"', f'code: "{pp["code"]}"']
            if pp.get("units") is not None:
                centesimal = int(round(float(pp["units"]) * 100))
                fields.append(f"units: {centesimal}")
            if pp.get("rate") is not None:
                fields.append(f"rate: {int(round(float(pp['rate'])))}")
            if pp.get("amount") is not None:
                fields.append(f"amount: {int(round(float(pp['amount'])))}")
            return "{" + ", ".join(fields) + "}"

        pay_parts_literal = "[" + ", ".join(_paypart_to_gql(pp) for pp in payparts) + "]"

        mutation = f"""
        mutation CreatePayParts {{
            createPayParts(input: {{
                companyId: "{self.company_id}",
                payParts: {pay_parts_literal}
            }}) {{
                createdPayParts {{
                    id
                    code
                    units
                    rate
                    amount
                    employee {{
                        id
                        name
                    }}
                }}
            }}
        }}
        """

        logger.info(f"Creating {len(payparts)} payparts for company {self.company_id}")

        result = await self._execute_query(mutation)

        if result.get("errors"):
            error_messages = [e.get("message", "unknown error") for e in result["errors"]]
            raise Exception(f"Failed to create payparts: {'; '.join(error_messages)}")

        created = result["data"]["createPayParts"]["createdPayParts"]
        logger.info(f"Successfully created {len(created)} payparts")

        return {"createdPayParts": created}

    async def create_paypart(
        self,
        employee_id: str,
        code: str,
        units: Optional[float] = None,
        rate: Optional[float] = None,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a single paypart (convenience method).

        Args:
            employee_id: Danløn employee ID
            code:        Pay part code (e.g. "T1")
            units:       Number of units / hours (if allowed by the code)
            rate:        Rate per unit (if allowed by the code)
            amount:      Total amount (if allowed by the code)

        Returns:
            Created paypart object or None
        """
        paypart: Dict[str, Any] = {"employeeId": employee_id, "code": code}
        if units is not None:
            paypart["units"] = units
        if rate is not None:
            paypart["rate"] = rate
        if amount is not None:
            paypart["amount"] = amount

        result = await self.create_payparts([paypart])
        created = result.get("createdPayParts", [])
        return created[0] if created else None


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
