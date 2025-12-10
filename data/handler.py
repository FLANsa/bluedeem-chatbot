"""Data handler for Google Sheets with validation, normalization, and caching."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from cachetools import TTLCache
from utils.date_parser import get_today_riyadh
from data.sources import GoogleSheetsSource


# Cache with TTL
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
cache = TTLCache(maxsize=100, ttl=CACHE_TTL)


# Expected CSV schemas
DOCTORS_SCHEMA = [
    'doctor_id', 'doctor_name', 'specialty', 'branch_id', 'days',
    'time_from', 'time_to', 'phone', 'email', 'experience_years',
    'qualifications', 'notes'
]

BRANCHES_SCHEMA = [
    'branch_id', 'branch_name', 'address', 'city', 'phone', 'email',
    'hours_weekdays', 'hours_weekend', 'maps_url', 'features',
    'parking', 'accessibility'
]

SERVICES_SCHEMA = [
    'service_id', 'service_name', 'specialty', 'description', 'price_sar',
    'price_range', 'available_branch_ids', 'duration_minutes',
    'preparation_required', 'popular'
]

AVAILABILITY_SCHEMA = [
    'date', 'doctor_id', 'branch_id', 'available', 'note', 'last_updated'
]


def normalize_bool(value: str) -> bool:
    """Normalize boolean values."""
    if not value:
        return False
    value_lower = value.lower().strip()
    return value_lower in ['نعم', 'yes', 'true', '1', 'y', 'ن']


def normalize_list(value: str) -> List[str]:
    """Normalize comma-separated list."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def validate_schema(rows: List[Dict], expected_schema: List[str], file_name: str) -> bool:
    """Validate CSV schema."""
    if not rows:
        return True
    
    actual_columns = set(rows[0].keys())
    expected_columns = set(expected_schema)
    
    missing = expected_columns - actual_columns
    if missing:
        raise ValueError(f"Missing columns in {file_name}: {missing}")
    
    return True


def normalize_doctors_data(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Normalize doctors data."""
    normalized = []
    for row in rows:
        normalized_row = {
            'doctor_id': row.get('doctor_id', '').strip(),
            'doctor_name': row.get('doctor_name', '').strip(),
            'specialty': row.get('specialty', '').strip(),
            'branch_id': row.get('branch_id', '').strip(),
            'days': row.get('days', '').strip(),
            'time_from': row.get('time_from', '').strip(),
            'time_to': row.get('time_to', '').strip(),
            'phone': row.get('phone', '').strip(),
            'email': row.get('email', '').strip(),
            'experience_years': row.get('experience_years', '').strip(),
            'qualifications': row.get('qualifications', '').strip(),
            'notes': row.get('notes', '').strip()
        }
        normalized.append(normalized_row)
    return normalized


def normalize_branches_data(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Normalize branches data."""
    normalized = []
    for row in rows:
        features = normalize_list(row.get('features', ''))
        normalized_row = {
            'branch_id': row.get('branch_id', '').strip(),
            'branch_name': row.get('branch_name', '').strip(),
            'address': row.get('address', '').strip(),
            'city': row.get('city', '').strip(),
            'phone': row.get('phone', '').strip(),
            'email': row.get('email', '').strip(),
            'hours_weekdays': row.get('hours_weekdays', '').strip(),
            'hours_weekend': row.get('hours_weekend', '').strip(),
            'maps_url': row.get('maps_url', '').strip(),
            'features': features,
            'parking': normalize_bool(row.get('parking', '')),
            'accessibility': normalize_bool(row.get('accessibility', ''))
        }
        normalized.append(normalized_row)
    return normalized


def normalize_services_data(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Normalize services data."""
    normalized = []
    for row in rows:
        available_branch_ids = normalize_list(row.get('available_branch_ids', ''))
        normalized_row = {
            'service_id': row.get('service_id', '').strip(),
            'service_name': row.get('service_name', '').strip(),
            'specialty': row.get('specialty', '').strip(),
            'description': row.get('description', '').strip(),
            'price_sar': row.get('price_sar', '').strip(),
            'price_range': row.get('price_range', '').strip(),
            'available_branch_ids': available_branch_ids,
            'duration_minutes': row.get('duration_minutes', '').strip(),
            'preparation_required': normalize_bool(row.get('preparation_required', '')),
            'popular': normalize_bool(row.get('popular', ''))
        }
        normalized.append(normalized_row)
    return normalized


def normalize_availability_data(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Normalize availability data."""
    normalized = []
    for row in rows:
        normalized_row = {
            'date': row.get('date', '').strip(),
            'doctor_id': row.get('doctor_id', '').strip(),
            'branch_id': row.get('branch_id', '').strip(),
            'available': normalize_bool(row.get('available', '')),
            'note': row.get('note', '').strip(),
            'last_updated': row.get('last_updated', '').strip()
        }
        normalized.append(normalized_row)
    return normalized


class DataHandler:
    """Data handler for Google Sheets with caching."""
    
    def __init__(self):
        """Initialize data handler."""
        self._doctors = None
        self._branches = None
        self._services = None
        self._availability = None
        
        # Initialize Google Sheets source if enabled
        self.google_sheets_source = None
        google_sheets_enabled = os.getenv('GOOGLE_SHEETS_ENABLED', 'false').lower() == 'true'
        google_sheets_id = os.getenv('GOOGLE_SHEETS_ID', '')
        
        if google_sheets_enabled and google_sheets_id:
            try:
                credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'google-credentials.json')
                if credentials_path and not credentials_path.startswith('/'):
                    # Relative path - make it absolute
                    from pathlib import Path
                    credentials_path = str(Path(__file__).parent.parent / credentials_path)
                
                self.google_sheets_source = GoogleSheetsSource(
                    spreadsheet_id=config.GOOGLE_SHEETS_ID,
                    credentials_path=credentials_path if credentials_path else None,
                    sheet_names=config.GOOGLE_SHEETS_SHEET_NAMES
                )
                import logging
                logging.info("Google Sheets source initialized")
            except Exception as e:
                import traceback
                import logging
                logging.error(f"Failed to initialize Google Sheets: {e}")
                logging.debug(f"Details: {traceback.format_exc()}")
                logging.warning("Google Sheets initialization failed. System will not function without Google Sheets.")
                self.google_sheets_source = None
    
    def _load_doctors(self) -> List[Dict[str, Any]]:
        """Load doctors from Google Sheets only."""
        cache_key = 'doctors'
        if cache_key in cache:
            return cache[cache_key]
        
        # Only use Google Sheets if enabled
        if not self.google_sheets_source:
            raise ValueError("Google Sheets is not enabled. Please set GOOGLE_SHEETS_ENABLED=true in .env")
        
        try:
            rows = self.google_sheets_source.get_doctors()
            if not rows:
                raise ValueError("No doctors data found in Google Sheets. Please check Sheet '01_doctors'")
            
            validate_schema(rows, DOCTORS_SCHEMA, 'doctors')
            normalized = normalize_doctors_data(rows)
            cache[cache_key] = normalized
            return normalized
        except Exception as e:
            raise ValueError(f"Failed to load doctors from Google Sheets: {e}")
    
    def _load_branches(self) -> List[Dict[str, Any]]:
        """Load branches from Google Sheets only."""
        cache_key = 'branches'
        if cache_key in cache:
            return cache[cache_key]
        
        # Only use Google Sheets if enabled
        if not self.google_sheets_source:
            raise ValueError("Google Sheets is not enabled. Please set GOOGLE_SHEETS_ENABLED=true in .env")
        
        try:
            rows = self.google_sheets_source.get_branches()
            if not rows:
                raise ValueError("No branches data found in Google Sheets. Please check Sheet '02_branches'")
            
            validate_schema(rows, BRANCHES_SCHEMA, 'branches')
            normalized = normalize_branches_data(rows)
            cache[cache_key] = normalized
            return normalized
        except Exception as e:
            raise ValueError(f"Failed to load branches from Google Sheets: {e}")
    
    def _load_services(self) -> List[Dict[str, Any]]:
        """Load services from Google Sheets only."""
        cache_key = 'services'
        if cache_key in cache:
            return cache[cache_key]
        
        # Only use Google Sheets if enabled
        if not self.google_sheets_source:
            raise ValueError("Google Sheets is not enabled. Please set GOOGLE_SHEETS_ENABLED=true in .env")
        
        try:
            rows = self.google_sheets_source.get_services()
            if not rows:
                raise ValueError("No services data found in Google Sheets. Please check Sheet '03_services'")
            
            validate_schema(rows, SERVICES_SCHEMA, 'services')
            normalized = normalize_services_data(rows)
            cache[cache_key] = normalized
            return normalized
        except Exception as e:
            raise ValueError(f"Failed to load services from Google Sheets: {e}")
    
    def _load_availability(self) -> List[Dict[str, Any]]:
        """Load availability from Google Sheets only."""
        cache_key = 'availability'
        if cache_key in cache:
            return cache[cache_key]
        
        # Only use Google Sheets if enabled
        if not self.google_sheets_source:
            raise ValueError("Google Sheets is not enabled. Please set GOOGLE_SHEETS_ENABLED=true in .env")
        
        try:
            # Get all availability data (we'll filter by date later)
            rows = self.google_sheets_source.get_doctor_availability("")
            # Empty list is OK for availability (no records means no specific availability)
            validate_schema(rows, AVAILABILITY_SCHEMA, 'availability')
            normalized = normalize_availability_data(rows)
            cache[cache_key] = normalized
            return normalized
        except Exception as e:
            raise ValueError(f"Failed to load availability from Google Sheets: {e}")
    
    def get_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors."""
        if self._doctors is None:
            self._doctors = self._load_doctors()
        return self._doctors
    
    def get_branches(self) -> List[Dict[str, Any]]:
        """Get all branches."""
        if self._branches is None:
            self._branches = self._load_branches()
        return self._branches
    
    def get_services(self) -> List[Dict[str, Any]]:
        """Get all services."""
        if self._services is None:
            self._services = self._load_services()
        return self._services
    
    def get_doctor_availability(self, date_str: str, doctor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get doctor availability for a specific date.
        
        Args:
            date_str: Date string (YYYY-MM-DD) or relative date
            doctor_id: Optional doctor ID to filter
            
        Returns:
            List of availability records
        """
        # Parse date if relative
        from utils.date_parser import parse_relative_date
        parsed_date = parse_relative_date(date_str)
        if parsed_date:
            date_str = parsed_date.strftime('%Y-%m-%d')
        
        # Only use Google Sheets
        if not self.google_sheets_source:
            raise ValueError("Google Sheets is not enabled. Please set GOOGLE_SHEETS_ENABLED=true in .env")
        
        try:
            results = self.google_sheets_source.get_doctor_availability(date_str, doctor_id)
            return results
        except Exception as e:
            # If no specific availability found, return empty list (not an error)
            if "not found" in str(e).lower() or "no data" in str(e).lower():
                return []
            raise ValueError(f"Failed to get availability from Google Sheets: {e}")
    
    def get_doctor_availability_today(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get doctor availability for today (timezone-aware: Asia/Riyadh).
        
        Args:
            doctor_id: Doctor ID
            
        Returns:
            Availability record or None if not found
        """
        today = get_today_riyadh()
        date_str = today.strftime('%Y-%m-%d')
        
        availability = self.get_doctor_availability(date_str, doctor_id)
        if availability:
            return availability[0]
        return None
    
    def find_doctor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find doctor by name (fuzzy matching)."""
        from rapidfuzz import process
        
        doctors = self.get_doctors()
        if not doctors:
            return None
        
        doctor_names = {d['doctor_name']: d for d in doctors}
        result = process.extractOne(name, doctor_names.keys(), score_cutoff=70)
        
        if result:
            return doctor_names[result[0]]
        return None
    
    def find_service_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find service by name (fuzzy matching)."""
        from rapidfuzz import process
        
        services = self.get_services()
        if not services:
            return None
        
        service_names = {s['service_name']: s for s in services}
        result = process.extractOne(name, service_names.keys(), score_cutoff=70)
        
        if result:
            return service_names[result[0]]
        return None
    
    def get_branch_by_id(self, branch_id: str) -> Optional[Dict[str, Any]]:
        """Get branch by ID."""
        branches = self.get_branches()
        for branch in branches:
            if branch['branch_id'] == branch_id:
                return branch
        return None


# Global instance
data_handler = DataHandler()

