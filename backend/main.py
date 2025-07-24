#!/usr/bin/env python3
"""
FastAPI Backend for Automotive Parts Scraper
Wraps the AutoPartsDetector class and provides REST API and WebSocket endpoints.
"""

import asyncio
import json
import os
import uuid
import pickle
from typing import Dict, List, Optional, Callable
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# Import the existing AutoPartsDetector
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rockauto_scraper import AutoPartsDetector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Automotive Parts Scraper API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state management
class ProcessingState:
    def __init__(self):
        self.is_processing = False
        self.current_session_id = None
        self.detector = None
        self.parts_data = None
        self.total_parts = 0
        self.processed_count = 0
        self.results = []
        self.start_index = 0
        self.end_index = 0
        self.error_message = None
        self.connected_clients = set()
        self.should_stop = False
        self.make_leaderboard = {}  # {make: {'count': int, 'weighted_count': int}}
        self.history = []  # List of completed processing runs
        
    def reset(self):
        """Reset processing state"""
        self.is_processing = False
        self.current_session_id = None
        self.detector = None
        self.parts_data = None
        self.total_parts = 0
        self.processed_count = 0
        self.results = []
        self.start_index = 0
        self.end_index = 0
        self.error_message = None
        self.should_stop = False
        self.make_leaderboard = {}
    
    def reset_processing_only(self):
        """Reset only processing state, keep uploaded data"""
        self.is_processing = False
        self.current_session_id = None
        self.processed_count = 0
        self.results = []
        self.start_index = 0
        self.end_index = 0
        self.error_message = None
        self.should_stop = False
        self.make_leaderboard = {}
        self.session_file = None  # Will store path to saved session
    
    def save_session(self):
        """Save current session to disk for resume capability"""
        if not self.current_session_id:
            return None
            
        # Create sessions directory
        sessions_dir = Path("sessions")
        sessions_dir.mkdir(exist_ok=True)
        
        # Save session data
        session_data = {
            'session_id': self.current_session_id,
            'parts_data': self.parts_data,
            'total_parts': self.total_parts,
            'processed_count': self.processed_count,
            'results': self.results,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'make_leaderboard': self.make_leaderboard,
            'timestamp': datetime.now().isoformat()
        }
        
        session_file = sessions_dir / f"session_{self.current_session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        self.session_file = str(session_file)
        logger.info(f"Session saved to {session_file}")
        return str(session_file)
    
    def load_session(self, session_id: str):
        """Load a saved session from disk"""
        session_file = Path("sessions") / f"session_{session_id}.json"
        
        if not session_file.exists():
            return False
            
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Restore session state
            self.current_session_id = session_data['session_id']
            self.parts_data = session_data['parts_data']
            self.total_parts = session_data['total_parts']
            self.processed_count = session_data['processed_count']
            self.results = session_data['results']
            self.start_index = session_data['start_index']
            self.end_index = session_data['end_index']
            self.make_leaderboard = session_data['make_leaderboard']
            self.session_file = str(session_file)
            
            logger.info(f"Session {session_id} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return False
    
    def get_available_sessions(self):
        """Get list of available saved sessions"""
        sessions_dir = Path("sessions")
        if not sessions_dir.exists():
            return []
            
        sessions = []
        for session_file in sessions_dir.glob("session_*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                sessions.append({
                    'session_id': session_data['session_id'],
                    'timestamp': session_data['timestamp'],
                    'processed_count': session_data['processed_count'],
                    'total_parts': session_data['total_parts'],
                    'progress_percentage': (session_data['processed_count'] / (session_data['end_index'] - session_data['start_index'])) * 100 if session_data['end_index'] > session_data['start_index'] else 0
                })
            except Exception as e:
                logger.warning(f"Error reading session file {session_file}: {e}")
                
        # Sort by timestamp, newest first
        sessions.sort(key=lambda x: x['timestamp'], reverse=True)
        return sessions
    
    def save_to_history(self):
        """Save completed processing run to history"""
        if not self.results or not self.current_session_id:
            return None
            
        # Create history directory
        history_dir = Path("history")
        history_dir.mkdir(exist_ok=True)
        
        # Calculate summary statistics
        total_processed = len(self.results)
        successful_lookups = sum(1 for r in self.results if r.get('makes') and r['makes'] != 'NOT_FOUND')
        success_rate = (successful_lookups / total_processed) * 100 if total_processed > 0 else 0
        
        # Get top makes for this session
        top_makes = self.get_top_makes(5)
        
        # Create history entry
        history_entry = {
            'id': self.current_session_id,
            'timestamp': datetime.now().isoformat(),
            'filename': f"history_{self.current_session_id}.json",
            'summary': {
                'total_processed': total_processed,
                'successful_lookups': successful_lookups,
                'success_rate': success_rate,
                'start_index': self.start_index,
                'end_index': self.end_index,
                'total_parts_in_file': self.total_parts,
                'top_makes': top_makes[:3]  # Top 3 makes for preview
            },
            'results': self.results,
            'leaderboard': dict(self.make_leaderboard),
            'parts_data': {
                'automotive_count': len(self.parts_data.get('automotive', [])),
                'tools_count': len(self.parts_data.get('tools', [])),
                'unknown_count': len(self.parts_data.get('unknown', []))
            }
        }
        
        # Save detailed results to file
        history_file = history_dir / f"history_{self.current_session_id}.json"
        with open(history_file, 'w') as f:
            json.dump(history_entry, f, indent=2)
        
        # Add summary to in-memory history (without full results for performance)
        history_summary = {
            'id': self.current_session_id,
            'timestamp': history_entry['timestamp'],
            'filename': history_entry['filename'],
            'summary': history_entry['summary']
        }
        
        # Add to beginning of history list and keep last 50 entries
        self.history.insert(0, history_summary)
        self.history = self.history[:50]
        
        logger.info(f"Processing run saved to history: {history_file}")
        return str(history_file)
    
    def load_history_entry(self, entry_id: str):
        """Load full results for a specific history entry"""
        history_file = Path("history") / f"history_{entry_id}.json"
        
        if not history_file.exists():
            return None
            
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history entry {entry_id}: {e}")
            return None
    
    def get_history_list(self):
        """Get list of history entries (summaries only)"""
        # Load history from disk if not in memory
        if not self.history:
            self.load_history_from_disk()
        return self.history
    
    def load_history_from_disk(self):
        """Load history summaries from disk"""
        history_dir = Path("history")
        if not history_dir.exists():
            return
            
        history_entries = []
        for history_file in history_dir.glob("history_*.json"):
            try:
                with open(history_file, 'r') as f:
                    entry = json.load(f)
                    # Extract just the summary for the list
                    summary = {
                        'id': entry['id'],
                        'timestamp': entry['timestamp'],
                        'filename': entry['filename'],
                        'summary': entry['summary']
                    }
                    history_entries.append(summary)
            except Exception as e:
                logger.warning(f"Error reading history file {history_file}: {e}")
        
        # Sort by timestamp, newest first
        history_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        self.history = history_entries[:50]  # Keep last 50 entries
    
    def update_leaderboard(self, makes_list, quantity):
        """Update the make leaderboard with weighted counts"""
        if makes_list and makes_list != 'NOT_FOUND':
            # Split makes by comma and clean them
            makes = [make.strip() for make in makes_list.split(',') if make.strip()]
            
            for make in makes:
                if make not in self.make_leaderboard:
                    self.make_leaderboard[make] = {'count': 0, 'weighted_count': 0}
                
                self.make_leaderboard[make]['count'] += 1
                self.make_leaderboard[make]['weighted_count'] += quantity
    
    def get_top_makes(self, limit=10):
        """Get top makes sorted by weighted count"""
        sorted_makes = sorted(
            self.make_leaderboard.items(),
            key=lambda x: x[1]['weighted_count'],
            reverse=True
        )
        return sorted_makes[:limit]

# Global state instance
state = ProcessingState()

# Pydantic models for API requests/responses
class ProcessingRequest(BaseModel):
    start_index: int = 0
    end_index: Optional[int] = None
    is_test: bool = False

class StatusResponse(BaseModel):
    is_processing: bool
    session_id: Optional[str]
    total_parts: int
    processed_count: int
    progress_percentage: float
    error_message: Optional[str]
    has_data: bool

class ResumeRequest(BaseModel):
    session_id: str

class SessionInfo(BaseModel):
    session_id: str
    timestamp: str
    processed_count: int
    total_parts: int
    progress_percentage: float

class HistorySummary(BaseModel):
    id: str
    timestamp: str
    summary: Dict
    
class HistoryEntry(BaseModel):
    id: str
    timestamp: str
    summary: Dict
    results: List[Dict]
    leaderboard: Dict
    parts_data: Dict

class PartResult(BaseModel):
    index: int
    item_num: str
    part_number: str
    description: str
    qty: int
    unit_retail: float
    ext_retail: float
    category: str
    makes: Optional[str] = None
    source: Optional[str] = None

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        state.connected_clients.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in state.connected_clients:
            state.connected_clients.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        logger.info(f"Broadcasting to {len(self.active_connections)} clients: {message.get('type', 'unknown')}")
        if not self.active_connections:
            logger.warning("No active WebSocket connections to broadcast to")
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
                logger.debug(f"Message sent successfully to client")
            except Exception as e:
                logger.warning(f"Failed to send message to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Enhanced AutoPartsDetector with callback support
class WebAutoPartsDetector(AutoPartsDetector):
    def __init__(self, csv_file: str, progress_callback: Optional[Callable] = None):
        super().__init__(csv_file)
        self.progress_callback = progress_callback
        
    async def process_parts_batch_async(self, parts: List[Dict], max_parts: int = 10, 
                                       start_idx: int = 0) -> List[Dict]:
        """Async version of process_parts_batch with progress callbacks"""
        results = []
        successful_lookups = 0
        
        logger.info(f"Starting async batch processing of {min(max_parts, len(parts))} parts...")
        
        for i, part in enumerate(parts[:max_parts]):
            # Check if we should stop
            if state.should_stop:
                logger.info("Processing stopped by user request")
                break
                
            part_number = part['part_number']
            logger.info(f"Processing part {i+1}/{min(max_parts, len(parts))}: {part_number}")
            
            # Send progress update every part for real-time feel (optimized out the 0.1s delay instead)
            logger.info(f"Checking progress callback: {self.progress_callback is not None}")
            if self.progress_callback:
                # Calculate success rate so far
                current_successful = sum(1 for r in results if r.get('makes') and r['makes'] != 'NOT_FOUND')
                success_rate = (current_successful / len(results)) * 100 if results else 0
                
                # Calculate correct progress percentage for the entire range
                total_in_range = state.end_index - state.start_index
                # Current absolute position in the range (adding i+1 to existing processed count)
                absolute_processed = state.processed_count + i + 1
                progress_pct = (absolute_processed / total_in_range) * 100 if total_in_range > 0 else 0
                
                logger.info("Calling progress callback for progress update")
                await self.progress_callback({
                    'type': 'progress',
                    'current_index': start_idx + i,
                    'total_parts': state.total_parts,
                    'processed_count': absolute_processed,
                    'successful_lookups': current_successful,
                    'success_rate': success_rate,
                    'leaderboard': state.get_top_makes(10),
                    'current_part': {
                        'part_number': part_number,
                        'description': part['description']
                    },
                    'progress_percentage': min(progress_pct, 100)
                })
            
            # Only use RockAuto - no unreliable fallback methods
            makes = self.search_rockauto(part_number, part['description'], part.get('item_num', ''))
            source = 'RockAuto'
            
            # Record results
            part_result = part.copy()
            if makes:
                unique_makes = list(set(makes))
                unique_makes.sort()
                
                part_result['makes'] = ', '.join(unique_makes)
                part_result['source'] = source
                part_result['category'] = 'Automotive'
                successful_lookups += 1
                logger.info(f"✅ Found makes for {part_number}: {part_result['makes']}")
            else:
                part_result['makes'] = 'NOT_FOUND'
                part_result['source'] = 'NONE'
                part_result['category'] = 'Automotive'
                logger.warning(f"❌ No makes found for {part_number}")
            
            results.append(part_result)
            # Update the global processed count correctly
            state.processed_count = state.processed_count + 1 if hasattr(state, 'processed_count') and state.processed_count else i + 1
            state.results = results
            
            # Update leaderboard with weighted counts
            state.update_leaderboard(part_result['makes'], part_result['qty'])
            
            # Save progress every 10 parts
            if (i + 1) % 10 == 0:
                state.save_session()
            
            # Send result update for every part (ensure real-time updates)
            if self.progress_callback:
                logger.info("Calling progress callback for result update")
                await self.progress_callback({
                    'type': 'result',
                    'result': {
                        'index': start_idx + i,
                        'item_num': part_result['item_num'],
                        'part_number': part_result['part_number'],
                        'description': part_result['description'],
                        'qty': part_result['qty'],
                        'unit_retail': part_result['unit_retail'],
                        'ext_retail': part_result['ext_retail'],
                        'category': part_result['category'],
                        'makes': part_result['makes'],
                        'source': part_result['source']
                    },
                    'leaderboard': state.get_top_makes(10)
                })
            
            # Removed 0.1s delay - UI can handle the updates fine
        
        # Close browser after processing
        self._close_browser()
        
        success_rate = (successful_lookups / len(results)) * 100 if results else 0
        logger.info(f"Async batch processing complete! Success rate: {success_rate:.1f}%")
        
        return results

# API Endpoints

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV file and parse it"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Save uploaded file temporarily
        temp_filename = f"temp_{uuid.uuid4().hex}.csv"
        temp_path = os.path.join("uploads", temp_filename)
        
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Save file
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Initialize detector and load data
        detector = WebAutoPartsDetector(temp_path)
        detector.load_data()
        
        # Categorize parts
        categorized = detector.categorize_parts()
        
        # Store in state
        state.detector = detector
        state.parts_data = categorized
        state.total_parts = len(categorized['automotive'])
        state.reset_processing_only()  # Reset only processing state, keep uploaded data
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "message": "File uploaded successfully",
            "total_automotive_parts": len(categorized['automotive']),
            "total_tool_parts": len(categorized['tools']),
            "total_unknown_parts": len(categorized['unknown'])
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start")
async def start_processing(request: ProcessingRequest):
    """Start processing parts"""
    logger.info(f"Processing request received: start_index={request.start_index}, end_index={request.end_index}, is_test={request.is_test}")
    logger.info(f"Current state: is_processing={state.is_processing}, parts_data exists={state.parts_data is not None}")
    if state.parts_data:
        logger.info(f"Parts data keys: {list(state.parts_data.keys()) if state.parts_data else 'None'}")
        logger.info(f"Automotive parts count: {len(state.parts_data.get('automotive', [])) if state.parts_data else 'N/A'}")
    try:
        if state.is_processing:
            logger.error("Processing already in progress")
            raise HTTPException(status_code=400, detail="Processing already in progress")
        
        if not state.parts_data:
            logger.error("No parts data found in state")
            raise HTTPException(status_code=400, detail="No data loaded. Please upload a CSV file first.")
        
        # Set up processing parameters
        automotive_parts = state.parts_data['automotive']
        total_parts = len(automotive_parts)
        
        if request.is_test:
            # Test mode: process first 50 parts
            start_idx = 0
            end_idx = min(50, total_parts)
        else:
            # Use provided range
            start_idx = request.start_index
            end_idx = request.end_index if request.end_index is not None else total_parts
            
        # Validate range
        if start_idx < 0 or start_idx >= total_parts:
            raise HTTPException(status_code=400, detail=f"Invalid start index: {start_idx}. Must be between 0 and {total_parts-1}")
        if end_idx <= start_idx:
            raise HTTPException(status_code=400, detail=f"Invalid range: end_idx ({end_idx}) must be greater than start_idx ({start_idx})")
        if end_idx > total_parts:
            raise HTTPException(status_code=400, detail=f"Invalid end index: {end_idx}. Cannot exceed total parts ({total_parts})")
        
        # Set up state
        state.is_processing = True
        state.current_session_id = str(uuid.uuid4())
        state.start_index = start_idx
        state.end_index = end_idx
        state.processed_count = 0
        state.results = []
        state.should_stop = False
        state.error_message = None
        
        # Select parts to process
        parts_to_process = automotive_parts[start_idx:end_idx]
        
        # Start background processing
        asyncio.create_task(process_parts_background(parts_to_process, start_idx))
        
        return {
            "message": "Processing started",
            "session_id": state.current_session_id,
            "start_index": start_idx,
            "end_index": end_idx,
            "parts_to_process": len(parts_to_process)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting processing: {e}")
        state.reset()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_processing():
    """Stop current processing"""
    if not state.is_processing:
        return {"message": "No processing in progress"}
    
    state.should_stop = True
    
    # Close browser session if it exists
    if state.detector and hasattr(state.detector, 'driver') and state.detector.driver:
        try:
            state.detector.driver.quit()
            logger.info("Browser session closed due to stop request")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
    
    # Wait a moment for processing to stop
    await asyncio.sleep(1)
    
    # Save current progress before stopping
    if state.current_session_id:
        state.save_session()
    
    # Broadcast stop message
    await manager.broadcast({
        'type': 'stopped',
        'message': 'Processing stopped by user',
        'partial_results': len(state.results)
    })
    
    state.is_processing = False
    
    return {
        "message": "Processing stopped",
        "partial_results_count": len(state.results)
    }

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current processing status"""
    progress_percentage = 0
    if state.end_index > state.start_index:
        # Calculate progress based on how many parts we've processed in this range
        total_in_range = state.end_index - state.start_index
        progress_percentage = (state.processed_count / total_in_range) * 100
        # Ensure it doesn't exceed 100%
        progress_percentage = min(progress_percentage, 100)
    
    return StatusResponse(
        is_processing=state.is_processing,
        session_id=state.current_session_id,
        total_parts=state.total_parts,
        processed_count=state.processed_count,
        progress_percentage=progress_percentage,
        error_message=state.error_message,
        has_data=state.parts_data is not None
    )

@app.get("/api/results")
async def get_results():
    """Get current results"""
    return {
        "results": state.results,
        "total_results": len(state.results),
        "is_processing": state.is_processing
    }

@app.post("/api/export")
async def export_results():
    """Export results to CSV"""
    try:
        if not state.results:
            raise HTTPException(status_code=400, detail="No results to export")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enriched_parts_{timestamp}.csv"
        
        # Prepare data for export
        export_data = []
        for result in state.results:
            export_data.append({
                'Item #': result['item_num'],
                'Item Description': result['description'],
                'Qty': result['qty'],
                'Unit Retail': result['unit_retail'],
                'Ext. Retail': result['ext_retail'],
                'Part Number': result['part_number'],
                'Category': result['category'],
                'Makes': result.get('makes', 'NOT_PROCESSED'),
                'Source': result.get('source', 'N/A')
            })
        
        # Add tools and unknown parts if available
        if state.parts_data:
            for part in state.parts_data['tools']:
                export_data.append({
                    'Item #': part['item_num'],
                    'Item Description': part['description'],
                    'Qty': part['qty'],
                    'Unit Retail': part['unit_retail'],
                    'Ext. Retail': part['ext_retail'],
                    'Part Number': part['part_number'],
                    'Category': 'Tools',
                    'Makes': 'N/A (Tool)',
                    'Source': 'N/A'
                })
            
            for part in state.parts_data['unknown']:
                export_data.append({
                    'Item #': part['item_num'],
                    'Item Description': part['description'],
                    'Qty': part['qty'],
                    'Unit Retail': part['unit_retail'],
                    'Ext. Retail': part['ext_retail'],
                    'Part Number': part['part_number'],
                    'Category': 'Unknown',
                    'Makes': 'UNKNOWN_CATEGORY',
                    'Source': 'N/A'
                })
        
        # Create DataFrame and save
        df = pd.DataFrame(export_data)
        export_path = os.path.join("exports", filename)
        os.makedirs("exports", exist_ok=True)
        df.to_csv(export_path, index=False)
        
        return {
            "message": "Results exported successfully",
            "filename": filename,
            "total_rows": len(export_data),
            "file_path": export_path
        }
        
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_sessions():
    """Get list of available saved sessions"""
    try:
        sessions = state.get_available_sessions()
        return sessions
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume")
async def resume_session(request: ResumeRequest):
    """Resume processing from a saved session"""
    try:
        if state.is_processing:
            raise HTTPException(status_code=400, detail="Processing already in progress")
        
        # Load the session
        if not state.load_session(request.session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Calculate remaining parts to process
        remaining_parts = state.end_index - state.start_index - state.processed_count
        if remaining_parts <= 0:
            raise HTTPException(status_code=400, detail="Session already completed")
        
        # Set up processing to continue from where it left off
        automotive_parts = state.parts_data['automotive']
        start_from = state.start_index + state.processed_count
        parts_to_process = automotive_parts[start_from:state.end_index]
        
        # Resume processing
        state.is_processing = True
        state.should_stop = False
        state.error_message = None
        
        # Start background processing from the resume point
        asyncio.create_task(process_parts_background(parts_to_process, start_from))
        
        return {
            "message": "Session resumed successfully",
            "session_id": state.current_session_id,
            "resuming_from": start_from,
            "remaining_parts": remaining_parts,
            "already_processed": state.processed_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a saved session"""
    try:
        session_file = Path("sessions") / f"session_{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history", response_model=List[HistorySummary])
async def get_history():
    """Get list of processing history entries"""
    try:
        history_list = state.get_history_list()
        return history_list
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Get detailed results for a specific history entry"""
    try:
        entry = state.load_history_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="History entry not found")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Delete a history entry"""
    try:
        history_file = Path("history") / f"history_{entry_id}.json"
        if history_file.exists():
            history_file.unlink()
            
            # Remove from in-memory history
            state.history = [h for h in state.history if h['id'] != entry_id]
            
            return {"message": "History entry deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="History entry not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/history/{entry_id}/view")
async def view_history_entry(entry_id: str):
    """Load a history entry for viewing (sets current results without processing)"""
    try:
        entry = state.load_history_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="History entry not found")
        
        # Temporarily load the historical results for viewing
        # Don't change processing state, just return the data for UI display
        return {
            "message": "History entry loaded for viewing",
            "entry": entry,
            "results": entry['results'],
            "leaderboard": entry['leaderboard'],
            "summary": entry['summary']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive with a timeout to avoid blocking
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                # Timeout is expected - just continue the loop
                pass
            except Exception:
                # Any other exception means the connection is broken
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# Background processing function
async def process_parts_background(parts_to_process: List[Dict], start_idx: int):
    """Background task for processing parts"""
    try:
        # Create progress callback
        async def progress_callback(message):
            logger.info(f"Broadcasting WebSocket message: {message['type']}")
            await manager.broadcast(message)
            # Small delay to ensure message is sent
            await asyncio.sleep(0.01)
        
        # Use the existing detector but add progress callback
        detector = state.detector
        if not detector:
            raise Exception("No detector found - data may not be loaded")
            
        # Convert to WebAutoPartsDetector if needed
        if not isinstance(detector, WebAutoPartsDetector):
            # Copy the existing detector's data to a new WebAutoPartsDetector
            new_detector = WebAutoPartsDetector("", progress_callback)
            new_detector.data = detector.data
            new_detector.categorized_data = getattr(detector, 'categorized_data', None)
            if hasattr(detector, 'session'):
                new_detector.session = detector.session
            detector = new_detector
            state.detector = detector
        else:
            # Just update the callback
            detector.progress_callback = progress_callback
        
        # Process parts
        results = await detector.process_parts_batch_async(
            parts_to_process, 
            max_parts=len(parts_to_process),
            start_idx=start_idx
        )
        
        if not state.should_stop:
            # Processing completed successfully
            state.results = results
            state.is_processing = False
            
            # Save final session state
            state.save_session()
            
            # Save to history for future access
            state.save_to_history()
            
            await manager.broadcast({
                'type': 'completed',
                'message': 'Processing completed successfully',
                'total_results': len(results),
                'success_rate': len([r for r in results if r.get('makes') != 'NOT_FOUND']) / len(results) * 100 if results else 0
            })
        else:
            # Processing was stopped by user
            state.results = results  # Keep partial results
            state.is_processing = False
            logger.info(f"Processing stopped by user after {len(results)} parts")
        
    except Exception as e:
        logger.error(f"Error in background processing: {e}")
        state.error_message = str(e)
        state.is_processing = False
        
        await manager.broadcast({
            'type': 'error',
            'message': f'Processing failed: {str(e)}'
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)