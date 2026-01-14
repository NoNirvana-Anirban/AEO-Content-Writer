from typing import List, Optional
from serpapi import search
from config import Config

class SERPResearchAgent:
    """Agent responsible for getting top-ranking URLs for a target keyword"""
    
    def __init__(self):
        self.config = Config()
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set the progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, message):
        """Update progress if callback is set"""
        if self.progress_callback:
            self.progress_callback(message)
    
    def run(self, keyword: str, location: Optional[str] = None) -> List[str]:
        """Main method to run SERP research and return list of URLs
        
        Args:
            keyword: The search keyword
            location: Optional location (canonical name from SerpApi Locations API).
                     If not provided, defaults to United States.
        """
        try:
            # Default to United States if no location is provided
            if location:
                location_info = f" in {location}"
            else:
                location_info = " in United States (default)"
                location = None  # Explicitly set to None to use default
            
            self._update_progress(f"Searching for keyword: {keyword}{location_info}")
            
            search_params = {
                "q": keyword,
                "api_key": self.config.SERPAPI_KEY,
                "num": self.config.SERP_RESULTS_COUNT,
                "gl": "us",  # Default to United States country code
                "hl": "en"   # Default language
            }
            
            # Add location parameter if provided (SerpApi accepts location parameter)
            # If not provided, gl="us" ensures United States is used as default
            if location:
                search_params["location"] = location
            
            self._update_progress("Querying SerpAPI for search results...")
            results = search(search_params)
            
            organic_results = results.get("organic_results", [])
            self._update_progress(f"Found {len(organic_results)} organic search results")
            
            # Extract top 5 URLs from results
            urls = []
            for result in organic_results[:5]:  # Top 5 results per keyword
                link = result.get("link", "")
                if link:
                    urls.append(link)
            
            print(f"[SUCCESS] SERP research completed. Found {len(urls)} URLs for keyword: {keyword}")
            
            # Log sample output
            print("\n" + "="*80)
            print("[SAMPLE OUTPUT - SERPResearchAgent]")
            print("="*80)
            print(f"Return type: List[str]")
            print(f"Total URLs: {len(urls)}")
            if urls:
                print(f"Sample URLs (first 3):")
                for i, url in enumerate(urls[:3], 1):
                    print(f"  {i}. {url}")
            print("="*80 + "\n")
            
            return urls
            
        except Exception as e:
            print(f"Error searching keyword: {e}")
            return []
