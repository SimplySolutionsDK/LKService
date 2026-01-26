# LKService

Time Registration CSV Parser - A FastAPI application for processing time registration CSV files with overtime calculations based on Danish automotive industry rules (DBR/Industriens Overenskomst 2026).

## Features

- **CSV File Processing**: Upload and parse time registration CSV files
- **Overtime Calculation**: Automatic overtime calculations following Danish automotive industry collective agreement rules
- **Multiple Employee Types**: Support for Lærling, Svend, Funktionær, and Elev
- **Call-out Detection**: Identifies and handles call-out eligible time entries
- **Multiple Export Formats**: Daily, weekly, or combined CSV output
- **Web Interface**: User-friendly interface for file upload and data preview
- **Session-based Preview**: Preview calculated data before exporting

## Technology Stack

- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pandas**: Data processing
- **Pydantic**: Data validation
- **Jinja2**: Template rendering

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LKService.git
cd LKService
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Locally

Start the development server:
```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

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