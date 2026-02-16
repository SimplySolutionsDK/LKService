# Danløn Integration - Quick Start Guide

This guide will help you test the Danløn OAuth integration and paypart creation flow.

## Prerequisites

1. Python environment with all dependencies installed
2. Danløn demo account credentials
3. Environment variables configured

## Step 1: Configure Environment

Add these to your `.env` file:

```bash
# Danløn Demo Configuration
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82
APP_BASE_URL=http://localhost:8000
```

## Step 2: Start the Application

```powershell
# Start the backend
npm run backend:dev

# Or if you want both frontend and backend:
npm run dev
```

The API will be available at `http://localhost:8000`

## Step 3: Test the OAuth Connection Flow

### Option A: Using Browser

1. **Open your browser** and go to:
   ```
   http://localhost:8000/danlon/connect
   ```

2. **You'll be redirected to Danløn's login page**
   - Username: `simplysolutions`
   - Password: `s5zC4uVFrJgGBYhMfybV`

3. **Give consent** when asked

4. **Select a company** (or it will auto-select if only one)

5. **You'll see a success page** confirming the connection

### Option B: Using PowerShell/curl

Check connection status:
```powershell
curl http://localhost:8000/danlon/status?company_id=YOUR_COMPANY_ID
```

## Step 4: Test Getting Company Information

Once connected, test fetching company data:

```powershell
# Get company info, employees, and metadata
curl "http://localhost:8000/danlon/example/company-info?company_id=YOUR_COMPANY_ID"
```

This will return:
- Company details (name, VAT number, etc.)
- List of employees
- Available pay codes, absence codes, and hour types

## Step 5: Test Creating Payparts

### Get Required IDs First

From the company info response, note:
- An `employee_id` (from the employees list)
- A `pay_code_id` (from metadata.pay_codes)

### Create a Test Paypart

```powershell
# Create a single test paypart
curl -X POST "http://localhost:8000/danlon/example/test-single-paypart?company_id=YOUR_COMPANY_ID&employee_id=EMPLOYEE_ID&pay_code_id=PAY_CODE_ID&hours=8.0&rate=200.0"
```

Replace:
- `YOUR_COMPANY_ID` with the company ID from step 3
- `EMPLOYEE_ID` with an employee ID from the company info
- `PAY_CODE_ID` with a pay code ID from the metadata

### Test Batch Paypart Creation

```powershell
# This uses example data - modify the endpoint code to use your actual data
curl -X POST "http://localhost:8000/danlon/example/sync-payparts?company_id=YOUR_COMPANY_ID"
```

## Step 6: Verify in Danløn

1. Log into the Danløn demo environment
2. Navigate to the payroll section
3. Verify that your payparts were created

## Step 7: Test Disconnection

### Disconnect from Your App

```powershell
curl -X POST "http://localhost:8000/danlon/disconnect" `
  -H "Content-Type: application/json" `
  -d "{\"company_id\": \"YOUR_COMPANY_ID\"}"
```

### Or Test Disconnect from Danløn Side

Go to Danløn's integration page and disconnect. The callback will clean up tokens.

## API Documentation

Once the server is running, you can view the full API documentation at:

```
http://localhost:8000/docs
```

This provides an interactive Swagger UI where you can test all endpoints.

## Common Issues and Solutions

### Issue: "No valid access token"

**Cause:** Not connected to Danløn yet

**Solution:** Go through Step 3 to connect

---

### Issue: "DANLON_CLIENT_SECRET environment variable not set"

**Cause:** Environment variables not loaded

**Solution:** 
1. Verify `.env` file exists and has the correct values
2. Restart the application
3. Check that `python-dotenv` is installed

---

### Issue: Redirect URI mismatch

**Cause:** `APP_BASE_URL` doesn't match the running server

**Solution:** 
- If running locally, use `http://localhost:8000`
- If using a different port, update `APP_BASE_URL` accordingly
- Make sure the URL doesn't have a trailing slash

---

### Issue: "Failed to exchange code for token"

**Cause:** Client secret is incorrect

**Solution:** 
- Double-check `DANLON_CLIENT_SECRET` in `.env`
- Make sure there are no extra spaces or quotes
- Verify you're using the correct environment (demo vs prod)

---

### Issue: Employee or pay code not found

**Cause:** IDs from example don't match your company

**Solution:** 
1. First call `/danlon/example/company-info` to get valid IDs
2. Use those IDs in your paypart creation requests
3. Update the example data in `danlon_integration_example.py`

## Integration with Your Workflow

To integrate this with your CSV processing workflow:

1. **After CSV Processing**: When workers have compared all time registrations

2. **Get the Processed Data**: From your CSV parser/overtime calculator

3. **Transform to Payparts**: Map your data structure to Danløn's format
   ```python
   from app.services.danlon_api import get_danlon_api_service
   
   async def push_to_danlon(user_id, company_id, time_entries):
       api = get_danlon_api_service(user_id, company_id)
       
       # Get metadata for mapping
       employees = await api.get_employees()
       meta = await api.get_paypart_meta()
       
       # Transform your data
       payparts = transform_time_entries_to_payparts(
           time_entries, 
           employees, 
           meta
       )
       
       # Create in Danløn
       result = await api.create_payparts(payparts)
       return result
   ```

4. **Add UI Controls**: Add buttons in frontend for:
   - "Connect to Danløn"
   - "Sync to Danløn" (when data is ready)
   - "View Sync Status"

## Next Steps

1. ✅ Test the OAuth flow
2. ✅ Test creating payparts
3. ⬜ Implement database storage for tokens (see `DANLON_INTEGRATION.md`)
4. ⬜ Add user authentication
5. ⬜ Integrate with your CSV processing workflow
6. ⬜ Add frontend UI components
7. ⬜ Deploy to staging environment
8. ⬜ Test with production credentials
9. ⬜ Deploy to production

## Testing Checklist

- [ ] Can connect to Danløn successfully
- [ ] Can see company information
- [ ] Can list employees
- [ ] Can list pay codes and metadata
- [ ] Can create a single test paypart
- [ ] Can create multiple payparts
- [ ] Token automatically refreshes when expired
- [ ] Can disconnect from your app
- [ ] Can disconnect from Danløn and reconnect
- [ ] Error messages are helpful and logged

## Support

For issues or questions:
1. Check the logs in your terminal
2. Review `DANLON_INTEGRATION.md` for detailed documentation
3. Check the Swagger docs at `/docs`
4. Review the example code in `app/routers/danlon_integration_example.py`
