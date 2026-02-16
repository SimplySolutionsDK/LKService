# End-to-End Testing Guide

Complete walkthrough to test the full Danløn integration from connection to paypart creation.

## Prerequisites

Before starting, ensure:
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Frontend built: `cd frontend && npm install && npm run build`
- [ ] Environment variables configured in `.env`
- [ ] Application running: `npm run backend:dev` or `npm run dev`

## Test Environment Setup

### 1. Configure Environment

Create or update the **root** `.env` file (NOT `frontend/.env local`):

```bash
# Danløn Demo Configuration
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82
APP_BASE_URL=http://localhost:8000

# Database (auto-creates SQLite)
# DATABASE_URL=sqlite+aiosqlite:///./lkservice.db
```

**Important:** 
- Danløn configuration goes in the **root `.env`** (for the FastAPI backend)
- Frontend variables are in `frontend/.env local` (for API endpoints)
- You do NOT need to add Danløn variables to the frontend's env file

### 2. Start Application

```bash
# Option 1: Backend only
npm run backend:dev

# Option 2: Backend + Frontend (if developing frontend)
npm run dev
```

Wait for:
```
Initializing database...
Database initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 3. Verify Health

Open: http://localhost:8000/health

Should return:
```json
{
  "status": "healthy",
  "service": "Time Registration CSV Parser"
}
```

## Phase 1: Database Verification

### 1.1 Check Database Created

```bash
# Should see lkservice.db file created
ls lkservice.db
```

### 1.2 Verify Tables

```bash
# Optional: inspect database
sqlite3 lkservice.db

# Then inside sqlite3, run these commands:
.tables
SELECT * FROM danlon_tokens;
.quit
```

Or as a one-liner:
```bash
sqlite3 lkservice.db "SELECT * FROM danlon_tokens;"
```

Should show `danlon_tokens` table (empty initially).

## Phase 2: Danløn OAuth Connection

### 2.1 Open Application

Navigate to: http://localhost:8000

You should see:
- Main upload interface
- Settings gear icon (⚙️) in the top right corner

### 2.2 Open Settings Menu

1. Click the **⚙️ Settings** icon in the top right corner
2. Settings menu should appear with two tabs:
   - "⚙️ Generelt" (General)
   - "🔗 Danløn Integration"
3. Click the **"🔗 Danløn Integration"** tab

### 2.3 Check Initial Connection Status

In the Danløn Integration tab, you should see:
- "Not Connected" status
- Blue info box
- "Connect to Danløn" button

### 2.4 Initiate Connection

Click **"Connect to Danløn"** button

**Expected:** Redirect to Danløn login page
- URL should be: `https://auth.lessor.dk/auth/realms/danlon-integration-demo/...`

### 2.5 Login to Danløn

Use demo credentials:
- **Username:** `simplysolutions`
- **Password:** `s5zC4uVFrJgGBYhMfybV`

Click **Login**

### 2.6 Give Consent

Danløn will ask for consent:
- Review permissions
- Click **"Allow"** or **"Grant Access"**

### 2.7 Select Company

If account has multiple companies:
- Select the company you want to connect
- Click **"Continue"** or **"Confirm"**

**Expected:** Redirect back to your app

### 2.8 Verify Success

You should see:
- Success page OR
- Redirect to app with "Connected to Danløn" green status

Open the **Settings menu** (⚙️) and go to the **Danløn Integration** tab:
- ✓ Green "Connected to Danløn" box
- Company name displayed
- Company ID shown
- Token expiry time shown

### 2.9 Verify Database Storage

```bash
sqlite3 lkservice.db
> SELECT user_id, company_id, company_name, created_at FROM danlon_tokens;
```

Should show one row with:
- `user_id`: "demo_user"
- `company_id`: (your company ID)
- `company_name`: (your company name)
- `created_at`: (current timestamp)

## Phase 3: Fetch Company Data

### 3.1 Test Company Info Endpoint

Open: http://localhost:8000/docs (Swagger UI)

Or use curl:

```bash
# Get company info
curl "http://localhost:8000/danlon/example/company-info?company_id=YOUR_COMPANY_ID"
```

Replace `YOUR_COMPANY_ID` with the company ID from Phase 2.

**Expected Response:**
```json
{
  "company": {
    "id": "...",
    "name": "...",
    "vat_number": "..."
  },
  "employees": {
    "count": 5,
    "list": [...]
  },
  "metadata": {
    "pay_codes": [...],
    "absence_codes": [...],
    "hour_types": [...]
  }
}
```

### 3.2 Note Important IDs

From the response, note:
- An **employee ID** (from `employees.list[0].id`)
- A **pay code ID** (from `metadata.pay_codes[0].id`)
- The **pay code** (from `metadata.pay_codes[0].code`)

You'll need these for testing!

## Phase 4: Process Time Registrations

### 4.1 Upload Test CSV

Option A: Use the web interface
1. Go to http://localhost:8000
2. Make sure "Upload CSV" tab is selected
3. Upload a test CSV file
4. Click "Vis Preview"

Option B: Use the API fetch
1. Click "Hent fra API" tab
2. Select employee and date range
3. Click fetch button

**Expected:** See preview data with daily and weekly tables

### 4.2 Verify Preview Data

Check that you see:
- Daily records table
- Weekly summary
- Overtime calculations
- Call-out indicators (if applicable)

## Phase 5: Sync to Danløn

### 5.1 Using Web Interface

1. Ensure you have preview data (from Phase 4)
2. Open the **Settings menu** (⚙️) in the top right corner
3. Click the **"🔗 Danløn Integration"** tab
4. Look for "📤 Sync to Danløn" card
5. Should show:
   - Connected status
   - "Sync to Danløn" button enabled

Click **"Sync to Danløn"**

Confirm the dialog

**Expected:**
- Syncing spinner
- After few seconds: Success message
- Summary showing:
  - Created: X payparts
  - Skipped: Y entries (if any)
  - Errors: Z entries (if any)

### 5.2 Review Sync Results

Check the results panel in the settings menu:
- ✓ Green success box
- Number of payparts created
- If any were skipped, click "Show Details" to see why

**Common skip reasons:**
- Employee not found (employee number doesn't match)
- Pay code not found (pay code doesn't exist in Danløn)
- Missing required fields

### 5.3 Using API Directly

Alternative test via curl:

```bash
curl -X POST "http://localhost:8000/danlon/example/sync-payparts?company_id=YOUR_COMPANY_ID"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Successfully created X payparts",
  "summary": {
    "created": X,
    "skipped": Y,
    "errors": 0
  },
  "created_payparts": [...]
}
```

## Phase 6: Verify in Danløn

### 6.1 Login to Danløn Portal

1. Go to the Danløn demo environment
2. Login with your credentials
3. Navigate to payroll/salary section

### 6.2 Check Payparts

Look for:
- The payparts you just created
- Correct dates
- Correct hours
- Correct amounts
- Correct employees

### 6.3 Verify Details

For each paypart:
- Employee matches
- Date is correct
- Hours calculated properly
- Rate is correct
- Amount = hours × rate

## Phase 7: Test Token Refresh

### 7.1 Wait for Token Expiry

Tokens expire after 5 minutes. Wait 5-6 minutes, then:

```bash
# Test that token auto-refreshes
curl "http://localhost:8000/danlon/example/company-info?company_id=YOUR_COMPANY_ID"
```

**Expected:**
- Should work without errors
- Token refreshed automatically
- Check logs for "Refreshing access token"

### 7.2 Check Database

```bash
sqlite3 lkservice.db
> SELECT updated_at FROM danlon_tokens;
```

`updated_at` should be more recent than `created_at`, indicating token was refreshed.

## Phase 8: Test Disconnection

### 8.1 Disconnect from App

In the web interface:
1. Open the **Settings menu** (⚙️)
2. Go to **"🔗 Danløn Integration"** tab
3. Click "🔌 Disconnect" button
4. Confirm

**Expected:**
- Success message
- Status changes to "Not Connected"
- "Connect to Danløn" button appears again

### 8.2 Verify Database

```bash
sqlite3 lkservice.db
> SELECT * FROM danlon_tokens;
```

Should return no rows (tokens deleted).

### 8.3 Reconnect

In the **Settings menu** (⚙️) > **Danløn Integration** tab, click "Connect to Danløn" again

Should go through OAuth flow again (already logged in, might skip login screen).

## Phase 9: Production Readiness Test

### 9.1 Test with Production Credentials (Optional)

If you have production credentials:

Update `.env`:
```bash
DANLON_ENVIRONMENT=prod
DANLON_CLIENT_ID=simplysolutions
DANLON_CLIENT_SECRET=oFqALlksfa3xK2CcQJXbXXaofXDH79Qd
```

Restart app and repeat Phases 2-6.

### 9.2 Test Error Handling

**Test 1: Invalid Company ID**
```bash
curl "http://localhost:8000/danlon/example/company-info?company_id=invalid"
```
Should return 500 with error message.

**Test 2: Not Connected**
```bash
# Disconnect first, then:
curl -X POST "http://localhost:8000/danlon/example/sync-payparts?company_id=test"
```
Should return error about not being connected.

**Test 3: Missing Fields**
Try syncing data with missing employee numbers or pay codes.
Should skip those entries with clear reason.

## Phase 10: Performance Test (Optional)

### 10.1 Test Large Batch

Create or upload a CSV with 100+ entries.

**Expected:**
- Should process without timeout
- Sync completes successfully
- All entries processed (created or skipped)

### 10.2 Check Logs

Monitor backend logs:
```
Danløn sync successful: X payparts created
```

## Complete Success Criteria

You've successfully completed testing when:

- [x] ✅ Database initialized automatically
- [x] ✅ Can connect to Danløn via OAuth
- [x] ✅ Connection status shows "Connected"
- [x] ✅ Tokens stored in database
- [x] ✅ Can fetch company info and employees
- [x] ✅ Can upload/process CSV files
- [x] ✅ Can sync data to Danløn
- [x] ✅ Sync shows success with counts
- [x] ✅ Payparts created in Danløn
- [x] ✅ Tokens auto-refresh after 5 minutes
- [x] ✅ Can disconnect and reconnect
- [x] ✅ Error handling works properly
- [x] ✅ Frontend UI shows all states correctly

## Troubleshooting Common Issues

### Issue: "Database not initialized"

**Fix:**
```bash
# Delete old database and restart
rm lkservice.db
npm run backend:dev
```

---

### Issue: "No module named 'app.models.danlon_tokens'"

**Fix:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: OAuth redirect fails

**Fix:**
- Check `APP_BASE_URL` in `.env`
- Should be exactly: `http://localhost:8000` (no trailing slash)
- Restart app after changing

---

### Issue: "Employee not found" when syncing

**Fix:**
- Check employee numbers in CSV match Danløn `employment_number`
- Use `/danlon/example/company-info` to see valid employee numbers
- Update CSV with correct employee numbers

---

### Issue: "Pay code not found"

**Fix:**
- Check pay codes in CSV match Danløn pay code codes
- Use `/danlon/example/company-info` to see valid pay codes
- Common codes: "100" (regular), "150" (overtime)

---

### Issue: Connection lost after app restart

**Fix:**
- This is expected with SQLite - tokens should persist
- Check `lkservice.db` exists
- If using PostgreSQL, connection should always persist

## Next Steps After Testing

1. ✅ Local testing complete
2. ⬜ Deploy to Railway (see `RAILWAY_DEPLOYMENT.md`)
3. ⬜ Test on Railway with production URL
4. ⬜ Configure production Danløn credentials
5. ⬜ Train users on the workflow
6. ⬜ Set up monitoring and alerts

## Test Report Template

Use this to document your test results:

```
Date: ___________
Tester: ___________

Phase 1 - Database: [ ] Pass [ ] Fail
Phase 2 - OAuth: [ ] Pass [ ] Fail
Phase 3 - Company Data: [ ] Pass [ ] Fail
Phase 4 - Process Data: [ ] Pass [ ] Fail
Phase 5 - Sync: [ ] Pass [ ] Fail
Phase 6 - Verify Danløn: [ ] Pass [ ] Fail
Phase 7 - Token Refresh: [ ] Pass [ ] Fail
Phase 8 - Disconnect: [ ] Pass [ ] Fail

Issues Found:
_________________________________
_________________________________

Notes:
_________________________________
_________________________________
```

---

**You're now ready for the full end-to-end test!** Follow each phase in order, and you'll verify the complete integration from connection to paypart creation. 🚀
