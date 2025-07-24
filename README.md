# Automotive Parts Scraper Web Application

A full-stack web application for processing automotive parts data and automatically detecting vehicle make compatibility through web scraping.

## Features

- **File Upload**: Drag-and-drop CSV file upload with validation
- **Real-time Processing**: Live progress updates via WebSocket
- **Flexible Range Selection**: Process all parts, test batches, or custom ranges
- **Interactive Controls**: Start, stop, and resume processing
- **Live Results Table**: Scrollable table with real-time result updates
- **Export Functionality**: Download enriched results as CSV
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

- **Backend**: FastAPI with WebSocket support
- **Frontend**: React with real-time updates
- **Data Processing**: Wraps existing AutoPartsDetector class
- **Web Scraping**: RockAuto and Google search fallback

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- Chrome browser (for Selenium)

### Running the Complete Application

1. **Clone and navigate to the project:**
   ```bash
   cd Parts_scraper
   ```

2. **Set up the virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   ```

4. **Install Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

5. **Start both servers (in separate terminals):**

   **Terminal 1 - Backend:**
   ```bash
   source venv/bin/activate
   python backend/main.py
   ```

   **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm start
   ```

6. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### Alternative: One-Terminal Setup

You can start both servers from the root directory:
```bash
# Start backend in background
source venv/bin/activate && python backend/main.py &

# Start frontend in background  
cd frontend && npm start &
```

## Detailed Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI server:
   ```bash
   python main.py
   ```

   **Note:** If you get import errors, run from the project root instead:
   ```bash
   cd ..  # Go back to project root
   source venv/bin/activate
   python backend/main.py
   ```

   The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the React development server:
   ```bash
   npm start
   ```

   The frontend will be available at `http://localhost:3000`

## Usage

### 1. Upload CSV File
- Drag and drop a CSV file or click "Browse Files"
- The file should contain columns: `Item #`, `Item Description`, `Qty`, `Unit Retail`, `Ext. Retail`
- The system will automatically categorize parts into Automotive, Tools, and Unknown

### 2. Configure Processing
- **Test Run**: Process first 50 automotive parts (recommended for testing)
- **Custom Range**: Specify start and end indices (e.g., 0-100)
- **Full Processing**: Process all automotive parts

### 3. Monitor Progress
- Real-time progress bar and statistics
- Live updates of current part being processed
- WebSocket connection status indicator

### 4. View Results
- Scrollable table with real-time result updates
- Status indicators (Found/Not Found)
- Vehicle make information and data source
- Auto-scroll to latest results (can be disabled)

### 5. Export Results
- Click "Export Results" to download CSV
- Includes processed automotive parts plus original tools/unknown parts
- Timestamped filename for easy organization

## API Endpoints

### HTTP Endpoints
- `POST /api/upload` - Upload CSV file
- `POST /api/start` - Start processing with parameters
- `POST /api/stop` - Stop current processing
- `GET /api/status` - Get current processing status
- `GET /api/results` - Get current results
- `POST /api/export` - Export results to CSV

### WebSocket
- `WS /ws` - Real-time progress and result updates

## File Structure

```
Parts_scraper/
├── rockauto_scraper.py          # Original scraper logic
├── backend/
│   ├── main.py                  # FastAPI server
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main React component
│   │   ├── index.js            # React entry point
│   │   ├── index.css           # Global styles
│   │   └── components/
│   │       ├── FileUpload.js   # File upload component
│   │       ├── ControlPanel.js # Processing controls
│   │       ├── ProgressIndicator.js # Progress display
│   │       └── ResultsTable.js # Results table
│   ├── public/
│   │   └── index.html          # HTML template
│   └── package.json            # Node.js dependencies
└── README.md                   # This file
```

## Development Notes

### Backend Features
- Wraps existing `AutoPartsDetector` class with async support
- WebSocket broadcasting for real-time updates
- Background task processing with stop/resume capability
- Proper error handling and session management

### Frontend Features
- React functional components with hooks
- Real-time WebSocket communication
- Responsive CSS Grid layout
- Auto-scroll with manual override
- Notification system for user feedback

### Error Handling
- File upload validation
- Range validation with user feedback
- WebSocket reconnection logic
- Processing error recovery

## Testing the Complete Flow

1. **Start both servers** (backend on :8000, frontend on :3000)
2. **Upload test CSV file** (use existing enriched_parts_test.csv)
3. **Run test processing** (50 parts) to verify functionality
4. **Test stop/resume** functionality
5. **Try custom ranges** (e.g., 1-10)
6. **Export results** and verify CSV output
7. **Test error scenarios** (invalid files, network issues)

## Troubleshooting

### Common Issues

1. **WebSocket connection fails**: Check if backend is running on port 8000
2. **File upload fails**: Ensure CSV has required columns
3. **Processing stalls**: Check browser console for errors
4. **Selenium errors**: Ensure Chrome browser is installed

### Performance Tips

- Use test runs before processing large datasets
- Stop processing if needed - partial results are saved
- Clear browser cache if experiencing UI issues
- Monitor backend logs for scraping issues

## Future Enhancements

- [ ] Table sorting and filtering
- [ ] Result pagination for large datasets
- [ ] Processing history and session management
- [ ] Advanced search and filtering options
- [ ] Batch export with custom formats
- [ ] Processing templates and presets