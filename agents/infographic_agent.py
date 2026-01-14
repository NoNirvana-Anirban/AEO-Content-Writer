import json
from typing import Dict, Any
from config import Config
import requests

class InfographicAgent:
    """Agent responsible for generating infographics based on requirements"""
    
    def __init__(self, model: str = "google/gemini-3-pro-image-preview"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def generate_infographic(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an infographic based on the requirement
        
        Args:
            requirement: Dictionary with structure:
                {
                    "type": "infographic",
                    "prompt": "Detailed prompt for infographic creation",
                    "placement": "Where in article",
                    "priority": "high" | "medium" | "low"
                }
        
        Returns:
            Dictionary with generated infographic data:
            {
                "type": "infographic",
                "image_url": "URL or base64 data",
                "alt_text": "Descriptive alt text",
                "placement": "original placement",
                "status": "success" | "error",
                "error": "error message if failed"
            }
        """
        if requirement.get('type') != 'infographic':
            return {
                'type': 'infographic',
                'status': 'error',
                'error': 'Requirement type is not "infographic"'
            }
        
        prompt = requirement.get('prompt', '')
        if not prompt:
            return {
                'type': 'infographic',
                'status': 'error',
                'error': 'No prompt provided in requirement'
            }
        
        try:
            # OpenRouter image generation requires modalities parameter
            # Images are returned as base64-encoded data URLs in the assistant message
            payload = {
                "model": self.model,
                "modalities": ["image", "text"],  # Required for image generation
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert infographic designer. Create informative, visually appealing infographics optimized for web publishing. Always generate infographics with dimensions 1200x1800 pixels (2:3 portrait aspect ratio) for optimal web display. Return the generated infographic as a base64 data URL, and provide alt text and caption in your response."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate an infographic based on this detailed prompt:

{prompt}

CRITICAL REQUIREMENTS:
1. Infographic dimensions: 1200x1800 pixels (2:3 portrait aspect ratio) - optimized for web publishing
2. Format: High-quality, web-optimized infographic suitable for blog posts and articles
3. Provide alt text: A clear, descriptive alt text (100-200 characters) explaining what the infographic shows
4. Provide caption: A caption explaining the infographic content (if relevant)

Please generate the infographic with the specified dimensions and return it as a base64 data URL. Format your response as:
Alt Text: [descriptive alt text here]
Caption: [optional caption here]
[base64 image data URL]"""
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Infographic Agent"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for infographic generation
            )
            response.raise_for_status()
            
            response_data = response.json()
            message = response_data["choices"][0]["message"]
            
            # Check for image in the response (base64 data URL)
            image_url = None
            alt_text = ''
            caption = ''
            
            # OpenRouter returns images in message.images array according to documentation
            # Structure: message.images[0].image_url.url
            if "images" in message and isinstance(message["images"], list) and len(message["images"]) > 0:
                image_obj = message["images"][0]  # Get first image
                if isinstance(image_obj, dict):
                    if "image_url" in image_obj and isinstance(image_obj["image_url"], dict):
                        image_url = image_obj["image_url"].get("url", "")
                    elif "url" in image_obj:
                        image_url = image_obj["url"]
            
            # Extract text content for alt text and caption
            content = message.get("content", "")
            if content and isinstance(content, str):
                text_content = content.strip()
                if text_content:
                    # Try to extract structured alt text and caption
                    import re
                    alt_match = re.search(r'alt\s*text\s*:?\s*(.+?)(?:\n|caption|$)', text_content, re.IGNORECASE)
                    caption_match = re.search(r'caption\s*:?\s*(.+?)(?:\n|alt|$)', text_content, re.IGNORECASE)
                    
                    if alt_match:
                        alt_text = alt_match.group(1).strip()[:200]
                    elif not alt_text:
                        # Fallback: use first line or first 200 chars
                        lines = [line.strip() for line in text_content.split('\n') if line.strip() and not line.strip().startswith('data:image')]
                        if lines:
                            alt_text = lines[0][:200]
                        else:
                            alt_text = text_content[:200]
                    
                    if caption_match:
                        caption = caption_match.group(1).strip()[:500]
                    elif not caption and len(text_content) > 200:
                        # Fallback: use second line or remaining text
                        lines = [line.strip() for line in text_content.split('\n') if line.strip() and not line.strip().startswith('data:image')]
                        if len(lines) > 1:
                            caption = ' '.join(lines[1:])[:500]
                    
                    # If still no alt_text, generate from prompt
                    if not alt_text or len(alt_text) < 10:
                        # Generate descriptive alt text from prompt
                        alt_text = prompt[:200] if prompt else 'Generated infographic'
            
            # Clean up image_url if found (remove any whitespace/newlines)
            if image_url:
                image_url = image_url.replace('\n', '').replace('\r', '').replace(' ', '')
            
            # If no image found, check if there's a description
            if not image_url:
                # No image generated, create placeholder
                description = str(content) if content else "Infographic generation in progress"
                return {
                    'type': 'infographic',
                    'image_url': '',
                    'description': description,
                    'alt_text': alt_text or description[:100],
                    'caption': caption,
                    'placement': requirement.get('placement', ''),
                    'priority': requirement.get('priority', 'medium'),
                    'status': 'success',
                    'is_placeholder': True
                }
            
            return {
                'type': 'infographic',
                'image_url': image_url,
                'alt_text': alt_text or 'Generated infographic',
                'caption': caption,
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium'),
                'status': 'success',
                'is_placeholder': False
            }
            
        except Exception as e:
            print(f"Error generating infographic: {e}")
            return {
                'type': 'infographic',
                'status': 'error',
                'error': f'Infographic generation failed: {str(e)}',
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium')
            }
    
    def run(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to generate infographic"""
        return self.generate_infographic(requirement)

