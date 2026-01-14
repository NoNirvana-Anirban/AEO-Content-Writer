import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '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')
    SERPAPI_KEY = os.getenv('SERPAPI_KEY')
    WORDPRESS_DOMAIN = os.getenv('WORDPRESS_DOMAIN')
    WORDPRESS_USER = os.getenv('WORDPRESS_USER')
    WORDPRESS_PASSWORD = os.getenv('WORDPRESS_PASSWORD')
    
    # OpenAI Configuration
    OPENAI_MODEL = "gpt-5"
    OPENAI_TEMPERATURE = 0.7
    
    # OpenRouter Configuration
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # SERP Configuration
    SERP_RESULTS_COUNT = 10
    
    # Flask Configuration
    FLASK_HOST = "127.0.0.1"
    FLASK_PORT = 3000
    FLASK_DEBUG = False  # Disabled to prevent auto-reload issues
    
    # Site Configuration (for SEO/OG tags)
    SITE_URL = os.getenv('SITE_URL', 'https://example.com')
    SITE_NAME = os.getenv('SITE_NAME', 'Content Site')