# Frontend - React TypeScript Application

This is the React + TypeScript frontend for the LKService Time Registration Parser.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **CSS Modules** - Component-scoped styling

## Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── layout/       # Header, Footer
│   │   ├── upload/       # File upload components
│   │   ├── preview/      # Data preview components
│   │   ├── modals/       # Modal dialogs
│   │   └── ui/           # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API service layer
│   ├── types/            # TypeScript type definitions
│   └── styles/           # Global styles and CSS variables
├── public/               # Static assets
└── dist/                 # Built production files (gitignored)
```

## Development

### Prerequisites
- Node.js 20.19+ or 22.12+
- npm 11+

### Commands

```bash
# Install dependencies
npm install

# Start development server (with HMR)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Workflow

1. **Start the backend**: From the project root, run the FastAPI backend
   ```bash
   cd app
   uvicorn main:app --reload
   ```

2. **Start the frontend**: In a separate terminal
   ```bash
   cd frontend
   npm run dev
   ```

The Vite dev server will proxy API requests to `http://localhost:8000`.

## Production

To deploy:

1. Build the frontend:
   ```bash
   npm run build
   ```

2. The built files in `dist/` are automatically served by the FastAPI backend when you run:
   ```bash
   python -m uvicorn app.main:app
   ```

## API Integration

The frontend communicates with the FastAPI backend via:
- `/api/preview` - Upload and preview CSV files
- `/api/export/{session_id}` - Export processed data

See `src/services/api.ts` for the API client implementation.
