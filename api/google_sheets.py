import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict, Optional
import json
import os
from config.settings import get_settings
from utils.logger import logger

settings = get_settings()

class GoogleSheetsAPI:
    """Google Sheets API Client"""
    
    def __init__(self):
        self.spreadsheet_id = settings.GOOGLE_SHEETS_SPREADSHEET_ID
        self.client = None
        self.spreadsheet = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try from environment variable first (Railway)
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            else:
                # Fallback to file
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    settings.GOOGLE_SHEETS_CREDENTIALS_FILE, scope
                )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info("Google Sheets authenticated successfully")
            
        except Exception as e:
            logger.error(f"Failed to authenticate Google Sheets: {str(e)}")
    
    def get_worksheet(self, name: str):
        """Get or create worksheet"""
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Creating worksheet: {name}")
            return self.spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
    
    def read_products(self) -> List[Dict]:
        """Read products from 'productos' sheet"""
        try:
            worksheet = self.get_worksheet("productos")
            records = worksheet.get_all_records()
            logger.info(f"Read {len(records)} products from Google Sheets")
            return records
        except Exception as e:
            logger.error(f"Error reading products: {str(e)}")
            return []
    
    def write_product_status(self, products: List[Dict]):
        """Write product status to 'estado_productos' sheet"""
        try:
            worksheet = self.get_worksheet("estado_productos")
            
            # Clear existing data
            worksheet.clear()
            
            # Headers
            headers = ["sku", "name", "status", "score", "ml_item_id", "price", "margin", "updated_at"]
            worksheet.append_row(headers)
            
            # Data
            for product in products:
                row = [
                    product.get("sku", ""),
                    product.get("name", ""),
                    product.get("status", ""),
                    product.get("score", 0),
                    product.get("ml_item_id", ""),
                    product.get("price", 0),
                    product.get("margin", 0),
                    product.get("updated_at", "")
                ]
                worksheet.append_row(row)
            
            logger.info(f"Wrote {len(products)} product statuses to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error writing product status: {str(e)}")
    
    def write_actions(self, actions: List[Dict]):
        """Write actions to 'acciones' sheet"""
        try:
            worksheet = self.get_worksheet("acciones")
            
            # Headers (if empty)
            if worksheet.row_count == 0:
                headers = ["date", "product_sku", "action_type", "reason", "success"]
                worksheet.append_row(headers)
            
            # Data
            for action in actions:
                row = [
                    action.get("created_at", ""),
                    action.get("product_sku", ""),
                    action.get("action_type", ""),
                    action.get("reason", ""),
                    str(action.get("success", True))
                ]
                worksheet.append_row(row)
            
            logger.info(f"Wrote {len(actions)} actions to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error writing actions: {str(e)}")
    
    def sync_all(self, products: List[Dict], actions: List[Dict]):
        """Sync all data to Google Sheets"""
        try:
            self.write_product_status(products)
            self.write_actions(actions[-100:])  # Last 100 actions
            logger.info("Google Sheets sync completed")
        except Exception as e:
            logger.error(f"Error syncing to Google Sheets: {str(e)}")

# Global instance
try:
    sheets_api = GoogleSheetsAPI()
except Exception as e:
    logger.warning(f"Google Sheets not initialized: {str(e)}")
    sheets_api = None
