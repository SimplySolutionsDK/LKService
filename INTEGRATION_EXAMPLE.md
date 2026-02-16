# Integrating Danløn Sync into Your Workflow

This guide shows exactly how to add Danløn sync to your existing CSV processing workflow.

## Quick Integration (5 Minutes)

### Step 1: Add Sync Button to Your Upload Response

Modify your existing upload endpoint to include a `sync_to_danlon` option:

```python
from app.routers import upload
from app.services.danlon_sync import sync_time_registrations_to_danlon, check_danlon_connection

@upload.router.post("/upload")
async def upload_csv(
    file: UploadFile,
    company_id: Optional[str] = None,
    auto_sync: bool = False
):
    """Your existing upload endpoint with Danløn sync added."""
    
    # Your existing CSV processing logic
    processed_data = await process_csv_file(file)
    
    # If user wants to sync to Danløn
    danlon_result = None
    if auto_sync and company_id:
        user_id = "demo_user"  # TODO: Get from session
        
        # Check connection first
        is_connected = await check_danlon_connection(user_id, company_id)
        
        if is_connected:
            # Sync to Danløn
            danlon_result = await sync_time_registrations_to_danlon(
                user_id=user_id,
                company_id=company_id,
                time_registrations=processed_data["time_entries"]
            )
        else:
            danlon_result = {
                "success": False,
                "message": "Not connected to Danløn. Please connect first."
            }
    
    return {
        "processed_data": processed_data,
        "danlon_sync": danlon_result.to_dict() if danlon_result else None
    }
```

### Step 2: Add Frontend Sync Button

```typescript
// In your React component
import { useState } from 'react';

function UploadPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [companyId, setCompanyId] = useState('');
  
  // Check connection status on mount
  useEffect(() => {
    checkDanlonConnection();
  }, []);
  
  async function checkDanlonConnection() {
    const response = await fetch(`/danlon/status?company_id=${companyId}`);
    const data = await response.json();
    setIsConnected(data.connected);
  }
  
  async function connectToDanlon() {
    window.location.href = '/danlon/connect';
  }
  
  async function uploadAndSync(file: File, autoSync: boolean) {
    const formData = new FormData();
    formData.append('file', file);
    
    const params = new URLSearchParams({
      company_id: companyId,
      auto_sync: autoSync.toString()
    });
    
    const response = await fetch(`/upload?${params}`, {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.danlon_sync) {
      if (result.danlon_sync.success) {
        alert(`Success! Created ${result.danlon_sync.summary.created} payparts`);
      } else {
        alert(`Sync failed: ${result.danlon_sync.message}`);
      }
    }
    
    return result;
  }
  
  return (
    <div>
      <h1>Upload Time Registrations</h1>
      
      {/* Connection Status */}
      <div className="danlon-status">
        {isConnected ? (
          <span>✓ Connected to Danløn</span>
        ) : (
          <button onClick={connectToDanlon}>
            Connect to Danløn
          </button>
        )}
      </div>
      
      {/* Upload Form */}
      <input type="file" onChange={(e) => handleFileChange(e.target.files[0])} />
      
      {/* Sync Option */}
      {isConnected && (
        <label>
          <input type="checkbox" checked={autoSync} onChange={...} />
          Automatically sync to Danløn after processing
        </label>
      )}
      
      <button onClick={() => uploadAndSync(file, autoSync)}>
        Upload {autoSync ? 'and Sync' : ''}
      </button>
    </div>
  );
}
```

## Complete Workflow Example

Here's a complete example showing the full worker flow:

```python
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
from app.services.csv_parser import parse_csv
from app.services.overtime_calculator import calculate_overtime
from app.services.danlon_sync import sync_time_registrations_to_danlon
from app.services.danlon_api import get_danlon_api_service

router = APIRouter(prefix="/workflow", tags=["Complete Workflow"])

@router.post("/process-and-sync")
async def complete_workflow(
    file: UploadFile,
    company_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = "demo_user"
):
    """
    Complete workflow:
    1. Parse CSV
    2. Calculate overtime
    3. Let worker review/compare
    4. Sync to Danløn when approved
    """
    
    # Step 1: Parse CSV
    raw_data = await parse_csv(file)
    
    # Step 2: Calculate overtime and process
    processed_data = calculate_overtime(raw_data)
    
    # Step 3: Get Danløn company info for comparison
    api = get_danlon_api_service(user_id, company_id)
    company_info = await api.get_current_company()
    employees = await api.get_employees()
    
    # Return data for worker to review
    return {
        "status": "ready_for_review",
        "processed_data": processed_data,
        "danlon_company": company_info,
        "danlon_employees": employees,
        "total_entries": len(processed_data["time_entries"]),
        "next_action": "POST /workflow/approve-and-sync to sync to Danløn"
    }


@router.post("/approve-and-sync")
async def approve_and_sync(
    session_id: str,  # Your session/batch ID
    company_id: str,
    user_id: str = "demo_user"
):
    """
    After worker has reviewed and approved, sync to Danløn.
    """
    
    # Get the processed data from your storage
    # (In reality, you'd fetch this from database based on session_id)
    processed_data = get_processed_data(session_id)
    
    # Sync to Danløn
    result = await sync_time_registrations_to_danlon(
        user_id=user_id,
        company_id=company_id,
        time_registrations=processed_data["time_entries"]
    )
    
    if result.success:
        # Mark as synced in your database
        mark_as_synced(session_id, result.created_payparts)
        
        return {
            "status": "synced",
            "message": f"Successfully created {result.created_count} payparts",
            "details": result.to_dict()
        }
    else:
        return {
            "status": "sync_failed",
            "message": result.message,
            "details": result.to_dict()
        }
```

## Alternative: Manual Sync After Review

If you want workers to manually trigger sync after comparing:

```python
@router.get("/review/{session_id}")
async def review_session(
    session_id: str,
    company_id: str,
    user_id: str = "demo_user"
):
    """Get data for worker to review."""
    
    processed_data = get_processed_data(session_id)
    
    # Get Danløn data for comparison
    api = get_danlon_api_service(user_id, company_id)
    danlon_employees = await api.get_employees()
    danlon_meta = await api.get_paypart_meta()
    
    return {
        "session_id": session_id,
        "processed_data": processed_data,
        "danlon_employees": danlon_employees,
        "danlon_pay_codes": danlon_meta["pay_codes"],
        "comparison": compare_data(processed_data, danlon_employees)
    }


@router.post("/sync/{session_id}")
async def sync_session(
    session_id: str,
    company_id: str,
    user_id: str = "demo_user"
):
    """Sync a reviewed session to Danløn."""
    
    processed_data = get_processed_data(session_id)
    
    result = await sync_time_registrations_to_danlon(
        user_id=user_id,
        company_id=company_id,
        time_registrations=processed_data["time_entries"]
    )
    
    return result.to_dict()
```

## Field Mapping Customization

If your CSV has different field names, specify the mapping:

```python
result = await sync_time_registrations_to_danlon(
    user_id=user_id,
    company_id=company_id,
    time_registrations=data,
    # Custom field mappings
    employee_number_field="medarbejder_nr",
    date_field="dato",
    hours_field="timer",
    rate_field="timeløn",
    pay_code_field="lønart",
    description_field="beskrivelse",
    reference_field="reference_nummer"
)
```

Or use auto-detection:

```python
from app.services.danlon_sync import sync_csv_data_to_danlon

# This automatically detects common field name variations
result = await sync_csv_data_to_danlon(
    user_id=user_id,
    company_id=company_id,
    csv_data=your_csv_data
)
```

## Error Handling Best Practices

```python
async def safe_sync_to_danlon(user_id, company_id, data):
    """Sync with proper error handling."""
    
    try:
        # Check connection first
        from app.services.danlon_sync import check_danlon_connection
        
        if not await check_danlon_connection(user_id, company_id):
            return {
                "success": False,
                "error": "not_connected",
                "message": "Please connect to Danløn first",
                "action_url": "/danlon/connect"
            }
        
        # Perform sync
        result = await sync_time_registrations_to_danlon(
            user_id=user_id,
            company_id=company_id,
            time_registrations=data
        )
        
        # Log results
        if result.success:
            logger.info(
                f"Danløn sync successful: {result.created_count} payparts created"
            )
        else:
            logger.warning(
                f"Danløn sync failed: {result.message}"
            )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Danløn sync exception: {str(e)}")
        return {
            "success": False,
            "error": "exception",
            "message": str(e)
        }
```

## Background Processing

For large batches, process sync in the background:

```python
from fastapi import BackgroundTasks

async def sync_in_background(user_id, company_id, data, session_id):
    """Background task for syncing."""
    result = await sync_time_registrations_to_danlon(
        user_id=user_id,
        company_id=company_id,
        time_registrations=data
    )
    
    # Update status in database
    update_sync_status(session_id, result.to_dict())
    
    # Optionally notify user (email, websocket, etc.)
    notify_user(user_id, f"Sync complete: {result.message}")


@router.post("/sync-async/{session_id}")
async def sync_async(
    session_id: str,
    company_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = "demo_user"
):
    """Start background sync."""
    
    data = get_processed_data(session_id)
    
    background_tasks.add_task(
        sync_in_background,
        user_id,
        company_id,
        data,
        session_id
    )
    
    return {
        "status": "sync_started",
        "message": "Sync running in background",
        "session_id": session_id,
        "check_status_url": f"/workflow/status/{session_id}"
    }
```

## Summary

To integrate Danløn sync into your workflow:

1. ✅ Import the sync function: `from app.services.danlon_sync import sync_time_registrations_to_danlon`

2. ✅ Add connection check in your UI

3. ✅ Call sync function after worker approves data

4. ✅ Handle the result and show feedback to worker

5. ✅ Optional: Add background processing for large batches

The integration is designed to be simple - just one function call to sync your data!
