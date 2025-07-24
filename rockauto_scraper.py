#!/usr/bin/env python3
"""
Automotive Parts Make Detector

This script processes a CSV file of automotive parts, extracts part numbers,
and queries RockAuto.com and other auto parts websites to determine which
vehicle makes each part fits.

Author: Python Data Engineer + Automotive Parts Analyst
"""

import pandas as pd
import requests
import time
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging
from typing import List, Dict, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoPartsDetector:
    def __init__(self, csv_file: str):
        """Initialize the parts detector with a CSV file."""
        self.csv_file = csv_file
        self.df = None
        self.session = requests.Session()
        self.driver = None
        
        # Configure session with proper headers to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
        
        # Keywords for categorizing parts
        self.automotive_keywords = [
            # Engine & Performance - specific automotive terms
            'brake pad', 'brake rotor', 'brake disc', 'brake shoe', 'brake line', 'brake fluid', 'brake booster',
            'oil filter', 'air filter', 'fuel filter', 'cabin filter', 'catalytic converter',
            'spark plug', 'glow plug', 'ignition coil', 'fuel pump', 'water pump', 'oil pump',
            'alternator', 'starter', 'car battery', 'auto battery', 'timing belt', 'timing chain',
            'serpentine belt', 'drive belt', 'radiator hose', 'heater hose', 'vacuum hose',
            'head gasket', 'intake gasket', 'exhaust gasket', 'transmission fluid', 'transmission filter',
            'clutch disc', 'clutch plate', 'pressure plate', 'flywheel', 'radiator', 'thermostat',
            'cylinder head', 'engine block', 'piston ring', 'connecting rod', 'crankshaft',
            'camshaft', 'valve cover', 'intake manifold', 'exhaust manifold', 'turbocharger',
            'supercharger', 'intercooler', 'a/c compressor', 'ac compressor', 'condenser',
            'evaporator', 'expansion valve', 'orifice tube', 'vapor canister', 'charcoal canister',
            
            # Suspension & Steering - specific automotive terms
            'shock absorber', 'strut assembly', 'coil spring', 'leaf spring', 'air spring',
            'tie rod end', 'ball joint', 'control arm', 'sway bar', 'stabilizer bar', 'anti-roll bar',
            'cv joint', 'cv axle', 'drive axle', 'half shaft', 'driveshaft', 'prop shaft',
            'steering rack', 'rack and pinion', 'power steering pump', 'steering column',
            'steering wheel', 'tie rod', 'drag link', 'pitman arm', 'idler arm',
            'engine mount', 'transmission mount', 'motor mount', 'strut mount',
            'suspension bushing', 'control arm bushing', 'sway bar bushing',
            
            # Braking System - already covered above, removing duplicates
            'brake caliper', 'brake cylinder', 'master cylinder', 'wheel cylinder',
            'brake drum', 'brake disc', 'abs module', 'abs sensor', 'abs pump',
            
            # Electrical & Lighting - specific automotive terms
            'headlight', 'headlamp', 'tail light', 'turn signal', 'fog light', 'running light',
            'side mirror', 'rearview mirror', 'windshield wiper', 'wiper blade', 'wiper motor',
            'horn', 'car horn', 'hid ballast', 'xenon ballast', 'led headlight',
            'clock spring', 'blower motor', 'blower resistor', 'hvac blower', 'cabin fan',
            'ignition switch', 'ignition module', 'ecu', 'pcm', 'bcm', 'abs module',
            'wiring harness', 'engine harness', 'transmission harness', 'headlight harness',
            'tpms sensor', 'tire pressure sensor', 'oxygen sensor', 'o2 sensor',
            'map sensor', 'maf sensor', 'throttle position', 'crankshaft sensor', 'camshaft sensor',
            'coolant temp sensor', 'oil pressure sensor', 'fuel level sensor',
            
            # Body & Interior - specific automotive terms
            'car bumper', 'front bumper', 'rear bumper', 'fender', 'quarter panel',
            'car door', 'door handle', 'door lock', 'door latch', 'window regulator',
            'car seat', 'driver seat', 'passenger seat', 'seat belt', 'center console',
            'dashboard', 'instrument panel', 'glove box', 'sun visor',
            'weatherstrip', 'door seal', 'window seal', 'trunk seal', 'hood seal',
            'car antenna', 'radio antenna', 'power antenna',
            
            # Wheels & Tires - specific automotive terms
            'car wheel', 'alloy wheel', 'steel wheel', 'wheel hub', 'hub assembly',
            'lug nut', 'wheel stud', 'hub cap', 'center cap', 'valve stem',
            'wheel bearing', 'hub bearing', 'tire valve', 'tpms valve',
            
            # Exhaust System
            'exhaust pipe', 'muffler', 'catalytic converter', 'exhaust manifold',
            'exhaust gasket', 'exhaust clamp', 'tail pipe', 'resonator',
            
            # HVAC System
            'heater core', 'evaporator core', 'hvac blower', 'a/c evaporator',
            'heater hose', 'hvac control', 'climate control', 'temperature blend door',
            
            # Truck/Heavy Duty Components
            'freightliner', 'peterbilt', 'kenworth', 'mack', 'volvo truck', 'international truck',
            'semi truck', 'trailer', 'fifth wheel', 'kingpin', 'glad hand', 'air brake',
            'diesel fuel', 'def fluid', 'urea tank', 'dpf filter', 'scr system'
        ]
        
        self.tool_keywords = [
            # Power Tools  
            'angle grinder', 'circular saw', 'jigsaw', 'rotary hammer', 'demolition hammer',
            'electric drill', 'cordless drill', 'impact driver', 'driver drill', 'hammer drill',
            'reciprocating saw', 'recip saw', 'band saw', 'miter saw', 'table saw',
            'orbital sander', 'belt sander', 'palm sander', 'router tool', 'trim router',
            'chainsaw', 'pole saw', 'leaf blower', 'pressure washer', 'shop vac',
            
            # Hand Tools & Tool Sets
            'hand tool', 'tool kit', 'tool set', 'mechanic tool set', 'wrench set', 
            'socket set', 'ratchet set', 'combination wrench', 'box wrench', 'open wrench',
            'torque wrench', 'breaker bar', 'extension bar', 'universal joint',
            'screwdriver set', 'bit set', 'hex key', 'allen wrench', 'pliers set',
            'needle nose', 'wire strippers', 'cutting pliers', 'locking pliers',
            
            # Workshop Equipment & Storage
            'toolbox', 'tool chest', 'tool cabinet', 'tool cart', 'rolling cart',
            'work bench', 'workbench', 'shop stool', 'creeper', 'mechanics creeper',
            'work light', 'shop light', 'led work light', 'trouble light',
            'air compressor', 'shop compressor', 'portable compressor',
            'bench vise', 'pipe vise', 'anvil', 'shop press',
            
            # Automotive Service Tools (tools, not parts)
            'floor jack', 'bottle jack', 'scissor jack', 'transmission jack',
            'engine hoist', 'cherry picker', 'porta power', 'engine stand',
            'tire changer', 'wheel balancer', 'bead breaker', 'tire iron', 'lug wrench',
            'oil drain pan', 'funnel set', 'magnetic drain plug',
            
            # Diagnostic & Test Equipment
            'multimeter', 'digital multimeter', 'code reader', 'scan tool', 'obd scanner',
            'oscilloscope', 'function generator', 'power supply', 'battery tester',
            'compression tester', 'leak tester', 'timing light', 'stroboscope',
            
            # General Hardware & Fasteners
            'bolt assortment', 'screw assortment', 'nut assortment', 'washer assortment',
            'cotter pin', 'clevis pin', 'hitch pin', 'spring pin', 'roll pin',
            
            # Safety Equipment
            'safety glasses', 'work gloves', 'shop gloves', 'hearing protection',
            'knee pads', 'back support', 'shop apron'
        ]
        
        # Keywords that indicate NON-automotive items (exclusions)
        self.non_automotive_keywords = [
            # Home/Kitchen items
            'kitchen', 'cooking', 'recipe', 'food', 'dining', 'tableware', 'cookware',
            'coffee', 'tea', 'beverage', 'drink', 'bottle opener', 'can opener',
            'cutting board', 'knife set', 'silverware', 'dishwasher', 'microwave',
            
            # Personal items
            'clothing', 'shirt', 'pants', 'jacket', 'shoes', 'boots', 'hat', 'cap',
            'watch', 'jewelry', 'necklace', 'ring', 'wallet', 'purse', 'bag',
            
            # Electronics (non-automotive)
            'phone', 'tablet', 'laptop', 'computer', 'monitor', 'keyboard', 'mouse',
            'headphones', 'speaker', 'bluetooth', 'usb cable', 'charger', 'adapter',
            'camera', 'video', 'tv', 'television', 'remote control',
            
            # Home improvement
            'paint', 'brush', 'roller', 'ladder', 'garden', 'lawn', 'plant', 'seed',
            'fertilizer', 'pesticide', 'sprinkler', 'hose nozzle', 'watering',
            
            # Office supplies
            'paper', 'pen', 'pencil', 'marker', 'notebook', 'binder', 'stapler',
            'calculator', 'desk', 'chair', 'filing cabinet'
        ]
    
    def _initialize_browser(self):
        """Initialize Selenium WebDriver with Chrome."""
        if self.driver is None:
            try:
                # Configure Chrome options
                chrome_options = Options()
                # Keep visible for debugging - can be headless for production
                # chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # Initialize driver
                driver_path = ChromeDriverManager().install()
                
                # Fix webdriver-manager bug where it sometimes points to wrong file
                if driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
                    import os
                    driver_dir = os.path.dirname(driver_path)
                    actual_driver = os.path.join(driver_dir, 'chromedriver')
                    if os.path.exists(actual_driver):
                        driver_path = actual_driver
                        logger.info(f"Fixed driver path from THIRD_PARTY_NOTICES to: {driver_path}")
                    else:
                        logger.error(f"Could not find actual chromedriver in {driver_dir}")
                
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Execute script to hide automation indicators
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                logger.info("Browser initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize browser: {e}")
                raise
    
    def _close_browser(self):
        """Close the browser if it's open."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
    
    def __del__(self):
        """Ensure browser is closed when object is destroyed."""
        self._close_browser()
    
    def load_data(self) -> None:
        """Load and parse the CSV file."""
        try:
            self.df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(self.df)} rows from {self.csv_file}")
            logger.info(f"Columns: {list(self.df.columns)}")
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            raise
    
    def extract_part_number(self, item_num: str) -> str:
        """Extract part number after the first underscore."""
        if pd.isna(item_num) or not isinstance(item_num, str):
            return ""
        
        underscore_index = item_num.find('_')
        if underscore_index != -1:
            return item_num[underscore_index + 1:]
        return item_num
    
    def categorize_parts(self) -> Dict[str, List[Dict]]:
        """Categorize parts into automotive, tools, and unknown."""
        categorized = {
            'automotive': [],
            'tools': [],
            'unknown': []
        }
        
        for index, row in self.df.iterrows():
            item_num = row.get('Item #', '')
            description = str(row.get('Item Description', '')).lower()
            part_number = self.extract_part_number(item_num)
            
            part_data = {
                'index': index,
                'item_num': item_num,
                'part_number': part_number,
                'description': row.get('Item Description', ''),
                'qty': row.get('Qty', 0),
                'unit_retail': row.get('Unit Retail', 0),
                'ext_retail': row.get('Ext. Retail', 0)
            }
            
            # First check for non-automotive exclusions
            is_non_automotive = any(keyword in description for keyword in self.non_automotive_keywords)
            
            # Check if automotive (but exclude if it's clearly non-automotive)
            is_automotive = False
            if not is_non_automotive:
                is_automotive = any(keyword in description for keyword in self.automotive_keywords)
            
            # Only check for tools if it's not automotive and not excluded
            is_tool = False
            if not is_automotive and not is_non_automotive:
                is_tool = any(keyword in description for keyword in self.tool_keywords)
            
            if is_automotive:
                categorized['automotive'].append(part_data)
            elif is_tool:
                categorized['tools'].append(part_data)
            else:
                categorized['unknown'].append(part_data)
        
        logger.info(f"Categorized parts: {len(categorized['automotive'])} automotive, "
                   f"{len(categorized['tools'])} tools, {len(categorized['unknown'])} unknown")
        
        return categorized
    
    def search_rockauto(self, part_number: str, part_description: str = "", full_item_num: str = "") -> Optional[List[str]]:
        """Search RockAuto for a part number using streamlined direct search."""
        try:
            # Check if we should stop processing (import here to avoid circular imports)
            try:
                from backend.main import state
                if hasattr(state, 'should_stop') and state.should_stop:
                    logger.info("Stopping RockAuto search due to user request")
                    return None
            except:
                pass  # If we can't import state, continue normally
                
            # Initialize browser if needed
            if self.driver is None:
                self._initialize_browser()
            
            # Use direct part search URL - most efficient method
            search_url = f"https://www.rockauto.com/en/partsearch/?partnum={part_number}"
            logger.info(f"Direct part search: {search_url}")
            self.driver.get(search_url)
            
            # Wait for page to load (reduced from 3s to 1.5s)
            time.sleep(1.5)
            current_url = self.driver.current_url
            logger.info(f"Result URL: {current_url}")
            
            makes = set()
            
            # Check for immediate buyers guide popup first
            try:
                popup = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.ID, "buyersguidepopup-outer_b"))
                )
                logger.info("Found immediate buyers guide popup")
                makes.update(self._extract_makes_from_popup())
                if makes:
                    logger.info(f"Success: Found makes from immediate popup: {makes}")
                    return sorted([make for make in makes if self._is_valid_make(make)])
            except TimeoutException:
                pass
            
            # If on search results page, look for part links that trigger popups
            if "/partsearch" in current_url:
                logger.info("On search results page - looking for part links")
                
                # Find all part number links that trigger the buyers guide popup
                part_links = self.driver.find_elements(By.CSS_SELECTOR, "span[id^='vew_partnumber']")
                logger.info(f"Found {len(part_links)} part number links")
                
                if part_links:
                    # Get the text of each part link to see what we found
                    for i, link in enumerate(part_links[:5]):  # Check first 5
                        try:
                            part_text = link.text.strip()
                            logger.info(f"Part link {i+1}: {part_text}")
                        except:
                            pass
                    
                    # Try clicking the first few part links to trigger popup
                    for i, link in enumerate(part_links[:3]):  # Try first 3 links
                        try:
                            if link.is_displayed():
                                part_text = link.text.strip()
                                logger.info(f"Clicking part link {i+1}: {part_text}")
                                link.click()
                                time.sleep(1)  # Reduced from 2s to 1s
                                
                                # Check for popup after click
                                try:
                                    WebDriverWait(self.driver, 3).until(
                                        EC.presence_of_element_located((By.ID, "buyersguidepopup-outer_b"))
                                    )
                                    logger.info("Popup appeared after clicking part link")
                                    makes.update(self._extract_makes_from_popup())
                                    if makes:
                                        logger.info(f"Success: Found makes from popup: {makes}")
                                        return sorted([make for make in makes if self._is_valid_make(make)])
                                except TimeoutException:
                                    logger.info(f"No popup appeared for part {part_text}")
                                    continue
                        except Exception as e:
                            logger.warning(f"Error clicking part link {i+1}: {e}")
                            continue
                else:
                    logger.info("No part number links found on search results page")
            
            # If no popup appeared, check if page indicates no results
            page_source = self.driver.page_source.lower()
            if any(phrase in page_source for phrase in ['no results', 'no matches', 'not found', 'no applications found']):
                logger.info(f"RockAuto indicates no results for part {part_number}")
                return None
            
            logger.info(f"No vehicle makes found for part {part_number}")
            return None
                
        except Exception as e:
            logger.error(f"Error searching RockAuto for {part_number}: {e}")
            return None
    
    
    def _extract_makes_from_popup(self) -> set:
        """Extract makes from buyers guide popup."""
        makes = set()
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            popup = soup.find('div', id='buyersguidepopup-outer_b')
            
            if popup:
                popup_text = popup.get_text().strip()
                logger.info(f"Found buyers guide popup with text: '{popup_text}'")
                
                # Check for no applications message
                if "no applications found" in popup_text.lower():
                    logger.info("Popup indicates no applications found for this part")
                    return makes
                
                # Look for table rows
                rows = popup.find_all('tr')
                logger.info(f"Found {len(rows)} table rows in popup")
                
                if len(rows) == 0:
                    # Try looking for other content structures
                    all_text = popup_text.upper()
                    logger.info(f"No table rows, checking full popup text: '{all_text}'")
                    
                    # Extract makes from any text patterns
                    words = all_text.split()
                    for word in words:
                        word_clean = re.sub(r'[^\w]', '', word)
                        if self._is_known_make(word_clean):
                            normalized = self._normalize_make(word_clean)
                            makes.add(normalized)
                            logger.info(f"Found make from popup text: {normalized}")
                
                for i, row in enumerate(rows[:10]):  # Check first 10 rows
                    cells = row.find_all('td')
                    logger.info(f"Row {i+1}: {len(cells)} cells")
                    
                    for j, cell in enumerate(cells[:5]):  # Check first 5 cells
                        text = cell.get_text().strip()
                        logger.info(f"  Cell {j+1}: '{text}'")
                        
                        if text:  # Only process non-empty cells
                            text_upper = text.upper()
                            
                            # Method 1: Look for year-make patterns like "2008 HONDA"
                            year_make_matches = re.findall(r'\b(19|20)\d{2}[-\s]+([A-Z][A-Z]+)', text_upper)
                            for year, make in year_make_matches:
                                if self._is_known_make(make):
                                    normalized = self._normalize_make(make)
                                    makes.add(normalized)
                                    logger.info(f"Found make from year-make pattern: {normalized}")
                            
                            # Method 2: Look for standalone make names
                            words = text_upper.split()
                            for word in words:
                                word_clean = re.sub(r'[^\w]', '', word)  # Remove punctuation
                                if self._is_known_make(word_clean):
                                    normalized = self._normalize_make(word_clean)
                                    makes.add(normalized)
                                    logger.info(f"Found make from standalone word: {normalized}")
                            
                            # Method 3: Look for common patterns like "Fits: FORD HONDA"
                            fits_match = re.search(r'(?:fits?|compatible|for)[:.\s]*([A-Z\s,]+)', text_upper)
                            if fits_match:
                                fits_text = fits_match.group(1)
                                potential_makes = re.findall(r'\b([A-Z]{3,})\b', fits_text)
                                for make in potential_makes:
                                    if self._is_known_make(make):
                                        normalized = self._normalize_make(make)
                                        makes.add(normalized)
                                        logger.info(f"Found make from fits pattern: {normalized}")
                
                logger.info(f"Extracted {len(makes)} unique makes from popup: {makes}")
            else:
                logger.warning("No buyers guide popup found in HTML")
        
        except Exception as e:
            logger.warning(f"Error extracting from popup: {e}")
        
        return makes
    
    
    def _is_known_make(self, make: str) -> bool:
        """Check if make is a known automotive manufacturer."""
        known_makes = {
            'FORD', 'CHEVROLET', 'CHEVY', 'DODGE', 'TOYOTA', 'HONDA', 'NISSAN',
            'BMW', 'MERCEDES', 'AUDI', 'VOLKSWAGEN', 'SUBARU', 'MAZDA',
            'HYUNDAI', 'KIA', 'JEEP', 'CHRYSLER', 'BUICK', 'CADILLAC',
            'ACURA', 'INFINITI', 'LEXUS', 'LINCOLN', 'VOLVO', 'SAAB',
            'MITSUBISHI', 'ISUZU', 'SUZUKI', 'PONTIAC', 'OLDSMOBILE',
            'SATURN', 'MERCURY', 'PLYMOUTH', 'EAGLE', 'GEO'
        }
        return make.upper() in known_makes
    
    def _normalize_make(self, make: str) -> str:
        """Normalize make name to standard format."""
        make_upper = make.upper()
        if make_upper == 'CHEVY':
            return 'Chevrolet'
        return make.title()
    
    def _is_valid_make(self, make: str) -> bool:
        """Check if extracted make is valid (not generic terms)."""
        invalid_terms = {'part', 'parts', 'auto', 'car', 'vehicle', 'search', 'catalog', 'home'}
        return make.lower() not in invalid_terms and len(make) > 1
    
    
    
    def search_google_fallback(self, part_number: str) -> Optional[List[str]]:
        """
        DISABLED: Google search fallback was returning unreliable results.
        Only use RockAuto for confident, accurate results.
        """
        logger.info(f"Google fallback disabled for reliability - no results for {part_number}")
        return None
    
    def _extract_from_part_context(self, part_number: str) -> set:
        """Extract vehicle makes using part number context and pattern matching."""
        makes = set()
        try:
            # Common patterns for specific part prefixes/suffixes that might indicate makes
            part_patterns = {
                'Ford': ['F250', 'F350', 'F450', 'F550', 'FORD', 'FD', 'ECONOLINE'],
                'Chevrolet': ['CHEVY', 'SILVERADO', 'TAHOE', 'SUBURBAN', 'GM', 'CHEV'],  
                'Dodge': ['RAM', 'DAKOTA', 'DURANGO', 'CHALLENGER', 'CHARGER', 'DODGE'],
                'Honda': ['CIVIC', 'ACCORD', 'CRV', 'PILOT', 'RIDGELINE', 'HONDA'],
                'Toyota': ['CAMRY', 'COROLLA', 'RAV4', 'HIGHLANDER', 'PRIUS', 'TOYOTA'],
                'BMW': ['BMW', 'X5', 'X3', '525I', '528I', '535I', '550I'],
                'Mercedes': ['MERCEDES', 'BENZ', 'ML', 'GL', 'SL'],
                'Audi': ['AUDI', 'A4', 'A6', 'Q5', 'Q7'],
                'Nissan': ['NISSAN', 'ALTIMA', 'MAXIMA', 'PATHFINDER', 'TITAN'],
                'Mazda': ['MAZDA', 'CX5', 'CX7', 'CX9', 'MX5', 'MIATA'],
                'Subaru': ['SUBARU', 'OUTBACK', 'FORESTER', 'IMPREZA'],
                'Volkswagen': ['VW', 'VOLKSWAGEN', 'JETTA', 'PASSAT', 'BEETLE'],
                'Lexus': ['LEXUS', 'RX300', 'RX350', 'ES350', 'GS350'],
                'Acura': ['ACURA', 'TL', 'MDX', 'RDX', 'TSX']
            }
            
            part_upper = part_number.upper()
            
            # Check if part number contains make-specific patterns
            for make, patterns in part_patterns.items():
                for pattern in patterns:
                    if pattern in part_upper:
                        makes.add(make)
                        logger.info(f"Found make from part pattern: {make} (pattern: {pattern})")
                        break
            
            # Additional context-based logic for specific part types
            if any(prefix in part_upper for prefix in ['HS', 'HEAD']):
                # Head gasket sets are often Ford truck parts
                if any(indicator in part_upper for indicator in ['54657', '5465']):
                    makes.add('Ford')
                    logger.info("Found Ford from head gasket part pattern")
            
        except Exception as e:
            logger.warning(f"Error in part context extraction: {e}")
        
        return makes
    
    def _simple_google_search_enhanced(self, query: str) -> set:
        """Enhanced Google search with better pattern matching."""
        makes = set()
        try:
            search_url = "https://www.google.com/search"
            params = {'q': query, 'num': 10}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract text from search result titles and snippets
                search_elements = []
                # Look for result titles and descriptions
                search_elements.extend(soup.find_all(['h3', 'span', 'div'], class_=re.compile(r'title|snippet|description', re.I)))
                # Also check direct text content
                search_elements.extend(soup.find_all(text=True))
                
                for element in search_elements:
                    if hasattr(element, 'get_text'):
                        text = element.get_text()
                    else:
                        text = str(element)
                    
                    text = text.upper()
                    
                    # Skip very short or very long strings
                    if len(text) < 10 or len(text) > 200:
                        continue
                    
                    # Look for year-make patterns like "2010 Ford F-550"
                    year_make_patterns = re.findall(r'\b(19|20)\d{2}\s+([A-Z][A-Z]+)', text)
                    for _, make in year_make_patterns:
                        if self._is_known_make(make):
                            normalized = self._normalize_make(make)
                            makes.add(normalized)
                            logger.info(f"Found make from Google search: {normalized}")
                            if len(makes) >= 3:  # Limit results
                                return makes
                    
                    # Look for standalone make names in automotive context
                    words = text.split()
                    for i, word in enumerate(words):
                        word_clean = re.sub(r'[^\w]', '', word)
                        if self._is_known_make(word_clean):
                            # Check automotive context
                            context_words = words[max(0, i-4):i+5]
                            context_text = ' '.join(context_words).upper()
                            
                            if any(auto_word in context_text for auto_word in [
                                'PART', 'AUTO', 'CAR', 'VEHICLE', 'ENGINE', 'BRAKE', 'FILTER',
                                'GASKET', 'HEAD', 'CYLINDER', 'TRANSMISSION', 'SUSPENSION',
                                'OEM', 'AFTERMARKET', 'REPLACEMENT', 'FITS', 'FOR',
                                'SUPER', 'DUTY', 'PICKUP', 'TRUCK', 'SEDAN', 'COUPE'
                            ]):
                                normalized = self._normalize_make(word_clean)
                                makes.add(normalized)
                                logger.info(f"Found make from Google context: {normalized}")
                                if len(makes) >= 3:
                                    return makes
            
        except Exception as e:
            logger.warning(f"Enhanced Google search failed: {e}")
        
        return makes
    
    def _simple_google_search(self, part_number: str) -> set:
        """Simple fallback Google search using requests."""
        makes = set()
        try:
            # Use a simple Google search URL
            query = f'"{part_number}" advanced auto parts'
            search_url = f"https://www.google.com/search"
            params = {'q': query, 'num': 10}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Simple text extraction for vehicle makes
                text = response.text.upper()
                
                # Look for common patterns in the HTML
                year_make_patterns = re.findall(r'\b(19|20)\d{2}\s+([A-Z][A-Z]+)', text)
                for _, make in year_make_patterns[:20]:  # Limit to first 20 matches
                    if self._is_known_make(make):
                        normalized = self._normalize_make(make)
                        makes.add(normalized)
                        if len(makes) >= 3:  # Stop after finding 3 makes
                            break
            
        except Exception as e:
            logger.warning(f"Simple Google search failed: {e}")
        
        return makes
    
    def process_parts_batch(self, parts: List[Dict], max_parts: int = 10, skip_existing: bool = True, 
                           existing_results_file: str = None) -> List[Dict]:
        """Process a batch of parts to find their vehicle makes, optionally skipping those with existing makes."""
        results = []
        successful_lookups = 0
        skipped_count = 0
        
        # Load existing results if specified
        existing_makes = {}
        if skip_existing and existing_results_file:
            existing_makes = self._load_existing_makes(existing_results_file)
            logger.info(f"Loaded {len(existing_makes)} existing make entries from {existing_results_file}")
        
        logger.info(f"Starting batch processing of {min(max_parts, len(parts))} parts...")
        if skip_existing:
            logger.info("Skip mode enabled - will skip parts that already have make information")
        
        for i, part in enumerate(parts[:max_parts]):
            part_number = part['part_number']
            item_num = part.get('item_num', '')
            
            # Check if we should skip this part
            if skip_existing:
                existing_make = self._check_existing_make(part, existing_makes)
                if existing_make and existing_make not in ['NOT_FOUND', 'UNKNOWN_CATEGORY', '']:
                    logger.info(f"⏭️  Skipping part {i+1}/{min(max_parts, len(parts))}: {part_number} "
                               f"(already has make: {existing_make})")
                    
                    # Add to results with existing information
                    part_result = part.copy()
                    part_result['makes'] = existing_make
                    part_result['source'] = 'EXISTING'
                    part_result['confidence'] = 'Existing'
                    results.append(part_result)
                    successful_lookups += 1
                    skipped_count += 1
                    continue
            
            logger.info(f"Processing part {i+1}/{min(max_parts, len(parts))}: {part_number}")
            logger.info(f"Part description: {part['description']}")
            
            # Try RockAuto first - pass both part number and full item number
            makes = self.search_rockauto(part_number, part['description'], item_num)
            source = 'RockAuto'
            
            # Only use RockAuto - no unreliable fallback methods
            if not makes:
                logger.info(f"No reliable results found for {part_number}")
            
            # Record results
            part_result = part.copy()
            if makes:
                # Clean and deduplicate makes
                unique_makes = list(set(makes))
                unique_makes.sort()  # Alphabetical order
                
                part_result['makes'] = ', '.join(unique_makes)
                part_result['source'] = source
                part_result['confidence'] = 'High' if len(unique_makes) <= 3 else 'Medium'
                successful_lookups += 1
                logger.info(f"✅ Found makes for {part_number}: {part_result['makes']}")
            else:
                part_result['makes'] = 'NOT_FOUND'
                part_result['source'] = 'NONE'
                part_result['confidence'] = 'None'
                logger.warning(f"❌ No makes found for {part_number}")
            
            results.append(part_result)
            
            # Progress update every 3 parts
            if (i + 1) % 3 == 0:
                actual_processed = (i + 1) - skipped_count
                if actual_processed > 0:
                    success_rate = ((successful_lookups - skipped_count) / actual_processed) * 100
                else:
                    success_rate = 0
                logger.info(f"Progress: {i + 1}/{min(max_parts, len(parts))} parts completed "
                           f"({skipped_count} skipped, {actual_processed} processed), "
                           f"success rate: {success_rate:.1f}%")
        
        # Final summary
        actual_processed = len(results) - skipped_count
        if actual_processed > 0:
            final_success_rate = ((successful_lookups - skipped_count) / actual_processed) * 100
        else:
            final_success_rate = 0
            
        logger.info(f"Batch processing complete!")
        logger.info(f"  Total parts: {len(results)}")
        logger.info(f"  Skipped (already had makes): {skipped_count}")
        logger.info(f"  Actually processed: {actual_processed}")
        logger.info(f"  New matches found: {successful_lookups - skipped_count}")
        logger.info(f"  Success rate for new parts: {final_success_rate:.1f}%")
        
        # Close browser after processing
        self._close_browser()
        
        return results
    
    def _load_existing_makes(self, filename: str) -> Dict[str, str]:
        """Load existing make information from a CSV file."""
        existing_makes = {}
        try:
            if not os.path.exists(filename):
                logger.info(f"Existing results file {filename} not found, will process all parts")
                return existing_makes
                
            import pandas as pd
            df = pd.read_csv(filename)
            
            # Check if required columns exist
            required_cols = ['Item #', 'Part Number', 'Makes']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"Missing columns in {filename}: {missing_cols}. Will process all parts.")
                return existing_makes
            
            # Build lookup dictionary
            for _, row in df.iterrows():
                item_num = str(row.get('Item #', ''))
                part_num = str(row.get('Part Number', ''))
                makes = str(row.get('Makes', ''))
                
                if item_num and item_num != 'nan':
                    existing_makes[item_num] = makes
                if part_num and part_num != 'nan':
                    existing_makes[part_num] = makes
            
            logger.info(f"Successfully loaded {len(existing_makes)} existing make entries")
            
        except Exception as e:
            logger.warning(f"Error loading existing makes from {filename}: {e}")
            
        return existing_makes
    
    def _check_existing_make(self, part: Dict, existing_makes: Dict[str, str]) -> str:
        """Check if a part already has make information."""
        item_num = part.get('item_num', '')
        part_number = part.get('part_number', '')
        
        # Check by item number first (more specific)
        if item_num and item_num in existing_makes:
            return existing_makes[item_num]
            
        # Check by part number
        if part_number and part_number in existing_makes:
            return existing_makes[part_number]
            
        return ''
    
    def _merge_chunk_results(self, chunk_results: List[Dict], all_categorized: Dict, 
                            start_idx: int, existing_file: str = None) -> List[Dict]:
        """Merge chunk processing results with existing data."""
        try:
            # Start with all automotive parts
            all_automotive = all_categorized['automotive']
            merged_results = []
            
            # Load existing results if available
            existing_data = {}
            if existing_file and os.path.exists(existing_file):
                try:
                    import pandas as pd
                    df = pd.read_csv(existing_file)
                    # Create lookup by item number
                    for _, row in df.iterrows():
                        item_num = str(row.get('Item #', ''))
                        if item_num and item_num != 'nan':
                            existing_data[item_num] = {
                                'makes': str(row.get('Makes', '')),
                                'source': str(row.get('Source', '')),
                                'confidence': str(row.get('Confidence', ''))
                            }
                except Exception as e:
                    logger.warning(f"Could not load existing results for merging: {e}")
            
            # Create results for all parts
            for i, part in enumerate(all_automotive):
                item_num = part.get('item_num', '')
                
                # Check if this part was in our processed chunk
                if start_idx <= i < start_idx + len(chunk_results):
                    # Use the newly processed result
                    chunk_idx = i - start_idx
                    merged_results.append(chunk_results[chunk_idx])
                elif item_num in existing_data:
                    # Use existing data
                    part_result = part.copy()
                    existing = existing_data[item_num]
                    part_result['makes'] = existing['makes']
                    part_result['source'] = existing['source']
                    part_result['confidence'] = existing.get('confidence', 'Existing')
                    merged_results.append(part_result)
                else:
                    # No data available - mark as not processed
                    part_result = part.copy()
                    part_result['makes'] = 'NOT_PROCESSED'
                    part_result['source'] = 'N/A'
                    part_result['confidence'] = 'None'
                    merged_results.append(part_result)
                    
            logger.info(f"Merged chunk results: {len(merged_results)} total parts")
            return merged_results
            
        except Exception as e:
            logger.error(f"Error merging chunk results: {e}")
            # Fallback to just returning the chunk results
            return chunk_results
    
    def export_results(self, automotive_results: List[Dict], 
                      tool_parts: List[Dict], 
                      unknown_parts: List[Dict],
                      output_file: str = 'enriched_parts.csv') -> None:
        """Export results to a new CSV file."""
        
        # Create new dataframe with all results
        all_results = []
        
        # Add automotive parts with makes
        for result in automotive_results:
            row = {
                'Item #': result['item_num'],
                'Item Description': result['description'],
                'Qty': result['qty'],
                'Unit Retail': result['unit_retail'],
                'Ext. Retail': result['ext_retail'],
                'Part Number': result['part_number'],
                'Category': 'Automotive',
                'Makes': result.get('makes', 'NOT_PROCESSED'),
                'Source': result.get('source', 'N/A')
            }
            all_results.append(row)
        
        # Add tool parts
        for part in tool_parts:
            row = {
                'Item #': part['item_num'],
                'Item Description': part['description'],
                'Qty': part['qty'],
                'Unit Retail': part['unit_retail'],
                'Ext. Retail': part['ext_retail'],
                'Part Number': part['part_number'],
                'Category': 'Tools',
                'Makes': 'N/A (Tool)',
                'Source': 'N/A'
            }
            all_results.append(row)
        
        # Add unknown parts
        for part in unknown_parts:
            row = {
                'Item #': part['item_num'],
                'Item Description': part['description'],
                'Qty': part['qty'],
                'Unit Retail': part['unit_retail'],
                'Ext. Retail': part['ext_retail'],
                'Part Number': part['part_number'],
                'Category': 'Unknown',
                'Makes': 'UNKNOWN_CATEGORY',
                'Source': 'N/A'
            }
            all_results.append(row)
        
        # Create DataFrame and export
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(output_file, index=False)
        logger.info(f"Results exported to {output_file}")
        
        # Print summary
        print(f"\n=== PROCESSING SUMMARY ===")
        print(f"Total parts processed: {len(all_results)}")
        print(f"Automotive parts: {len(automotive_results)}")
        print(f"Tool parts: {len(tool_parts)}")
        print(f"Unknown parts: {len(unknown_parts)}")
        
        if automotive_results:
            found_makes = sum(1 for r in automotive_results if r.get('makes', 'NOT_FOUND') != 'NOT_FOUND')
            print(f"Automotive parts with makes found: {found_makes}/{len(automotive_results)}")

def main():
    """Main execution function."""
    print("=== AUTOMOTIVE PARTS MAKE DETECTOR ===")
    
    # Initialize detector
    detector = AutoPartsDetector('advLOT_DC52-MIX.csv')
    
    # Load data
    detector.load_data()
    
    # Categorize parts
    categorized = detector.categorize_parts()
    
    total_parts = len(categorized['automotive'])
    print(f"\nFound {total_parts} automotive parts.")
    
    # Ask user for processing preference with chunk options
    print("\nProcessing Options:")
    print("  1. Process all parts")
    print("  2. Process test batch (100 parts)")
    print("  3. Process custom chunk (specify range)")
    
    choice = input("Enter your choice (1, 2, or 3): ").strip()
    
    start_idx = 0
    max_parts = total_parts
    chunk_suffix = "full"
    
    if choice == '2':
        max_parts = 100
        chunk_suffix = "test"
    elif choice == '3':
        # Handle custom chunk processing
        print(f"\nCustom Chunk Processing (Total parts: {total_parts})")
        print("Examples:")
        print("  - Enter '100-200' to process parts 100 to 200")
        print("  - Enter '500-' or '500-end' to process from 500 to end")  
        print("  - Enter '0-500' to process first 500 parts")
        
        range_input = input("Enter range (e.g., '100-200', '500-end'): ").strip()
        
        try:
            if '-' in range_input:
                parts = range_input.split('-', 1)
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                
                # Parse start index
                start_idx = int(start_str) if start_str else 0
                
                # Parse end index  
                if not end_str or end_str.lower() in ['end', '']:
                    end_idx = total_parts
                else:
                    end_idx = int(end_str)
                
                # Validate range
                if start_idx < 0:
                    start_idx = 0
                if end_idx > total_parts:
                    end_idx = total_parts
                if start_idx >= end_idx:
                    print("❌ Invalid range: start must be less than end")
                    return
                    
                max_parts = end_idx - start_idx
                chunk_suffix = f"chunk_{start_idx}_{end_idx}"
                
                print(f"✅ Will process parts {start_idx} to {end_idx} ({max_parts} parts)")
                
            else:
                print("❌ Invalid range format. Please use format like '100-200' or '500-end'")
                return
                
        except ValueError:
            print("❌ Invalid range format. Please use numbers like '100-200' or '500-end'")
            return
    
    # Select the chunk of parts to process
    parts_to_process = categorized['automotive'][start_idx:start_idx + max_parts]
    output_file = f"enriched_parts_{chunk_suffix}.csv"
    
    print(f"\nProcessing {len(parts_to_process)} automotive parts...")
    if start_idx > 0:
        print(f"Starting from index {start_idx}")
    
    # Ask about skipping existing results
    skip_existing = True
    existing_file = None
    if os.path.exists(output_file):
        skip_choice = input(f"\nFound existing results file: {output_file}\n"
                          f"Skip parts that already have makes? (Y/n): ").strip().lower()
        if skip_choice in ['', 'y', 'yes']:
            skip_existing = True
            existing_file = output_file
            print("✅ Will skip parts that already have make information")
        else:
            skip_existing = False
            print("Will process all parts (may overwrite existing results)")
    
    if skip_existing and existing_file:
        print("Checking for existing results to skip...")
    print("This may take several minutes due to rate limiting...")
    
    # Process automotive parts with skip functionality
    automotive_results = detector.process_parts_batch(
        parts_to_process, 
        max_parts=len(parts_to_process),
        skip_existing=skip_existing,
        existing_results_file=existing_file
    )
    
    # For chunk processing, we need to include all parts in export but only update the processed ones
    if choice == '3' and start_idx > 0:
        # Load existing data to merge with new results
        all_results = detector._merge_chunk_results(automotive_results, categorized, start_idx, existing_file)
        detector.export_results(all_results, categorized['tools'], 
                               categorized['unknown'], output_file)
    else:
        # Normal export for full or test processing
        detector.export_results(automotive_results, categorized['tools'], 
                               categorized['unknown'], output_file)
    
    print(f"\n✅ Processing complete! Results saved to {output_file}")

if __name__ == "__main__":
    main()