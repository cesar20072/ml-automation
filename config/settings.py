from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Mercado Libre
    ML_APP_ID: str = ""
    ML_SECRET_KEY: str = ""
    ML_ACCESS_TOKEN: str = ""
    ML_REFRESH_TOKEN: str = ""
    ML_USER_ID: str = ""
    ML_COUNTRY: str = "MLM"
    
    # Shopify
    SHOPIFY_SHOP_URL: str = ""
    SHOPIFY_ACCESS_TOKEN: str = ""
    SHOPIFY_API_VERSION: str = "2024-01"
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_SHEETS_SPREADSHEET_ID: str = ""
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./ml_automation.db"
    
    # Business Rules
    MIN_MARGIN_PERCENTAGE: float = 30.0
    AUTO_PUBLISH_SCORE_THRESHOLD: int = 80
    TEST_AB_DURATION_DAYS: int = 7
    PAUSE_NO_SALES_DAYS: int = 14
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()
