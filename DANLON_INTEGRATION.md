# Danløn OAuth Integration

This document describes the Danløn OAuth2 integration implementation for automatic token management and paypart creation.

## Overview

The integration implements the complete OAuth2 authorization code flow as specified in the Danløn partner documentation. Workers can now automatically push time registrations to Danløn without manual token management.

## Architecture

### Components

1. **DanlonOAuthService** (`app/services/danlon_oauth.py`)
   - Handles OAuth2 flow (authorization, token exchange, refresh, revoke)
   - Manages token storage (in-memory, should be replaced with database)
   - Provides GraphQL query execution with automatic token handling

2. **DanlonAPIService** (`app/services/danlon_api.py`)
   - High-level API for business operations
   - Automatically handles token refresh
   - Methods for creating payparts, querying employees, etc.

3. **OAuth Router** (`app/routers/danlon_oauth.py`)
   - Endpoints for the connection/disconnection flow
   - Landing page, callbacks, success, and revoke handlers

## Environment Configuration

Add these environment variables to your `.env` file:

```bash
# Danløn OAuth Configuration
DANLON_ENVIRONMENT=demo              # or "prod" for production
DANLON_CLIENT_ID=partner-showcase    # Your client ID from Danløn
DANLON_CLIENT_SECRET=your_secret     # Your client secret from Danløn
APP_BASE_URL=http://localhost:8000   # Your application base URL
```

### Demo Environment Values

```bash
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82
APP_BASE_URL=http://localhost:8000
```

### Production Environment Values

```bash
DANLON_ENVIRONMENT=prod
DANLON_CLIENT_ID=simplysolutions
DANLON_CLIENT_SECRET=oFqALlksfa3xK2CcQJXbXXaofXDH79Qd
APP_BASE_URL=https://your-production-domain.com
```

## Connection Flow

### Step 1: User Initiates Connection

Users can initiate connection from either:
- **Your App**: Direct them to `GET /danlon/connect`
- **Danløn**: Danløn redirects to `GET /danlon/connect?return_uri=...`

### Step 2-6: Automatic OAuth Flow

The system automatically handles:
1. Redirect to Danløn OAuth2 server
2. User authentication and consent
3. Code exchange for temporary token
4. Company selection (if multiple companies)
5. Final token exchange

### Step 7-10: Token Storage

Once complete:
- Final access and refresh tokens are stored
- User is redirected to success page or back to Danløn
- Connection is ready for API calls

## API Endpoints

### Connection Endpoints

#### `GET /danlon/connect`
Initiate connection to Danløn.

**Query Parameters:**
- `return_uri` (optional): Return URI if initiated from Danløn

**Response:** Redirects to Danløn OAuth2 server

---

#### `GET /danlon/callback`
OAuth2 callback endpoint (automatically called by Danløn).

**Query Parameters:**
- `code`: Authorization code
- `return_uri` (optional): Return URI to preserve
- `error` (optional): Error code if authorization failed

**Response:** Redirects to select-company page

---

#### `GET /danlon/success`
Success callback after company selection (automatically called by Danløn).

**Query Parameters:**
- `code`: Code for final token exchange
- `company_id`: Selected company ID (base64)
- `return_uri` (optional): Return URI if initiated from Danløn

**Response:** Success page or redirect to return_uri

---

#### `GET /danlon/revoke`
Revoke callback when user disconnects from Danløn side.

**Query Parameters:**
- `return_uri` (optional): Return URI to redirect after cleanup

**Response:** Cleanup page or redirect to return_uri

---

#### `POST /danlon/disconnect`
Disconnect initiated from your application.

**Request Body (JSON):**
```json
{
  "user_id": "optional_user_id",
  "company_id": "required_company_id"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully disconnected from Danløn"
}
```

---

#### `POST /danlon/token/refresh`
Get a valid access token (auto-refreshes if needed).

**Request Body (JSON):**
```json
{
  "user_id": "optional_user_id",
  "company_id": "required_company_id"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "expires_in": 300
}
```

---

#### `GET /danlon/status`
Check connection status.

**Query Parameters:**
- `user_id` (optional): User ID
- `company_id` (optional): Company ID

**Response:**
```json
{
  "connected": true,
  "user_id": "demo_user",
  "company_id": "123",
  "expires_at": "2024-02-15T14:30:00",
  "created_at": "2024-02-15T14:25:00"
}
```

## Usage Examples

### Example 1: Create Payparts from Time Registrations

```python
from app.services.danlon_api import get_danlon_api_service

async def push_time_registrations_to_danlon(
    user_id: str,
    company_id: str,
    time_registrations: List[Dict]
):
    """
    Push processed time registrations to Danløn as payparts.
    
    Args:
        user_id: The authenticated user ID
        company_id: The Danløn company ID
        time_registrations: List of processed time registration data
    """
    # Get API service (handles auth automatically)
    api = get_danlon_api_service(user_id, company_id)
    
    # First, get employees and paypart metadata
    employees = await api.get_employees()
    meta = await api.get_paypart_meta()
    
    # Create a mapping for quick lookups
    employee_map = {emp["employment_number"]: emp["id"] for emp in employees}
    pay_code_map = {code["code"]: code["id"] for code in meta["pay_codes"]}
    
    # Transform time registrations to payparts
    payparts = []
    for reg in time_registrations:
        employee_id = employee_map.get(reg["employee_number"])
        pay_code_id = pay_code_map.get(reg["pay_code"])
        
        if not employee_id or not pay_code_id:
            continue  # Skip if employee or pay code not found
        
        paypart = {
            "employee_id": employee_id,
            "date": reg["date"],  # Format: "2024-02-15"
            "pay_code_id": pay_code_id,
            "hours": reg["hours"],
            "rate": reg["hourly_rate"],
            "amount": reg["hours"] * reg["hourly_rate"],
            "text": f"Time registration for {reg['date']}",
            "reference": reg.get("reference_number")
        }
        payparts.append(paypart)
    
    # Create all payparts in one call
    if payparts:
        result = await api.create_payparts(payparts)
        print(f"Created {len(result['payparts'])} payparts successfully!")
        return result
    else:
        print("No valid payparts to create")
        return None
```

### Example 2: Add to Existing Upload Router

```python
from fastapi import APIRouter, UploadFile, HTTPException
from app.services.danlon_api import get_danlon_api_service

router = APIRouter()

@router.post("/upload-and-sync")
async def upload_and_sync_to_danlon(
    file: UploadFile,
    company_id: str,
    auto_sync: bool = False
):
    """
    Upload CSV, process it, and optionally sync to Danløn.
    """
    # Process the CSV file (existing logic)
    processed_data = await process_csv(file)
    
    # If auto_sync is enabled, push to Danløn
    if auto_sync and company_id:
        user_id = "demo_user"  # Get from session/auth
        
        try:
            api = get_danlon_api_service(user_id, company_id)
            result = await push_time_registrations_to_danlon(
                user_id=user_id,
                company_id=company_id,
                time_registrations=processed_data["time_entries"]
            )
            
            return {
                "processed_data": processed_data,
                "danlon_sync": {
                    "success": True,
                    "payparts_created": len(result["payparts"])
                }
            }
        except Exception as e:
            # Don't fail the whole request if Danløn sync fails
            return {
                "processed_data": processed_data,
                "danlon_sync": {
                    "success": False,
                    "error": str(e)
                }
            }
    
    return {
        "processed_data": processed_data,
        "danlon_sync": None
    }
```

### Example 3: Frontend Connection Button

```typescript
// React component example
async function connectToDanlon() {
  // Simply redirect to the connect endpoint
  window.location.href = '/danlon/connect';
}

async function checkConnectionStatus(companyId: string) {
  const response = await fetch(`/danlon/status?company_id=${companyId}`);
  const status = await response.json();
  return status.connected;
}

async function disconnectFromDanlon(companyId: string) {
  const response = await fetch('/danlon/disconnect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_id: companyId })
  });
  return await response.json();
}
```

## Production Deployment Checklist

### 1. Replace In-Memory Token Storage

The current implementation uses in-memory storage for tokens. This MUST be replaced with a database before production.

**Required changes:**

1. Create database table for tokens:
```sql
CREATE TABLE danlon_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    company_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, company_id)
);
```

2. Update `store_tokens`, `get_tokens`, and `delete_tokens` methods in `DanlonOAuthService` to use database queries instead of `self._tokens` dictionary.

### 2. Add User Authentication

Currently using a hardcoded `demo_user`. Replace with actual user authentication:

1. Implement user session management
2. Update all `user_id = "demo_user"` references to get user from session
3. Add authentication middleware to protect endpoints

### 3. Environment Configuration

1. Set production environment variables
2. Use proper secret management (Azure Key Vault, etc.)
3. Configure `APP_BASE_URL` to your production domain

### 4. Error Handling and Logging

1. Add proper error tracking (Sentry, Application Insights, etc.)
2. Add audit logs for token operations
3. Implement retry logic for transient failures

### 5. Security Considerations

1. Use HTTPS only
2. Implement CSRF protection for state parameters
3. Add rate limiting to OAuth endpoints
4. Validate redirect URIs
5. Secure token storage with encryption at rest

### 6. Testing

1. Test complete OAuth flow in demo environment
2. Test token refresh logic
3. Test disconnect scenarios (both directions)
4. Test reconnection after disconnect
5. Test error cases (expired tokens, invalid codes, etc.)

## Troubleshooting

### Issue: "No valid access token"

**Solution:** User needs to connect first. Direct them to `/danlon/connect`.

### Issue: "Token expired" errors

**Solution:** The service automatically refreshes tokens. If this error persists, the refresh token may be invalid. User needs to reconnect.

### Issue: "Failed to exchange code for token"

**Solution:** 
- Check that `DANLON_CLIENT_SECRET` is set correctly
- Verify `APP_BASE_URL` matches the registered redirect URI
- Check logs for detailed error from Danløn

### Issue: Tokens not persisting across server restarts

**Solution:** This is expected with in-memory storage. Implement database storage (see Production Deployment Checklist).

## Flow Diagram

```
User Action                  Your App                    Danløn
    |                           |                           |
    |------ Click Connect ----->|                           |
    |                           |                           |
    |                           |---- Redirect Auth ------->|
    |                           |                           |
    |<---------- Login & Consent Screen --------------------|
    |                           |                           |
    |-------------------- Approve ------------------------->|
    |                           |                           |
    |                           |<--- Redirect Callback ----|
    |                           |     (with code)           |
    |                           |                           |
    |                           |---- Exchange Code ------->|
    |                           |<--- Temp Token -----------|
    |                           |                           |
    |                           |-- Redirect Select Co. --->|
    |                           |                           |
    |<---------- Select Company Screen ---------------------|
    |                           |                           |
    |-------------------- Select Company ------------------>|
    |                           |                           |
    |                           |<--- Redirect Success -----|
    |                           |     (with final code)     |
    |                           |                           |
    |                           |---- Get Final Tokens ---->|
    |                           |<--- Access + Refresh -----|
    |                           |                           |
    |                           |-- Store Tokens in DB      |
    |                           |                           |
    |<---- Show Success Page ---|                           |
    |                           |                           |
    
    [User now connected - can make API calls]
    
    |                           |                           |
    |-- Worker Ready to Sync -->|                           |
    |                           |                           |
    |                           |-- Get Valid Token         |
    |                           |-- (auto-refresh if needed)|
    |                           |                           |
    |                           |---- Create PayParts ----->|
    |                           |<--- Success --------------|
    |                           |                           |
    |<---- Sync Complete -------|                           |
```

## Next Steps

1. **Test the flow**: Run the app and try connecting to Danløn demo environment
2. **Implement database storage**: Replace in-memory token storage
3. **Add user authentication**: Replace `demo_user` with real user management
4. **Integrate with workers**: Add `danlon_sync` parameter to your upload endpoints
5. **Frontend UI**: Add "Connect to Danløn" button and sync status indicators
6. **Deploy to staging**: Test full flow in a staging environment
7. **Production deployment**: Follow the production checklist above
