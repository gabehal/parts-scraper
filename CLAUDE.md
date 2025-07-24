# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python automotive parts scraper that processes CSV files containing automotive parts data and enriches them with vehicle make compatibility information by querying auto parts websites (RockAuto, Advance Auto Parts).

## Setup and Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

The project uses a virtual environment located in `venv/`. Activate it with:
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

## Virtual Environment and Python Setup

- Always use a virtual environment for project isolation
- Use `python3` to ensure correct Python version
- Source the virtual environment before working
- Use `pip3` for package management
- Recommended workflow:
  * Create virtual env: `python3 -m venv venv`
  * Activate: `source venv/bin/activate`
  * Install packages: `pip3 install -r requirements.txt`

## Running the Application

Execute the main scraper:
```bash
python rockauto_scraper.py
```

The script will:
1. Load the input CSV file (`advLOT_DC52-MIX.csv`)
2. Categorize parts into automotive, tools, and unknown based on keywords
3. Prompt to process all automotive parts or just 10 for testing
4. Query external websites to find vehicle make compatibility
5. Export enriched results to a new CSV file

## Architecture

**Main Components:**
- `AutoPartsDetector` class: Core functionality for loading, categorizing, and processing parts
- Web scraping: Uses BeautifulSoup and requests with proper headers and rate limiting
- Data processing: Pandas for CSV handling and data manipulation

**Key Methods:**
- `load_data()`: Loads CSV input file
- `categorize_parts()`: Separates automotive vs tools vs unknown items using keyword matching
- `extract_part_number()`: Extracts part number after first underscore in item number
- `search_rockauto()` / `search_advance_auto()`: Web scraping methods for parts lookup
- `process_parts_batch()`: Batch processes parts with rate limiting and progress tracking
- `export_results()`: Exports enriched data to CSV

**Input Data Format:**
The CSV must contain columns: `Item #`, `Item Description`, `Qty`, `Unit Retail`, `Ext. Retail`

**Output Format:**
Enriched CSV with additional columns: `Part Number`, `Category`, `Makes`, `Source`

## Rate Limiting and Web Scraping

The scraper implements proper rate limiting (1-1.5 second delays) and uses realistic browser headers to avoid being blocked. It tries RockAuto first, then falls back to Advance Auto Parts if no results are found.

## Git and Version Control

- Use GitHub CLI (`gh`) for git work
- Autonomously create git version control for the project
- Create and manage issues directly through the GitHub CLI
- Commit changes independently when necessary

## Frontend Development Considerations

- Potential frontend implementation considerations:
  * Use React for building the user interface
  * Create a separate API for backend processing
  * Implement batch processing (e.g., first 50 items)
  * Add functionality to:
    - Import CSV file
    - Stop/pause processing
    - Run tests
    - Run for a specific range of items
  * Display results in a scrollable table
  * Save partial results during processing