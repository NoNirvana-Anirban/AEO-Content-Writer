import json
from typing import Dict, List, Any
from config import Config
import requests

class DOMAnalysisAgent:
    """Agent responsible for extracting and analyzing DOM content from URLs using LLM + Web Search via OpenRouter"""
    
    def __init__(self, model: str = None):
        self.config = Config()
        # Use openai/gpt-4o model (web search enabled separately)
        self.model = model or "openai/gpt-4o"
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        self.progress_callback = None
        self.web_search_enabled = True  # Enable web search for analysis
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def set_progress_callback(self, callback):
        """Set the progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, message):
        """Update progress if callback is set"""
        if self.progress_callback:
            self.progress_callback(message)
    
    
    def _consolidate_topics(self, all_url_topics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate major and minor topics across all URLs, merging similar topics and their subtopics"""
        try:
            self._update_progress("Consolidating topics across all URLs...")
            
            # Collect all major topics from all URLs
            all_major_topics = {}
            all_minor_topics = {}
            
            for url, topics_data in all_url_topics.items():
                # Process major topics
                for major_topic in topics_data.get('major_topics', []):
                    topic_name = major_topic.get('name', '').strip()
                    if not topic_name:
                        continue
                    
                    # Use topic name as key (normalize for comparison)
                    normalized_name = topic_name.lower()
                    
                    if normalized_name not in all_major_topics:
                        all_major_topics[normalized_name] = {
                            "name": topic_name,
                            "subtopics": set(),  # Use set to avoid duplicates
                            "urls": []
                        }
                    
                    # Add subtopics
                    for subtopic in major_topic.get('subtopics', []):
                        if subtopic and subtopic.strip():
                            all_major_topics[normalized_name]["subtopics"].add(subtopic.strip())
                    
                    # Track which URLs have this topic
                    all_major_topics[normalized_name]["urls"].append(url)
                
                # Process minor topics
                for minor_topic in topics_data.get('minor_topics', []):
                    topic_name = minor_topic.get('name', '').strip()
                    if not topic_name:
                        continue
                    
                    normalized_name = topic_name.lower()
                    
                    if normalized_name not in all_minor_topics:
                        all_minor_topics[normalized_name] = {
                            "name": topic_name,
                            "subtopics": set(),
                            "urls": []
                        }
                    
                    for subtopic in minor_topic.get('subtopics', []):
                        if subtopic and subtopic.strip():
                            all_minor_topics[normalized_name]["subtopics"].add(subtopic.strip())
                    
                    all_minor_topics[normalized_name]["urls"].append(url)
            
            # Convert to final format: convert sets to sorted lists
            consolidated_major = []
            for topic_data in all_major_topics.values():
                consolidated_major.append({
                    "name": topic_data["name"],
                    "subtopics": sorted(list(topic_data["subtopics"]))
                })
            
            consolidated_minor = []
            for topic_data in all_minor_topics.values():
                consolidated_minor.append({
                    "name": topic_data["name"],
                    "subtopics": sorted(list(topic_data["subtopics"]))
                })
            
            # Sort by number of URLs that mention it (most common first)
            consolidated_major.sort(key=lambda x: len(all_major_topics[x["name"].lower()]["urls"]), reverse=True)
            consolidated_minor.sort(key=lambda x: len(all_minor_topics[x["name"].lower()]["urls"]), reverse=True)
            
            return {
                "major_topics": consolidated_major,
                "minor_topics": consolidated_minor
            }
            
        except Exception as e:
            self._update_progress(f"Error consolidating topics: {str(e)}")
            return {
                "major_topics": [],
                "minor_topics": []
            }
    
    def _analyze_url_with_web_search(self, url: str) -> Dict[str, Any]:
        """Analyze a single URL using OpenRouter with web search to extract major and minor topics with subtopics"""
        try:
            self._update_progress(f"Analyzing {url[:60]}...")
            
            prompt = f"""Analyze the content of this webpage: {url}

Using web search, fetch and analyze the actual content from this URL. Extract the main topics and organize them into major and minor categories.

Focus on extracting:
- Major topics: Core themes, main sections, primary subject areas (typically H2-level headings or main sections)
- Minor topics: Supporting concepts, secondary themes, less prominent but still relevant topics
- Subtopics: Specific points, details, or aspects covered under each major/minor topic

IMPORTANT: Ignore and do NOT include topics from Call-to-Action (CTA) sections such as:
- Sign-up forms and buttons
- Purchase/buy now buttons
- Newsletter subscription forms
- Download buttons
- Contact forms
- "Get started" or "Try now" prompts
- Pricing tables with purchase buttons
- Any promotional or sales-focused content

Only extract topics from the actual informational/educational content.

Return a JSON object with this exact structure:
{{
  "major_topics": [
    {{
      "name": "Major topic name (clear, descriptive, 5-15 words)",
      "subtopics": [
        "Specific subtopic 1 (detailed, 5-20 words)",
        "Specific subtopic 2",
        "Specific subtopic 3"
      ]
    }},
    {{
      "name": "Another major topic",
      "subtopics": ["subtopic 1", "subtopic 2"]
    }}
  ],
  "minor_topics": [
    {{
      "name": "Minor topic name",
      "subtopics": ["subtopic 1", "subtopic 2"]
    }}
  ]
}}

Guidelines:
- Major topics should represent the main sections/themes of the content (typically 3-8 major topics)
- Each major topic should have 3-8 subtopics that are specific and detailed
- Minor topics are supporting themes (typically 2-5 minor topics)
- Each minor topic should have 2-5 subtopics
- Topic names should be clear, descriptive, and NOT generic (avoid "introduction", "conclusion", "about us", etc.)
- Subtopics should be specific, actionable, or descriptive points covered in that section
- Do NOT include CTA-related content

Return ONLY valid JSON, no other text."""

            # Prepare request payload for OpenRouter API
            payload = {
                "model": self.model,  # "openai/gpt-4o"
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing web content and extracting structured topics with subtopics. You have access to web search to fetch and analyze webpage content. Return only valid JSON in the exact format specified."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"}
            }
            
            # Enable web search via OpenRouter plugins
            # Note: Some models may not support plugins, so we'll try with and without
            if self.web_search_enabled:
                payload["plugins"] = [
                    {
                        "id": "web",
                        "max_results": 5
                    }
                ]
            
            # Make direct HTTP request to OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter analytics
                "X-Title": "DOM Analysis Agent"  # Optional: for OpenRouter analytics
            }
            
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # If 500 error and plugins are enabled, retry without plugins
                if e.response.status_code == 500 and self.web_search_enabled and "plugins" in payload:
                    print(f"[WARNING] Request with plugins failed (500), retrying without plugins for {url[:60]}...")
                    payload.pop("plugins", None)  # Remove plugins
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    response.raise_for_status()
                else:
                    raise  # Re-raise if it's not a 500 or plugins weren't enabled
            
            response_data = response.json()
            result = json.loads(response_data["choices"][0]["message"]["content"])
            
            # Validate and return structure
            return {
                "major_topics": result.get('major_topics', []),
                "minor_topics": result.get('minor_topics', [])
            }
            
        except Exception as e:
            self._update_progress(f"Error analyzing {url}: {str(e)}")
            return {"major_topics": [], "minor_topics": []}
    
    def run(self, urls: List[str]) -> Dict[str, Any]:
        """Main method to run DOM analysis using LLM + Web Search and return consolidated major/minor topics"""
        print(f"[INFO] Starting DOM analysis for {len(urls)} URLs using OpenRouter with Web Search")
        
        all_url_topics = {}
        successful_urls = 0
        
        for i, url in enumerate(urls, 1):
            try:
                self._update_progress(f"Processing URL {i}/{len(urls)}: {url[:50]}...")
                
                # Analyze URL using OpenRouter with web search
                topics_data = self._analyze_url_with_web_search(url)
                
                major_count = len(topics_data.get('major_topics', []))
                minor_count = len(topics_data.get('minor_topics', []))
                
                if major_count > 0 or minor_count > 0:
                    all_url_topics[url] = topics_data
                    successful_urls += 1
                    self._update_progress(f"Found {major_count} major and {minor_count} minor topics for {url[:50]}...")
                else:
                    self._update_progress(f"No topics extracted from {url[:50]}...")
                
            except Exception as e:
                self._update_progress(f"Error processing {url}: {str(e)}")
                continue
        
        # Consolidate topics across all URLs
        if not all_url_topics:
            print("[WARNING] No topics extracted from any URLs")
            return {
                "major_topics": [],
                "minor_topics": []
            }
        
        consolidated_result = self._consolidate_topics(all_url_topics)
        
        print(f"[SUCCESS] DOM analysis completed. Analyzed {successful_urls} URLs")
        print(f"[INFO] Consolidated into {len(consolidated_result['major_topics'])} major topics and {len(consolidated_result['minor_topics'])} minor topics")
        
        # Log sample output
        print("\n" + "="*80)
        print("[SAMPLE OUTPUT - DOMAnalysisAgent]")
        print("="*80)
        print(f"Return type: Dict[str, Any]")
        print(f"Major topics: {len(consolidated_result['major_topics'])}")
        if consolidated_result['major_topics']:
            print(f"Sample major topic: {consolidated_result['major_topics'][0]['name']}")
            print(f"  Subtopics: {len(consolidated_result['major_topics'][0]['subtopics'])}")
        print(f"Minor topics: {len(consolidated_result['minor_topics'])}")
        print(f"Sample JSON structure (first major topic):")
        sample_output = {
            "major_topics": consolidated_result['major_topics'][:1] if consolidated_result['major_topics'] else [],
            "minor_topics": consolidated_result['minor_topics'][:1] if consolidated_result['minor_topics'] else []
        }
        print(json.dumps(sample_output, indent=2))
        print("="*80 + "\n")
        
        return consolidated_result

