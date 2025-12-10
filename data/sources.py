"""Data source abstraction."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class DataSource(ABC):
    """Abstract base class for data sources."""
    
    @abstractmethod
    def get_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors."""
        pass
    
    @abstractmethod
    def get_branches(self) -> List[Dict[str, Any]]:
        """Get all branches."""
        pass
    
    @abstractmethod
    def get_services(self) -> List[Dict[str, Any]]:
        """Get all services."""
        pass
    
    @abstractmethod
    def get_doctor_availability(self, date: str, doctor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get doctor availability for a date."""
        pass


class GoogleSheetsSource(DataSource):
    """Google Sheets data source implementation."""
    
    def __init__(self, spreadsheet_id: str, credentials_path: str = None, sheet_names: Dict[str, str] = None):
        """
        Initialize Google Sheets source.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            credentials_path: Path to service account JSON file (optional, can use default credentials)
            sheet_names: Dictionary mapping data types to sheet names
        """
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ImportError("gspread and google-auth are required. Install with: pip install gspread google-auth")
        
        self.spreadsheet_id = spreadsheet_id
        self.sheet_names = sheet_names or {
            "doctors": "01_doctors",
            "branches": "02_branches",
            "services": "03_services",
            "availability": "04_doctor_availability"
        }
        
        # Authenticate
        import os
        import json
        from pathlib import Path
        
        # First, try to get credentials from environment variable (for Render)
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        if credentials_json:
            try:
                # Parse JSON string from environment variable
                if isinstance(credentials_json, str):
                    creds_dict = json.loads(credentials_json)
                else:
                    creds_dict = credentials_json
                
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
                self.client = gspread.authorize(creds)
            except Exception as e:
                raise ValueError(f"Failed to authenticate with Google Sheets from JSON. Error: {e}")
        elif credentials_path and Path(credentials_path).exists():
            # Use service account file
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
            self.client = gspread.authorize(creds)
        else:
            # Try using gspread's default authentication (service_account() method)
            # This looks for credentials in default locations or uses environment variables
            try:
                self.client = gspread.service_account()
            except Exception as e:
                raise ValueError(f"Failed to authenticate with Google Sheets. Please provide credentials_path or set up default credentials. Error: {e}")
        
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
    
    def _get_sheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Get data from a specific sheet."""
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            # Get all values
            values = sheet.get_all_values()
            
            if not values:
                return []
            
            # First row is headers
            headers = values[0]
            
            # Convert to list of dictionaries
            data = []
            for row in values[1:]:
                if any(cell.strip() for cell in row):  # Skip empty rows
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = row[i] if i < len(row) else ""
                    data.append(row_dict)
            
            return data
        except Exception as e:
            import logging
            logging.error(f"Error reading sheet {sheet_name}: {e}")
            return []
    
    def get_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors from Google Sheets."""
        return self._get_sheet_data(self.sheet_names["doctors"])
    
    def get_branches(self) -> List[Dict[str, Any]]:
        """Get all branches from Google Sheets."""
        return self._get_sheet_data(self.sheet_names["branches"])
    
    def get_services(self) -> List[Dict[str, Any]]:
        """Get all services from Google Sheets."""
        return self._get_sheet_data(self.sheet_names["services"])
    
    def get_doctor_availability(self, date: str, doctor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get doctor availability from Google Sheets."""
        # If date is empty, return all availability data
        if not date:
            return self._get_sheet_data(self.sheet_names["availability"])
        
        data = self._get_sheet_data(self.sheet_names["availability"])
        
        # Filter by date
        results = [record for record in data if record.get('date', '') == date]
        
        # Filter by doctor_id if provided
        if doctor_id:
            results = [r for r in results if r.get('doctor_id', '') == doctor_id]
        
        return results

