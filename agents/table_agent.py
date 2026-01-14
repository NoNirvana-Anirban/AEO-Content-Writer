import json
from typing import Dict, Any
from config import Config
import requests

class TableAgent:
    """Agent responsible for generating HTML tables based on requirements"""
    
    def __init__(self, model: str = "openai/gpt-4o"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def generate_table(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an HTML table based on the requirement
        
        Args:
            requirement: Dictionary with structure:
                {
                    "type": "table",
                    "prompt": "Detailed prompt for table creation",
                    "placement": "Where in article",
                    "priority": "high" | "medium" | "low"
                }
        
        Returns:
            Dictionary with generated table data:
            {
                "type": "table",
                "html": "HTML table code",
                "placement": "original placement",
                "status": "success" | "error",
                "error": "error message if failed"
            }
        """
        if requirement.get('type') != 'table':
            return {
                'type': 'table',
                'status': 'error',
                'error': 'Requirement type is not "table"'
            }
        
        prompt = requirement.get('prompt', '')
        if not prompt:
            return {
                'type': 'table',
                'status': 'error',
                'error': 'No prompt provided in requirement'
            }
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at creating well-structured HTML tables. Generate clean, accessible, and properly formatted HTML table code."
                    },
                    {
                        "role": "user",
                        "content": f"""Create a beautifully styled HTML table based on this detailed prompt:

{prompt}

Requirements:
1. Generate valid, well-structured HTML table code with proper semantic structure
2. Include proper table headers (<thead> and <th>)
3. Ensure accessibility with proper scope attributes on headers
4. Include a <style> block with comprehensive CSS styling that includes:
   - Proper padding: 12px 16px for cells (td, th)
   - Clean borders: 1px solid #e1e5e9 for all borders
   - Alternating row shading: #f8f9fa for even rows, #ffffff for odd rows
   - Header styling: background color #667eea, white text, bold font
   - Hover effects: #f0f4ff background on row hover
   - Border radius: 8px on the table container
   - Box shadow: subtle shadow for depth
   - Responsive design: table should scroll horizontally on mobile
5. Wrap the table in a <div class="table-responsive"> container
6. Include a caption if appropriate
7. Make the table visually appealing with modern, professional styling

Return a JSON object with this structure:
{{
    "html": "string (complete HTML code including <style> block, <div class='table-responsive'>, <table>, and all content)",
    "caption": "string (optional table caption)"
}}

The HTML should include:
- A <style> block with all CSS rules
- A <div class="table-responsive"> wrapper
- A properly structured <table> with <thead>, <tbody>, <th>, <td> elements
- All styling should be inline in the style block, not external

Return ONLY valid JSON, no other text."""
                    }
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Table Agent"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            table_result = json.loads(response_data["choices"][0]["message"]["content"])
            
            html = table_result.get('html', '')
            caption = table_result.get('caption', '')
            
            # Ensure the table has proper styling if not already included
            if html and '<style>' not in html.lower():
                # Add default styling if missing
                default_style = """
<style>
.table-responsive {
    overflow-x: auto;
    margin: 20px 0;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.content-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
}
.content-table thead {
    background: #667eea;
    color: white;
}
.content-table th {
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 2px solid #5568d3;
}
.content-table tbody tr {
    border-bottom: 1px solid #e1e5e9;
    transition: background-color 0.2s ease;
}
.content-table tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}
.content-table tbody tr:nth-child(odd) {
    background-color: #ffffff;
}
.content-table tbody tr:hover {
    background-color: #f0f4ff;
}
.content-table td {
    padding: 12px 16px;
    font-size: 14px;
    color: #333;
    border-right: 1px solid #e1e5e9;
}
.content-table td:last-child,
.content-table th:last-child {
    border-right: none;
}
.content-table caption {
    padding: 12px;
    font-weight: 600;
    font-size: 16px;
    color: #333;
    text-align: left;
    background: #f8f9fa;
    border-bottom: 2px solid #e1e5e9;
}
@media (max-width: 768px) {
    .content-table {
        font-size: 12px;
    }
    .content-table th,
    .content-table td {
        padding: 8px 12px;
    }
}
</style>
"""
                # Wrap table if not already wrapped
                if '<div class="table-responsive">' not in html.lower():
                    html = f'<div class="table-responsive">{html}</div>'
                
                # Add style block if missing
                html = default_style + html
                
                # Ensure table has the content-table class
                if 'class="content-table"' not in html and 'class=\'content-table\'' not in html:
                    html = html.replace('<table', '<table class="content-table"', 1)
            
            return {
                'type': 'table',
                'html': html,
                'caption': caption,
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium'),
                'status': 'success'
            }
            
        except Exception as e:
            print(f"Error generating table: {e}")
            return {
                'type': 'table',
                'status': 'error',
                'error': f'Table generation failed: {str(e)}',
                'placement': requirement.get('placement', ''),
                'priority': requirement.get('priority', 'medium')
            }
    
    def run(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to generate table"""
        return self.generate_table(requirement)

