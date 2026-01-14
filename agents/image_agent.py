import json
from typing import Dict, Any
from config import Config
import requests

class ImageAgent:
    """Agent responsible for generating images based on requirements"""
    
    def __init__(self, model: str = "google/gemini-2.5-flash-image"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def generate_image(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an image based on the requirement
        
        Args:
            requirement: Dictionary with structure:
                {
                    "type": "image",
                    "prompt": "Detailed prompt for image creation",
                    "placement": "Where in article",
                    "priority": "high" | "medium" | "low"
                }
        
        Returns:
            Dictionary with generated image data:
            {
                "type": "image",
                "image_url": "URL or base64 data",
                "alt_text": "Descriptive alt text",
                "placement": "original placement",
                "status": "success" | "error",
                "error": "error message if failed"
            }
        """
        if requirement.get('type') != 'image':
            return {
                'type': 'image',
                'status': 'error',
                'error': 'Requirement type is not "image"'
            }
        
        prompt = requirement.get('prompt', '')
        if not prompt:
            return {
                'type': 'image',
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
                        "content": "You are an expert image generation AI. Generate high-quality images optimized for web publishing. Always generate images with dimensions 1200x800 pixels (16:10 aspect ratio) for optimal web display. Return the generated image as a base64 data URL, and provide alt text and caption in your response."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate an image based on this detailed prompt:

{prompt}

CRITICAL REQUIREMENTS:
1. Image dimensions: 1200x800 pixels (16:10 aspect ratio) - optimized for web publishing
2. Format: High-quality, web-optimized image suitable for blog posts and articles
3. Provide alt text: A clear, descriptive alt text (100-150 characters) for accessibility
4. Provide caption: An optional caption describing the image (if relevant)

Please generate the image with the specified dimensions and return it as a base64 data URL. Format your response as:
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
                "X-Title": "Image Agent"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for image generation
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
                        # Fallback: use first line or first 150 chars
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
                        alt_text = prompt[:150] if prompt else 'Generated image'
            
            # Clean up image_url if found (remove any whitespace/newlines)
            if image_url:
                image_url = image_url.replace('\n', '').replace('\r', '').replace(' ', '')
            
            # If no image found, check if there's a description
            if not image_url:
                # No image generated, create placeholder
                description = str(content) if content else "Image generation in progress"
                return {
                    'type': 'image',
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
                'type': 'image',
                'image_url': image_url,
                'alt_text': alt_text or 'Generated image',
                'caption': caption,
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium'),
                'status': 'success',
                'is_placeholder': False
            }
            
        except Exception as e:
            print(f"Error generating image: {e}")
            return {
                'type': 'image',
                'status': 'error',
                'error': f'Image generation failed: {str(e)}',
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium')
            }
    
    def run(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to generate image"""
        return self.generate_image(requirement)

