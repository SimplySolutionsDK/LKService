# LKService

Time Registration CSV Parser - A FastAPI application for processing time registration CSV files with overtime calculations based on Danish automotive industry rules (DBR/Industriens Overenskomst 2026).

## Features

- **CSV File Processing**: Upload and parse time registration CSV files
- **Overtime Calculation**: Automatic overtime calculations following Danish automotive industry collective agreement rules
- **Multiple Employee Types**: Support for Lærling, Svend, Funktionær, and Elev
- **Credited Hours**: Automatic crediting of vacation, sick days, and public holidays (7.4 hours per day) toward weekly norm
- **Call-out Detection**: Identifies and handles call-out eligible time entries
- **Multiple Export Formats**: Daily, weekly, or combined CSV output
- **Web Interface**: User-friendly interface for file upload and data preview
- **Session-based Preview**: Preview calculated data before exporting

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pandas**: Data processing
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **CSS Modules**: Component-scoped styling

## Local Development

### Prerequisites

- Python 3.11 or higher
- Node.js 20.19+ or 22.12+
- npm 11+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LKService.git
cd LKService
```

2. **Backend Setup**:
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Configure API credentials
cp .env.example .env
# Edit .env with your actual API credentials
```

3. **Frontend Setup**:
```bash
# Navigate to frontend directory
cd frontend

# Copy environment template and configure API endpoints
cp .env.example .env.local
# Edit .env.local with your actual API URLs

# Install Node.js dependencies
npm install

# Build the frontend for production
npm run build

# Return to project root
cd ..
```

### API Configuration

The application supports fetching time registration data directly from external APIs as an alternative to CSV uploads.

**Backend Configuration (Required):**

1. **Copy the environment template** in the project root:
```bash
cp .env.example .env
```

2. **Edit `.env`** with your actual API credentials:
```bash
# External API Configuration
CORE_API_URL=https://apigw.ftzplus.dk/external/coreapi/api/
TIME_API_URL=https://apigw.ftzplus.dk/external/timeregistrationapi/api/

# API Authentication Key (from your API provider)
API_AUTH_KEY=your-actual-api-key-here

# Azure API Management Subscription Key (if required)
APIM_SUBSCRIPTION_KEY=your-subscription-key-here
```

3. **Restart the backend** to apply changes:
```bash
cd app
uvicorn main:app --reload
```

**Frontend Configuration (Optional):**

The frontend uses the Vite proxy to communicate with the backend, so no frontend configuration is needed for API access. However, you can customize the API URLs displayed in the UI by creating `frontend/.env.local`:

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local if needed (optional)
npm run build  # Required after changes
```

**Authentication Flow:**

The backend automatically handles authentication with the external APIs:
1. Requests a bearer token from the authentication endpoint using your API_AUTH_KEY
2. Caches the token and refreshes it before expiry
3. Adds required headers (Authorization, Ocp-Apim-Subscription-Key) to all API requests

No manual token management is required.

### Running Locally

#### Development Mode

For active development, run both the backend and frontend in separate terminals:

**Terminal 1 - Backend:**
```bash
# From project root (not from inside app directory)
python -m uvicorn app.main:app --reload

# Or on Windows with venv:
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
# From project root
cd frontend
npm run dev
```

The frontend dev server (http://localhost:5173) will proxy API requests to the backend (http://localhost:8000).

#### Production Mode

For production-like testing with the built frontend:

1. Build the frontend (if not already done):
```bash
cd frontend
npm run build
cd ..
```

2. Start the backend server (from project root):
```bash
python -m uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000` serving the built React app.

### API Endpoints

- `GET /` - Main web interface
- `GET /health` - Health check endpoint
- `POST /api/upload` - Upload and process CSV files
- `POST /api/preview` - Preview processed data
- `POST /api/export/{session_id}` - Export previewed data
- `POST /api/process` - Process and download in one step

## Deployment to Railway

This application is configured for easy deployment to Railway.

### Prerequisites

- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))

### Deployment Steps

1. **Push to GitHub**:
   - Ensure all changes are committed and pushed to your GitHub repository

2. **Connect to Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose the `LKService` repository
   - Railway will automatically detect the Python application

3. **Automatic Configuration**:
   - Railway reads the `Procfile` for start commands
   - `railway.toml` configures deployment settings
   - `runtime.txt` specifies Python version
   - Environment variables are automatically set

4. **Access Your App**:
   - Railway provides a public URL (e.g., `your-app.up.railway.app`)
   - Test the `/health` endpoint to verify deployment
   - Access the web interface at the root URL

### Auto-Deployment

Every push to the `main` branch triggers an automatic deployment to Railway.

### Configuration Files

- `Procfile`: Defines the web server start command
- `railway.toml`: Railway-specific deployment configuration
- `runtime.txt`: Specifies Python version
- `requirements.txt`: Python dependencies

## Project Structure

```
LKService/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   └── upload.py        # API endpoints
│   ├── services/
│   │   ├── csv_parser.py    # CSV parsing logic
│   │   ├── time_calculator.py
│   │   ├── overtime_calculator.py
│   │   ├── call_out_detector.py
│   │   ├── absence_detector.py  # Vacation/sick/holiday detection
│   │   └── csv_generator.py
│   └── templates/
│       └── index.html       # Web interface
├── Data/                    # Sample data files
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway start command
├── railway.toml             # Railway configuration
└── runtime.txt              # Python version
```

## License

All rights reserved.

## Support

For issues or questions, please open an issue in the GitHub repository.



# Credited Hours for Vacation, Sick Days, and Public Holidays

## Overview

The system now automatically credits **7.4 hours** (37 hours ÷ 5 days) toward the weekly norm for vacation days, sick days, and public holidays. This ensures that overtime is calculated correctly when employees have days off.

## How It Works

### Standard Daily Credit
- **7.4 hours** are credited for each vacation, sick, or public holiday day
- These credited hours count toward the 37-hour weekly norm
- Any work hours beyond the norm (including credited hours) count as overtime

### Example Scenarios

#### Scenario 1: Wednesday Vacation Day
- Monday: 8 hours worked
- Tuesday: 8 hours worked
- Wednesday: 0 hours worked, **7.4 hours credited** (vacation)
- Thursday: 8 hours worked
- Friday: 8 hours worked

**Calculation:**
- Total worked: 32 hours
- Total credited: 7.4 hours
- **Weekly total: 39.4 hours**
- Normal hours: 37 hours
- **Overtime: 2.4 hours**

#### Scenario 2: Thursday & Friday Public Holidays
- Monday: 10 hours worked
- Tuesday: 10 hours worked
- Wednesday: 10 hours worked
- Thursday: 0 hours worked, **7.4 hours credited** (public holiday)
- Friday: 0 hours worked, **7.4 hours credited** (public holiday)

**Calculation:**
- Total worked: 30 hours
- Total credited: 14.8 hours (7.4 × 2)
- **Weekly total: 44.8 hours**
- Normal hours: 37 hours
- **Overtime: 7.8 hours**

## Automatic Detection

The system automatically detects absence types based on activity keywords in Danish or English:

### Vacation (Ferie)
- "ferie"
- "vacation"
- "afspadsering"
- "fridag"

### Sick Leave (Syg)
- "syg"
- "sygdom"
- "sick"
- "barns sygedag"
- "barns 1. sygedag"
- "barns 2. sygedag"

### Public Holidays (Helligdage)
- "helligdag"
- "holiday"
- "public holiday"
- "juledag"
- "nytårsdag"
- "påske"
- "pinse"
- "store bededag"
- "kr. himmelfartsdag"
- "grundlovsdag"

## CSV Input Example

If an employee registers a time entry with activity "Ferie" on a day, that day will automatically be credited with 7.4 hours:

```csv
Tidsregistrering
Jakob Nielsen

Onsdag 15-01-2026
Aktivitet:;Start Tid:;Pause:;Slut Tid:;Varighed:
Ferie;00:00;;00:00;0 Timer 0 Minutter
```

This will result in:
- Worked hours: 0
- Credited hours: 7.4
- Day counted as vacation for overtime calculation

## Manual Override

If automatic detection doesn't work, the system can be extended to support manual marking of days through the UI or API endpoints.
