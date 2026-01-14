import json
from typing import Dict, List, Any
from config import Config
import requests

class ContentPresenterAgent:
    """Agent responsible for analyzing content and determining visual element requirements"""
    
    def __init__(self, model: str = "openai/gpt-4o"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def analyze_and_create_requirements(self, blog_post: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content and create requirements for visual elements
        
        Args:
            blog_post: Output from content_editor_agent with structure:
                {
                    "title": str,
                    "meta_title": str,
                    "meta_description": str,
                    "content": str (HTML formatted),
                    "content_brief_id": str
                }
        """
        if 'error' in blog_post:
            return blog_post
        
        title = blog_post.get('title', '')
        content = blog_post.get('content', '')
        
        if not content:
            return {
                **blog_post,
                'error': 'No content found in blog post to analyze'
            }
        
        # Extract text content from HTML for analysis (remove HTML tags for better analysis)
        import re
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = ' '.join(text_content.split())  # Normalize whitespace
        
        # Limit content to first 5000 chars for analysis
        content_preview = text_content[:5000] if len(text_content) > 5000 else text_content
        
        prompt = f"""Analyze the following blog post content and determine what visual elements should be added to enhance the article.

Title: {title}

Content:
{content_preview}

As an expert content manager, analyze the content and determine what visual elements would enhance the reader experience:

1. **Images**: Use ONLY for photos and pictures
   - Use for: Real photos, product images, location photos, screenshots, actual pictures of things
   - DO NOT use for: Diagrams, charts, flowcharts, text-based visuals, illustrations with text labels, or any visual that requires text annotations
   - Images are cost-effective and should be used for actual photographs and pictures
   - Zero images if the content has no actual photos or pictures to show

2. **Infographics**: Use for diagrams, charts, and visuals with text
   - CRITICAL: Infographics are 5x more expensive than images. Use them EXTREMELY judiciously.
   - MAXIMUM: Only 1 infographic per article, and ONLY if absolutely necessary
   - Use for: Complex multi-step processes that CANNOT be explained with images alone, intricate system architectures that require text labels, or critical data visualizations that MUST have annotations
   - AVOID if: The concept can be explained with images and text descriptions, or if the visual complexity doesn't justify the 5x cost
   - DO NOT use for: Simple photos or pictures (use images instead)
   - When a visual requires text, labels, or annotations, consider if an image with a caption would suffice before choosing an infographic
   - RULE: If you can explain it with images and text, use images. Only use infographics for concepts that are IMPOSSIBLE to convey without a diagram with text labels

3. **Tables**: Determine if tables would improve clarity
   - Consider: comparisons, specifications, data sets, step-by-step instructions, pricing
   - Use when structured data presentation is clearer than paragraphs
   - Zero tables if content doesn't contain tabular data

Guidelines:
- IMAGES = Photos/Pictures only: Use images for actual photographs, product images, location photos, screenshots
- INFOGRAPHICS = Last resort for complex diagrams: Use infographics ONLY when a concept is IMPOSSIBLE to explain without a diagram with text labels
- CRITICAL RULE: Maximum 1 infographic per article. Only use if absolutely necessary and cannot be replaced by images with captions
- Cost consideration: 5 images ≈ 1 infographic in cost. Prefer multiple images over 1 infographic when possible
- AVOID infographics unless: The visual complexity and text requirements make it the ONLY viable option
- Be strategic: Only suggest visual elements that genuinely enhance understanding
- Quality over quantity: Better to have fewer, well-placed visuals than many unnecessary ones
- Each requirement should have a clear purpose
- INFographic constraint: If you suggest an infographic, ensure it's the single most critical visual element that cannot be replaced

Return a JSON object with this structure:
{{
    "requirements": [
        {{
            "type": "image" | "infographic" | "table",
            "prompt": "Detailed prompt describing what should be created, including specific details, style, purpose, and placement context",
            "placement": "string (e.g., 'after H2: How to Cook', 'beginning of article', 'comparison section')",
            "priority": "high" | "medium" | "low"
        }}
    ],
    "analysis_summary": "Brief explanation of why these visual elements were chosen"
}}

Return ONLY valid JSON, no other text."""

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert content manager with deep expertise in content strategy, visual design, and user experience. Analyze content and determine optimal visual elements to enhance reader engagement and understanding."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Content Presenter Agent"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            requirements_data = json.loads(response_data["choices"][0]["message"]["content"])
            
            # Enforce maximum 1 infographic rule
            requirements = requirements_data.get('requirements', [])
            infographics = [r for r in requirements if r.get('type') == 'infographic']
            
            if len(infographics) > 1:
                # Keep only the highest priority infographic, or first one if priorities are equal
                infographics.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'low'), 1), reverse=True)
                # Remove all but the first infographic
                infographic_to_keep = infographics[0]
                # Remove all infographics from requirements
                requirements = [r for r in requirements if r.get('type') != 'infographic']
                # Add back only the highest priority one
                requirements.append(infographic_to_keep)
                print(f"[INFO] Limited infographics to 1 (kept highest priority: {infographic_to_keep.get('priority')})")
            
            # Add requirements to blog post
            blog_post['visual_requirements'] = requirements
            blog_post['visual_analysis_summary'] = requirements_data.get('analysis_summary', '')
            
            return blog_post
            
        except Exception as e:
            print(f"Error creating visual requirements: {e}")
            return {
                **blog_post,
                'error': f'Visual requirements generation failed: {str(e)}',
                'visual_requirements': [],
                'visual_analysis_summary': ''
            }
    
    def run(self, blog_post: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to analyze content and create visual requirements"""
        return self.analyze_and_create_requirements(blog_post)

