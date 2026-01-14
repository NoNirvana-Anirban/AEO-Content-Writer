import json
from typing import Dict, List, Any
from config import Config
import requests

class ContentWriterAgent:
    """Agent responsible for creating SEO-optimized blog posts with on-page elements"""
    
    def __init__(self, model: str = "openai/gpt-5"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def create_blog_post(self, content_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete blog post from content brief"""
        
        if 'error' in content_brief:
            return content_brief
        
        # Extract key information from brief (only content-related)
        target_keyword = content_brief.get('target_keyword', '')
        heading_structure = content_brief.get('heading_structure', [])
        topics_to_cover = content_brief.get('topics_to_cover', [])
        lsi_keywords = content_brief.get('lsi_keywords', [])
        recommended_word_count = content_brief.get('recommended_word_count', 2000)
        
        # Create comprehensive prompt for content writing only
        prompt = f"""
        Write comprehensive, SEO-optimized blog post content based on the following content brief:

        Target Keyword: {target_keyword}
        LSI Keywords: {', '.join(lsi_keywords)}
        Recommended Word Count: {recommended_word_count}
        
        Heading Structure:
        {json.dumps(heading_structure, indent=2)}
        
        Topics to Cover:
        {', '.join(topics_to_cover)}
        
        Requirements:
        1. Write engaging, informative content that naturally incorporates the target keyword and LSI keywords
        2. Follow the provided heading structure exactly (use H1, H2, H3, H4 as specified)
        3. Aim for approximately {recommended_word_count} words
        4. Include practical examples, tips, and actionable advice
        5. Write in a conversational yet authoritative tone
        6. Ensure proper keyword density (1-2% for primary keyword)
        7. If the content includes code examples (JSON, HTML, JavaScript, Python, SQL, etc.), format them using proper code blocks:
           - Use <pre class="wp-block-code"><code class="language-[lang]">[code]</code></pre> format
           - Detect language automatically (json, html, javascript, python, sql, php, css, etc.)
           - Ensure code is properly escaped and formatted
           - Example: <pre class="wp-block-code"><code class="language-json">{{"key": "value"}}</code></pre>
        
        Return the response as a JSON object with the following structure:
        {{
            "content": "string (HTML formatted with proper heading tags H1, H2, H3, H4, and code blocks when needed)"
        }}
        """
        
        try:
            # Prepare request payload for OpenRouter API
            payload = {
                "model": self.model,  # "openai/gpt-5"
                "messages": [
                    {"role": "system", "content": "You are an expert SEO content writer. Create comprehensive, engaging blog posts that rank well in search engines while providing genuine value to readers."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            # Make direct HTTP request to OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter analytics
                "X-Title": "Content Writer Agent"  # Optional: for OpenRouter analytics
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for content generation
            )
            response.raise_for_status()
            
            response_data = response.json()
            blog_post = json.loads(response_data["choices"][0]["message"]["content"])
            
            # Add metadata from content brief (title, meta tags are from brief, not generated here)
            blog_post['title'] = content_brief.get('recommended_title', '')
            blog_post['meta_title'] = content_brief.get('meta_title', '')
            blog_post['meta_description'] = content_brief.get('meta_description', '')
            blog_post['content_brief_id'] = content_brief.get('target_keyword', '')
            
            return blog_post
            
        except Exception as e:
            print(f"Error creating blog post: {e}")
            return {
                'error': f'Content generation failed: {str(e)}',
                'title': content_brief.get('recommended_title', ''),
                'meta_title': content_brief.get('meta_title', ''),
                'meta_description': content_brief.get('meta_description', ''),
                'content': ''
            }
    
    def run(self, content_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to run content writing"""
        return self.create_blog_post(content_brief)
