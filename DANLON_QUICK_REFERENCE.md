# Danløn Integration - Quick Reference Card

Quick reference for the most common operations.

## Environment Setup (One-time)

```bash
# Add to .env file
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82
APP_BASE_URL=http://localhost:8000
```

## Connect to Danløn (One-time per user)

```python
# Browser: Navigate to
http://localhost:8000/danlon/connect

# Login credentials (demo)
Username: simplysolutions
Password: s5zC4uVFrJgGBYhMfybV
```

## Check Connection Status

```python
# Python
from app.services.danlon_sync import check_danlon_connection

is_connected = await check_danlon_connection(user_id, company_id)

# HTTP
GET /danlon/status?company_id=YOUR_COMPANY_ID
```

## Sync Time Registrations (Main Function)

```python
from app.services.danlon_sync import sync_time_registrations_to_danlon

result = await sync_time_registrations_to_danlon(
    user_id="user123",
    company_id="danlon_company_id",
    time_registrations=[
        {
            "employee_number": "001",
            "date": "2024-02-15",
            "hours": 8.0,
            "hourly_rate": 200.0,
            "pay_code": "100",
            "description": "Regular work"
        }
    ]
)

# Check result
if result.success:
    print(f"Created {result.created_count} payparts")
    print(f"Skipped {result.skipped_count} entries")
else:
    print(f"Failed: {result.message}")
```

## Auto-Detect Field Names

```python
from app.services.danlon_sync import sync_csv_data_to_danlon

# Automatically detects common field name variations
result = await sync_csv_data_to_danlon(
    user_id=user_id,
    company_id=company_id,
    csv_data=your_csv_data  # No field mapping needed!
)
```

## Get Company Information

```python
from app.services.danlon_api import get_danlon_api_service

api = get_danlon_api_service(user_id, company_id)

# Get company
company = await api.get_current_company()

# Get employees
employees = await api.get_employees()

# Get pay codes and metadata
meta = await api.get_paypart_meta()
```

## Create Single Paypart (Testing)

```python
api = get_danlon_api_service(user_id, company_id)

paypart = await api.create_paypart(
    employee_id="employee_id_from_danlon",
    date="2024-02-15",
    pay_code_id="paycode_id_from_danlon",
    hours=8.0,
    rate=200.0,
    amount=1600.0,
    text="Test paypart"
)
```

## Error Handling

```python
try:
    result = await sync_time_registrations_to_danlon(...)
    
    if not result.success:
        # Handle sync errors
        print(f"Errors: {result.errors}")
        print(f"Skipped: {result.skipped_items}")
    else:
        # Success
        print(f"Created: {result.created_payparts}")
        
except Exception as e:
    # Handle exceptions
    print(f"Exception: {e}")
```

## Common HTTP Endpoints

```bash
# Connect to Danløn
GET http://localhost:8000/danlon/connect

# Check status
GET http://localhost:8000/danlon/status?company_id=XXX

# Get company info (example endpoint)
GET http://localhost:8000/danlon/example/company-info?company_id=XXX

# Sync payparts (example endpoint)
POST http://localhost:8000/danlon/example/sync-payparts?company_id=XXX

# Test single paypart (example endpoint)
POST http://localhost:8000/danlon/example/test-single-paypart?company_id=XXX&employee_id=YYY&pay_code_id=ZZZ&hours=8&rate=200

# Disconnect
POST http://localhost:8000/danlon/disconnect
Content-Type: application/json
{"company_id": "XXX"}
```

## Field Mapping Options

```python
# Default field names
sync_time_registrations_to_danlon(
    user_id=user_id,
    company_id=company_id,
    time_registrations=data,
    employee_number_field="employee_number",  # default
    date_field="date",                         # default
    hours_field="hours",                       # default
    rate_field="hourly_rate",                 # default
    pay_code_field="pay_code",                # default
    description_field="description",          # default
    reference_field="reference"               # default
)

# Custom field names (if your CSV is different)
sync_time_registrations_to_danlon(
    user_id=user_id,
    company_id=company_id,
    time_registrations=data,
    employee_number_field="medarbejder_nr",
    date_field="dato",
    hours_field="timer",
    rate_field="timeløn",
    pay_code_field="lønart"
)
```

## Response Object

```python
result = await sync_time_registrations_to_danlon(...)

# Result attributes
result.success          # bool
result.created_count    # int
result.skipped_count    # int
result.error_count      # int
result.message          # str
result.created_payparts # list
result.skipped_items    # list
result.errors           # list

# Convert to dict for JSON
result_dict = result.to_dict()
```

## Testing Workflow

```bash
# 1. Start app
npm run backend:dev

# 2. Connect (browser)
http://localhost:8000/danlon/connect

# 3. Get company info
curl "http://localhost:8000/danlon/example/company-info?company_id=YOUR_ID"

# 4. Test sync
curl -X POST "http://localhost:8000/danlon/example/sync-payparts?company_id=YOUR_ID"
```

## Common Issues

### "No valid access token"
→ Need to connect first: `/danlon/connect`

### "Employee not found"
→ Check employee number matches Danløn's employment_number

### "Pay code not found"
→ Use pay code from metadata: `/danlon/example/company-info`

### "Token expired"
→ Should auto-refresh. If not, check connection: `/danlon/status`

## API Documentation

Interactive docs available at:
```
http://localhost:8000/docs
```

## File Locations

- **OAuth Service**: `app/services/danlon_oauth.py`
- **API Service**: `app/services/danlon_api.py`
- **Sync Service**: `app/services/danlon_sync.py`
- **OAuth Endpoints**: `app/routers/danlon_oauth.py`
- **Example Endpoints**: `app/routers/danlon_integration_example.py`

## Key Functions to Import

```python
# For syncing
from app.services.danlon_sync import (
    sync_time_registrations_to_danlon,
    sync_csv_data_to_danlon,
    check_danlon_connection,
    get_danlon_company_info
)

# For direct API access
from app.services.danlon_api import get_danlon_api_service

# For OAuth operations
from app.services.danlon_oauth import get_danlon_oauth_service
```

## Production Checklist

- [ ] Set production environment variables
- [ ] Implement database token storage
- [ ] Add user authentication
- [ ] Move secrets to Key Vault
- [ ] Add sync history tracking
- [ ] Test with production credentials
- [ ] Deploy to staging
- [ ] Deploy to production

## Need Help?

- **Quick Start**: `DANLON_QUICKSTART.md`
- **Full Documentation**: `DANLON_INTEGRATION.md`
- **Integration Examples**: `INTEGRATION_EXAMPLE.md`
- **Implementation Details**: `DANLON_IMPLEMENTATION_SUMMARY.md`
