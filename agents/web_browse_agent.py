import json
from typing import List
from config import Config
import openai

class WebBrowseAgent:
    """SERP Research Agent using OpenAI Web Search tool (Responses API)"""
    
    def __init__(self, model: str = "gpt-4o-mini-search-preview"):  # Search-enabled model
        self.config = Config()
        self.model = model
        self.client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
        self.progress_callback = None
        
        if not self.config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
    
    def set_progress_callback(self, callback):
        self.progress_callback = callback
    
    def _update_progress(self, message):
        if self.progress_callback:
            self.progress_callback(message)
    
    def run(self, keyword: str) -> List[str]:
        """Main method to run web browsing research and return list of URLs"""
        try:
            self._update_progress(f"Searching for keyword: {keyword}")
            
            # Use OpenAI Chat Completions with web search tool
            self._update_progress("Using OpenAI Web Search tool...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a web search assistant. Search the web and return the top 5 search results in JSON format with title, link, and snippet for each result."
                    },
                    {
                        "role": "user", 
                        "content": f"Search the web for: {keyword}. Return the top 5 search results in this exact JSON format:\n\n{{\n  \"results\": [\n    {{\n      \"title\": \"Result Title\",\n      \"link\": \"https://example.com\",\n      \"snippet\": \"Description of the result\"\n    }}\n  ]\n}}\n\nReturn ONLY valid JSON, no other text."
                    }
                ]
            )
            
            # Extract URLs from response (search-enabled models may return text or JSON)
            response_content = response.choices[0].message.content
            self._update_progress("Parsing web search results...")
            
            # Debug: Log the raw response
            print(f"[DEBUG] Raw API response (first 1000 chars): {response_content[:1000] if response_content else 'EMPTY'}")
            
            urls = []
            
            # Try to parse as JSON first
            try:
                search_results = json.loads(response_content)
                print(f"[DEBUG] Successfully parsed as JSON. Structure: {type(search_results)}, Keys: {list(search_results.keys()) if isinstance(search_results, dict) else 'N/A'}")
                
                # Extract from JSON structure
                if isinstance(search_results, dict) and 'results' in search_results:
                    print(f"[DEBUG] Found 'results' key with {len(search_results['results'])} items")
                    for result in search_results['results'][:5]:  # Top 5 results
                        link = result.get('link', '') or result.get('url', '')
                        if link:
                            urls.append(link)
                elif isinstance(search_results, list):
                    print(f"[DEBUG] Response is a list with {len(search_results)} items")
                    for result in search_results[:5]:  # Top 5 results
                        if isinstance(result, dict):
                            link = result.get('link', '') or result.get('url', '')
                            if link:
                                urls.append(link)
                elif isinstance(search_results, dict):
                    # Try to find URLs in any key
                    print(f"[DEBUG] Response is dict with keys: {list(search_results.keys())}")
                    for key, value in search_results.items():
                        if isinstance(value, list):
                            for item in value[:5]:  # Top 5 results
                                if isinstance(item, dict):
                                    link = item.get('link', '') or item.get('url', '') or item.get('href', '')
                                    if link:
                                        urls.append(link)
                                elif isinstance(item, str) and item.startswith('http'):
                                    urls.append(item)
                                    
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract URLs from plain text
                self._update_progress("JSON parsing failed, extracting URLs from text response...")
                print(f"[DEBUG] JSON parse failed: {str(e)}, trying to extract URLs from text")
                
                # Extract URLs using regex
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;!?)]'
                found_urls = re.findall(url_pattern, response_content)
                
                # Clean and deduplicate URLs
                seen = set()
                for url in found_urls:
                    url = url.rstrip('.,;!?)')
                    if url and url not in seen and len(url) > 10:  # Basic URL validation
                        seen.add(url)
                        urls.append(url)
                        if len(urls) >= 5:  # Top 5 results
                            break
                
                if not urls:
                    print(f"[ERROR] Could not extract URLs. Full response: {response_content}")
            
            if not urls:
                self._update_progress("No URLs found in web search response")
                print(f"[ERROR] No URLs extracted from response")
                if response_content:
                    print(f"[ERROR] Response content (first 1000 chars): {response_content[:1000]}")
                return []
            
            self._update_progress(f"Found {len(urls)} search results using OpenAI Web Search")
            print(f"[SUCCESS] OpenAI Web Search research completed. Found {len(urls)} URLs")
            
            # Log sample output
            print("\n" + "="*80)
            print("[SAMPLE OUTPUT - WebBrowseAgent]")
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
            import traceback
            self._update_progress(f"Error with OpenAI Web Search: {str(e)}")
            print(f"[ERROR] OpenAI Web Search failed: {str(e)}")
            print(f"[ERROR] Full traceback:")
            traceback.print_exc()
            return []
