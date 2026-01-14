import re
import html
from typing import Dict, List, Any
from agents.image_agent import ImageAgent
from agents.infographic_agent import InfographicAgent
from agents.table_agent import TableAgent

class LayoutAgent:
    """Agent responsible for placing visual elements into content based on requirements"""
    
    def __init__(self):
        self.image_agent = ImageAgent()
        self.infographic_agent = InfographicAgent()
        self.table_agent = TableAgent()
    
    def _generate_visual_element(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a visual element based on requirement type"""
        req_type = requirement.get('type', '').lower()
        
        if req_type == 'image':
            return self.image_agent.run(requirement)
        elif req_type == 'infographic':
            return self.infographic_agent.run(requirement)
        elif req_type == 'table':
            return self.table_agent.run(requirement)
        else:
            return {
                'type': req_type,
                'status': 'error',
                'error': f'Unknown requirement type: {req_type}'
            }
    
    def _find_placement_position(self, content: str, placement: str, element_type: str = '') -> int:
        """Find the position in content where the visual element should be placed
        
        Args:
            content: HTML content string
            placement: Placement description (e.g., "after H2: How to Cook", "beginning of article")
            element_type: Type of element ('image', 'infographic', 'table')
        
        Returns:
            Position index where element should be inserted
        """
        placement_lower = placement.lower()
        
        # Special handling for infographics - place early (1st or 2nd fold)
        if element_type == 'infographic':
            # Find H1 end
            h1_match = re.search(r'</h1>', content, re.IGNORECASE)
            if h1_match:
                h1_end = h1_match.end()
                # Find first H2 after H1
                h2_match = re.search(r'<h2[^>]*>.*?</h2>', content[h1_end:], re.IGNORECASE | re.DOTALL)
                if h2_match:
                    # Place after first H2 (2nd fold)
                    return h1_end + h2_match.end()
                # If no H2, place after H1 (1st fold)
                return h1_end
            return 0
        
        # Special handling for tables - avoid very end
        if element_type == 'table':
            # Try to find placement, but if it would be at the end, place at 75% of content
            content_length = len(content)
            default_table_position = int(content_length * 0.75)  # 75% through content
        
        # Beginning of article
        if 'beginning' in placement_lower or 'start' in placement_lower:
            # Find first content after H1
            h1_match = re.search(r'</h1>', content, re.IGNORECASE)
            if h1_match:
                return h1_match.end()
            return 0
        
        # After specific heading - improved matching
        if 'after' in placement_lower:
            # Extract heading text from placement (more flexible patterns)
            # Pattern 1: "after H2: Title" or "after section: Title"
            heading_match = re.search(r'(?:h\d+|section)[:\s]+(.+?)(?:\s|$|,|\.)', placement, re.IGNORECASE)
            if heading_match:
                heading_text = heading_match.group(1).strip()
                # Try exact match first
                heading_pattern = rf'<h[2-4][^>]*>.*?{re.escape(heading_text)}.*?</h[2-4]>'
                match = re.search(heading_pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.end()
                
                # Try partial match (heading contains the text)
                words = heading_text.split()
                if len(words) > 0:
                    # Try matching with first few words
                    for word_count in range(len(words), 0, -1):
                        partial_text = ' '.join(words[:word_count])
                        heading_pattern = rf'<h[2-4][^>]*>.*?{re.escape(partial_text)}.*?</h[2-4]>'
                        match = re.search(heading_pattern, content, re.IGNORECASE | re.DOTALL)
                        if match:
                            return match.end()
            
            # Pattern 2: "after describing each breed" - find relevant section
            if 'describing' in placement_lower or 'each' in placement_lower:
                # Find H3 headings (usually subsections)
                h3_matches = list(re.finditer(r'<h3[^>]*>.*?</h3>', content, re.IGNORECASE | re.DOTALL))
                if h3_matches:
                    # Place after first H3
                    return h3_matches[0].end()
            
            # Try to find by heading level
            level_match = re.search(r'h(\d+)', placement_lower)
            if level_match:
                level = level_match.group(1)
                pattern = rf'<h{level}[^>]*>.*?</h{level}>'
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
                if matches:
                    # For images, try to find the most relevant one based on context
                    if element_type == 'image' and len(matches) > 1:
                        # Place after first matching heading (more relevant)
                        return matches[0].end()
                    return matches[-1].end()
        
        # Before specific heading
        if 'before' in placement_lower:
            heading_match = re.search(r'(?:h\d+|section)[:\s]+(.+?)(?:\s|$|,|\.)', placement, re.IGNORECASE)
            if heading_match:
                heading_text = heading_match.group(1).strip()
                heading_pattern = rf'<h[2-4][^>]*>.*?{re.escape(heading_text)}.*?</h[2-4]>'
                match = re.search(heading_pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.start()
        
        # Within section (find the section and place in middle/end of section)
        if 'within' in placement_lower:
            heading_match = re.search(r'(?:h\d+|section)[:\s]+(.+?)(?:\s|$|,|\.)', placement, re.IGNORECASE)
            if heading_match:
                heading_text = heading_match.group(1).strip()
                heading_pattern = rf'<h[2-4][^>]*>.*?{re.escape(heading_text)}.*?</h[2-4]>'
                match = re.search(heading_pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    section_start = match.end()
                    # Find next heading after this one
                    next_heading = re.search(r'<h[2-4]', content[section_start:], re.IGNORECASE)
                    if next_heading:
                        section_end = section_start + next_heading.start()
                        # Place in middle of section (not at very end)
                        return section_start + int((section_end - section_start) * 0.7)
                    # If no next heading, place at 80% of remaining content (not at very end)
                    remaining = len(content) - section_start
                    return section_start + int(remaining * 0.8)
        
        # Default placement based on element type
        if element_type == 'table':
            # Tables: 75% through content (not at very end)
            return int(len(content) * 0.75)
        elif element_type == 'image':
            # Images: Try to place after first H2 if available
            h1_match = re.search(r'</h1>', content, re.IGNORECASE)
            if h1_match:
                h2_match = re.search(r'<h2[^>]*>.*?</h2>', content[h1_match.end():], re.IGNORECASE | re.DOTALL)
                if h2_match:
                    return h1_match.end() + h2_match.end()
            # Default: 50% through content
            return int(len(content) * 0.5)
        else:
            # Default: 60% through content (not at very end)
            return int(len(content) * 0.6)
    
    def _insert_image(self, content: str, position: int, image_data: Dict[str, Any]) -> str:
        """Insert an image element into content at specified position"""
        image_url = image_data.get('image_url', '')
        alt_text = image_data.get('alt_text', '')
        caption = image_data.get('caption', '')
        description = image_data.get('description', '')
        is_placeholder = image_data.get('is_placeholder', False)
        
        # Build image HTML
        if image_url:
            # Ensure alt_text is present and properly escaped
            if not alt_text:
                alt_text = description or 'Image'
            # Escape HTML entities in alt_text
            alt_text_escaped = html.escape(alt_text)
            # Actual image URL available
            img_html = f'<figure class="content-image">\n    <img src="{image_url}" alt="{alt_text_escaped}" class="img-responsive" />\n'
            if caption:
                caption_escaped = html.escape(caption)
                img_html += f'    <figcaption>{caption_escaped}</figcaption>\n'
            img_html += '</figure>\n\n'
        elif is_placeholder and description:
            # Create a styled placeholder for image description
            img_html = f'''<figure class="content-image image-placeholder">
    <div class="placeholder-content">
        <div class="placeholder-icon">🖼️</div>
        <div class="placeholder-description">{description}</div>
        <div class="placeholder-label">Image Placeholder</div>
    </div>
    {f'<figcaption>{caption}</figcaption>' if caption else ''}
</figure>

<style>
.content-image.image-placeholder {{
    border: 2px dashed #667eea;
    border-radius: 8px;
    padding: 40px 20px;
    margin: 20px 0;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    text-align: center;
}}
.placeholder-content {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 15px;
}}
.placeholder-icon {{
    font-size: 48px;
    opacity: 0.6;
}}
.placeholder-description {{
    color: #333;
    font-size: 14px;
    line-height: 1.6;
    max-width: 600px;
    font-style: italic;
}}
.placeholder-label {{
    color: #667eea;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
</style>

'''
        else:
            # No image data available, skip
            return content
        
        return content[:position] + img_html + content[position:]
    
    def _insert_infographic(self, content: str, position: int, infographic_data: Dict[str, Any]) -> str:
        """Insert an infographic element into content at specified position"""
        image_url = infographic_data.get('image_url', '')
        alt_text = infographic_data.get('alt_text', '')
        caption = infographic_data.get('caption', '')
        description = infographic_data.get('description', '')
        is_placeholder = infographic_data.get('is_placeholder', False)
        
        # Build infographic HTML
        if image_url:
            # Ensure alt_text is present and properly escaped
            if not alt_text:
                alt_text = description or 'Infographic'
            # Escape HTML entities in alt_text
            alt_text_escaped = html.escape(alt_text)
            # Actual image URL available
            infographic_html = f'<figure class="content-infographic">\n    <img src="{image_url}" alt="{alt_text_escaped}" class="img-responsive infographic" />\n'
            if caption:
                caption_escaped = html.escape(caption)
                infographic_html += f'    <figcaption>{caption_escaped}</figcaption>\n'
            infographic_html += '</figure>\n\n'
        elif is_placeholder and description:
            # Create a styled placeholder for infographic description
            infographic_html = f'''<figure class="content-infographic infographic-placeholder">
    <div class="placeholder-content">
        <div class="placeholder-icon">📊</div>
        <div class="placeholder-description">{description}</div>
        <div class="placeholder-label">Infographic Placeholder</div>
    </div>
    {f'<figcaption>{caption}</figcaption>' if caption else ''}
</figure>

<style>
.content-infographic.infographic-placeholder {{
    border: 2px dashed #10b981;
    border-radius: 8px;
    padding: 40px 20px;
    margin: 20px 0;
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
    text-align: center;
}}
.placeholder-content {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 15px;
}}
.placeholder-icon {{
    font-size: 48px;
    opacity: 0.6;
}}
.placeholder-description {{
    color: #333;
    font-size: 14px;
    line-height: 1.6;
    max-width: 700px;
    font-style: italic;
}}
.placeholder-label {{
    color: #10b981;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
</style>

'''
        else:
            # No infographic data available, skip
            return content
        
        return content[:position] + infographic_html + content[position:]
    
    def _insert_table(self, content: str, position: int, table_data: Dict[str, Any]) -> str:
        """Insert a table element into content at specified position"""
        html = table_data.get('html', '')
        caption = table_data.get('caption', '')
        
        if not html:
            return content
        
        # The table HTML from table_agent already includes styling and wrapper
        # Just add caption if provided and not already in HTML
        if caption and '<caption>' not in html.lower():
            # Try to insert caption - check if there's a table tag
            if '<table' in html.lower():
                # Insert caption after opening table tag
                import re
                html = re.sub(r'(<table[^>]*>)', r'\1\n    <caption>' + caption + '</caption>', html, count=1, flags=re.IGNORECASE)
        
        # The HTML from table_agent should already be complete with styling
        # Just add spacing
        table_html = html + '\n\n'
        
        return content[:position] + table_html + content[position:]
    
    def _insert_visual_element(self, content: str, visual_element: Dict[str, Any]) -> str:
        """Insert a visual element into content based on its type and placement"""
        element_type = visual_element.get('type', '')
        placement = visual_element.get('placement', '')
        status = visual_element.get('status', 'error')
        
        if status != 'success':
            # Skip failed elements
            return content
        
        # Find placement position (pass element_type for better placement logic)
        position = self._find_placement_position(content, placement, element_type)
        
        # Insert based on type
        if element_type == 'image':
            return self._insert_image(content, position, visual_element)
        elif element_type == 'infographic':
            return self._insert_infographic(content, position, visual_element)
        elif element_type == 'table':
            return self._insert_table(content, position, visual_element)
        
        return content
    
    def create_layout(self, edited_content: str, visual_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create final layout by generating and placing all visual elements
        
        Args:
            edited_content: HTML content from content_editor_agent
            visual_requirements: List of requirements from content_presenter_agent
        
        Returns:
            Dictionary with final content and generation results:
            {
                "content": "Final HTML content with visual elements",
                "generated_elements": [List of generated elements with status],
                "errors": [List of errors if any]
            }
        """
        if not edited_content:
            return {
                'content': '',
                'generated_elements': [],
                'errors': ['No content provided']
            }
        
        if not visual_requirements:
            return {
                'content': edited_content,
                'generated_elements': [],
                'errors': []
            }
        
        # Sort requirements: infographics first (early placement), then images, then tables
        # Within each type, sort by priority (high first)
        type_priority = {'infographic': 0, 'image': 1, 'table': 2}
        sorted_requirements = sorted(
            visual_requirements,
            key=lambda x: (
                type_priority.get(x.get('type', '').lower(), 3),  # Type priority first
                {'high': 0, 'medium': 1, 'low': 2}.get(x.get('priority', 'medium'), 1)  # Then priority
            )
        )
        
        generated_elements = []
        errors = []
        final_content = edited_content
        
        # Generate and insert each visual element
        # Process in reverse order to maintain correct positions when inserting
        for requirement in reversed(sorted_requirements):
            try:
                # Generate visual element
                visual_element = self._generate_visual_element(requirement)
                generated_elements.append(visual_element)
                
                if visual_element.get('status') == 'success':
                    # Insert into content
                    final_content = self._insert_visual_element(final_content, visual_element)
                else:
                    errors.append(f"Failed to generate {requirement.get('type')}: {visual_element.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"Error processing {requirement.get('type')} requirement: {str(e)}")
                generated_elements.append({
                    'type': requirement.get('type'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'content': final_content,
            'generated_elements': generated_elements,
            'errors': errors
        }
    
    def run(self, blog_post: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to create final layout with visual elements
        
        Args:
            blog_post: Dictionary from content_presenter_agent with:
                {
                    "content": "HTML content from content_editor",
                    "visual_requirements": [List of requirements],
                    ... other fields
                }
        
        Returns:
            Updated blog_post with final content including visual elements
        """
        if 'error' in blog_post:
            return blog_post
        
        content = blog_post.get('content', '')
        visual_requirements = blog_post.get('visual_requirements', [])
        
        if not content:
            return {
                **blog_post,
                'error': 'No content found in blog post'
            }
        
        # Create layout
        layout_result = self.create_layout(content, visual_requirements)
        
        # Update blog post with final content
        updated_blog_post = {
            **blog_post,
            'content': layout_result['content'],
            'visual_elements_generated': layout_result['generated_elements'],
            'layout_errors': layout_result['errors'],
            'layout_completed': True
        }
        
        return updated_blog_post

