import httpx
from typing import Optional, Dict, Any, List
from config.settings import get_settings
from utils.logger import logger

settings = get_settings()

class MercadoLibreAPI:
    """Mercado Libre API Client"""
    
    def __init__(self):
        self.base_url = "https://api.mercadolibre.com"
        self.access_token = settings.ML_ACCESS_TOKEN
        self.user_id = settings.ML_USER_ID
        self.country = settings.ML_COUNTRY
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def refresh_token(self) -> bool:
        """Refresh access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": settings.ML_APP_ID,
                        "client_secret": settings.ML_SECRET_KEY,
                        "refresh_token": settings.ML_REFRESH_TOKEN
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    logger.info("ML access token refreshed")
                    return True
                else:
                    logger.error(f"Failed to refresh token: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False
    
    async def search_items(self, query: str, limit: int = 20) -> List[Dict]:
    """Search items in ML - Public search without authentication"""
    try:
        headers = {
            "User-Agent": "ML-Automation/1.0",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/sites/{self.country}/search",
                params={"q": query, "limit": limit},
                headers=headers,
                timeout=10.0
            )
                
                if response.status_code == 200:
                    return response.json().get("results", [])
                else:
                    logger.error(f"Search failed: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching items: {str(e)}")
            return []
    
    async def get_item(self, item_id: str) -> Optional[Dict]:
        """Get item details"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/items/{item_id}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get item failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting item: {str(e)}")
            return None
    
    async def create_item(self, item_data: Dict) -> Optional[Dict]:
        """Create new item"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/items",
                    headers=self._get_headers(),
                    json=item_data
                )
                
                if response.status_code == 201:
                    logger.info(f"Item created: {response.json()['id']}")
                    return response.json()
                else:
                    logger.error(f"Create item failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating item: {str(e)}")
            return None
    
    async def update_item(self, item_id: str, updates: Dict) -> bool:
        """Update item"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/items/{item_id}",
                    headers=self._get_headers(),
                    json=updates
                )
                
                if response.status_code == 200:
                    logger.info(f"Item updated: {item_id}")
                    return True
                else:
                    logger.error(f"Update item failed: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating item: {str(e)}")
            return False
    
    async def get_category_attributes(self, category_id: str) -> List[Dict]:
        """Get required attributes for category"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/categories/{category_id}/attributes"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get attributes failed: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting attributes: {str(e)}")
            return []
    
    async def get_listing_fees(self, category_id: str, price: float, 
                               listing_type: str = "gold_special") -> Optional[Dict]:
        """Calculate listing fees"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/sites/{self.country}/listing_prices",
                    params={
                        "category_id": category_id,
                        "price": price,
                        "listing_type_id": listing_type
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Get fees failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting fees: {str(e)}")
            return None

# Global instance
ml_api = MercadoLibreAPI()
