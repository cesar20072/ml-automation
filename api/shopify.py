import httpx
from typing import Optional, Dict, List
from config.settings import get_settings
from utils.logger import logger

settings = get_settings()

class ShopifyAPI:
    """Shopify API Client"""
    
    def __init__(self):
        self.shop_url = settings.SHOPIFY_SHOP_URL
        self.access_token = settings.SHOPIFY_ACCESS_TOKEN
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{self.shop_url}/admin/api/{self.api_version}"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    async def get_products(self, limit: int = 50) -> List[Dict]:
        """Get products from Shopify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/products.json",
                    headers=self._get_headers(),
                    params={"limit": limit}
                )
                
                if response.status_code == 200:
                    return response.json().get("products", [])
                else:
                    logger.error(f"Get products failed: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            return []
    
    async def get_product(self, product_id: str) -> Optional[Dict]:
        """Get single product"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/products/{product_id}.json",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json().get("product")
                else:
                    logger.error(f"Get product failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting product: {str(e)}")
            return None
    
    async def update_inventory(self, inventory_item_id: str, 
                              location_id: str, available: int) -> bool:
        """Update inventory quantity"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/inventory_levels/set.json",
                    headers=self._get_headers(),
                    json={
                        "location_id": location_id,
                        "inventory_item_id": inventory_item_id,
                        "available": available
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Inventory updated: {inventory_item_id} = {available}")
                    return True
                else:
                    logger.error(f"Update inventory failed: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating inventory: {str(e)}")
            return False
    
    async def get_inventory_levels(self, inventory_item_ids: List[str]) -> List[Dict]:
        """Get inventory levels"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/inventory_levels.json",
                    headers=self._get_headers(),
                    params={"inventory_item_ids": ",".join(inventory_item_ids)}
                )
                
                if response.status_code == 200:
                    return response.json().get("inventory_levels", [])
                else:
                    logger.error(f"Get inventory failed: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting inventory: {str(e)}")
            return []

# Global instance
shopify_api = ShopifyAPI()
