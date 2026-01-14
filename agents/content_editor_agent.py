import json
import os
import re
from typing import Dict, List, Any
from config import Config
import requests

class ContentEditorAgent:
    """Agent responsible for editing content to adhere to tone guidelines"""
    
    def __init__(self, json_model: str = "openai/gpt-4o", content_model: str = "openai/gpt-5"):
        self.config = Config()
        self.json_model = json_model
        self.content_model = content_model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        
        # Load tone guidelines file
        self.tone_file_path = os.path.join(os.path.dirname(__file__), "tone.txt")
    
    def _load_tone_guidelines(self) -> str:
        """Load tone guidelines from tone.txt file"""
        try:
            with open(self.tone_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Tone guidelines file not found: {self.tone_file_path}")
        except Exception as e:
            raise Exception(f"Error reading tone guidelines file: {str(e)}")
    
    def _convert_tone_to_json(self, tone_text: str) -> Dict[str, Any]:
        """Convert tone.txt to structured JSON using GPT-4o"""
        try:
            prompt = f"""Convert the following tone and quality guidelines into a structured JSON format that can be used to edit content.

Tone Guidelines:
{tone_text}

Create a comprehensive JSON structure that captures:
1. Core behavior principles
2. Tonality requirements
3. Structure and output discipline rules
4. Vocabulary controls (forbidden words, preferred style)
5. Quality standards
6. Internal self-editing checklist
7. Examples (approved vs not approved)

Return ONLY a valid JSON object with this structure:
{{
    "core_behavior": {{
        "principles": [
            {{"name": "string", "description": "string", "rules": ["string"]}}
        ]
    }},
    "tonality": {{
        "requirements": [
            {{"name": "string", "description": "string", "guidelines": ["string"]}}
        ]
    }},
    "structure": {{
        "rules": [
            {{"name": "string", "description": "string", "requirements": ["string"]}}
        ]
    }},
    "vocabulary": {{
        "forbidden_words": ["string"],
        "preferred_style": {{
            "nouns": ["string"],
            "verbs": ["string"],
            "descriptors": ["string"]
        }}
    }},
    "quality_standards": {{
        "depth_requirements": ["string"],
        "research_behavior": ["string"],
        "example_quality": ["string"],
        "originality": ["string"]
    }},
    "editing_checklist": [
        {{"category": "string", "checks": ["string"]}}
    ],
    "examples": {{
        "approved": [
            {{"type": "string", "text": "string"}}
        ],
        "not_approved": [
            {{"type": "string", "text": "string"}}
        ]
    }},
    "default_rules": ["string"]
}}

Return ONLY valid JSON, no other text."""

            payload = {
                "model": self.json_model,
                "messages": [
                    {"role": "system", "content": "You are an expert at converting guidelines and instructions into structured JSON format. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Content Editor Agent - JSON Converter"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            tone_json = json.loads(response_data["choices"][0]["message"]["content"])
            
            return tone_json
            
        except Exception as e:
            print(f"Error converting tone to JSON: {e}")
            # Return a minimal structure if conversion fails
            return {
                "error": str(e),
                "core_behavior": {"principles": []},
                "tonality": {"requirements": []},
                "vocabulary": {"forbidden_words": []}
            }
    
    def _edit_content_with_tone(self, content: str, tone_json: Dict[str, Any]) -> str:
        """Edit content to adhere to tone guidelines using GPT-5"""
        try:
            # Extract heading structure from original content to preserve it
            heading_pattern = r'<h([1-4])[^>]*>(.*?)</h[1-4]>'
            original_headings = re.findall(heading_pattern, content, re.IGNORECASE | re.DOTALL)
            
            # Format tone JSON for the prompt
            tone_guidelines = json.dumps(tone_json, indent=2)
            
            prompt = f"""Edit the following blog post content to strictly adhere to the tone and quality guidelines provided.

Tone Guidelines (JSON):
{tone_guidelines}

Original Content:
{content}

CRITICAL REQUIREMENTS - HEADING STRUCTURE PRESERVATION:
1. You MUST preserve the EXACT heading structure from the original content
2. DO NOT add, remove, or modify any heading tags (H1, H2, H3, H4)
3. DO NOT change heading text unless it contains forbidden words (then replace only the forbidden words)
4. DO NOT change heading hierarchy or order
5. DO NOT change heading levels (e.g., don't convert H2 to H3)
6. The heading structure is CRITICAL and must remain IDENTICAL

Editing Instructions:
1. Review every sentence against the tone guidelines
2. Remove any forbidden words and replace with preferred alternatives
3. Ensure clarity, substance, and zero hallucination
4. Follow the structure and output discipline rules
5. Apply the editing checklist before finalizing
6. ONLY edit the text content within paragraphs, lists, and other non-heading elements
7. Preserve ALL HTML tags exactly as they are (especially heading tags)
8. Only edit the content to match tone - do not change the topic, structure, or headings

Return the edited content as a JSON object with this structure:
{{
    "content": "string (HTML formatted with EXACT same heading structure, edited to match tone guidelines)"
}}

Return ONLY valid JSON, no other text."""

            payload = {
                "model": self.content_model,
                "messages": [
                    {"role": "system", "content": "You are an expert content editor. Your primary task is to edit content to strictly adhere to tone and quality guidelines while ABSOLUTELY PRESERVING the heading structure. You must NOT modify, add, remove, or change any heading tags (H1, H2, H3, H4) or their text. Only edit the paragraph and list content to match tone guidelines."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Content Editor Agent - Content Editor"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # Longer timeout for content editing
            )
            response.raise_for_status()
            
            response_data = response.json()
            edited_result = json.loads(response_data["choices"][0]["message"]["content"])
            edited_content = edited_result.get('content', content)
            
            # Validate that heading structure is preserved
            edited_headings = re.findall(heading_pattern, edited_content, re.IGNORECASE | re.DOTALL)
            
            # Check if heading count matches
            if len(edited_headings) != len(original_headings):
                print(f"[WARNING] Heading count mismatch: Original had {len(original_headings)} headings, edited has {len(edited_headings)}. Returning original content.")
                return content
            
            # Check if heading levels and order match
            for i, (orig_level, orig_text) in enumerate(original_headings):
                if i < len(edited_headings):
                    edit_level, edit_text = edited_headings[i]
                    if orig_level != edit_level:
                        print(f"[WARNING] Heading level changed at position {i}: Original H{orig_level} -> Edited H{edit_level}. Returning original content.")
                        return content
            
            return edited_content
            
        except Exception as e:
            print(f"Error editing content: {e}")
            return content  # Return original content if editing fails
    
    def run(self, blog_post: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to edit blog post content according to tone guidelines
        
        Args:
            blog_post: Output from content_writer_agent with structure:
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
        
        # Load tone guidelines
        tone_text = self._load_tone_guidelines()
        
        # Convert tone to JSON
        tone_json = self._convert_tone_to_json(tone_text)
        
        # Get original content
        original_content = blog_post.get('content', '')
        
        if not original_content:
            return {
                **blog_post,
                'error': 'No content found in blog post to edit'
            }
        
        # Edit content with tone guidelines
        edited_content = self._edit_content_with_tone(original_content, tone_json)
        
        # Return edited blog post
        edited_blog_post = {
            **blog_post,
            'content': edited_content,
            'tone_guidelines_applied': True
        }
        
        return edited_blog_post

