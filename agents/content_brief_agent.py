import json
from typing import Dict, List, Any
from config import Config
import requests

class ContentBriefAgent:
    """Agent responsible for creating structured content briefs from DOM analysis"""
    
    def __init__(self, model: str = "openai/gpt-4o"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def create_content_brief(self, keywords: str, location: str = None, dom_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate content brief from DOM analysis
        
        Args:
            keywords: Comma-separated keywords string (e.g., "keyword1, keyword2")
            location: Optional location string (e.g., "United States")
            dom_analysis: Output from dom_analysis_agent.py with structure:
                {
                    "major_topics": List[Dict[str, Any]],  # Each dict: {"name": str, "subtopics": List[str]}
                    "minor_topics": List[Dict[str, Any]]   # Each dict: {"name": str, "subtopics": List[str]}
                }
        """
        
        if dom_analysis is None:
            return {'error': 'DOM analysis data is required'}
        
        if 'error' in dom_analysis:
            return dom_analysis
        
        # Process keywords
        if isinstance(keywords, str):
            keyword_list = [k.strip() for k in keywords.split(',')]
            keyword_string = keywords
        else:
            keyword_list = keywords if isinstance(keywords, list) else []
            keyword_string = ', '.join(keyword_list)
        
        # Get major/minor topics from DOM analysis
        # Structure: List[Dict[str, Any]] where each dict has {"name": str, "subtopics": List[str]}
        major_topics = dom_analysis.get('major_topics', [])
        minor_topics = dom_analysis.get('minor_topics', [])
        
        # Format major/minor topics with subtopics (matching dom_analysis_agent output structure)
        major_topics_text = "\n".join([
            f"  - {topic.get('name', '')}: {', '.join(topic.get('subtopics', [])[:3])}..." 
            if topic.get('subtopics') else f"  - {topic.get('name', '')}"
            for topic in major_topics[:10]
        ]) if major_topics else "  - None"
        
        minor_topics_text = "\n".join([
            f"  - {topic.get('name', '')}: {', '.join(topic.get('subtopics', [])[:3])}..." 
            if topic.get('subtopics') else f"  - {topic.get('name', '')}"
            for topic in minor_topics[:10]
        ]) if minor_topics else "  - None"
        
        # Build location context if provided
        location_context = f"\n        Target Location: {location}" if location else ""
        
        topics_section = f"""
        DOM Analysis Results:
        
        MAJOR TOPICS (Core themes - prioritize these):
        {major_topics_text}
        
        MINOR TOPICS (Supporting themes):
        {minor_topics_text}
        
        IMPORTANT: 
        - The "topics_to_cover" in your response MUST prioritize all major topics first, then include relevant minor topics.
        - Use the subtopics as guidance for what specific points to cover under each major/minor topic.
        - These topics were extracted from actual competitor content analysis using web search via OpenRouter and represent what successful pages are covering.
        - Create a heading structure that aligns with these major topics.
        - Each topic has subtopics that provide specific details to cover in that section.
            """
        
        # Create prompt for content brief generation
        prompt = f"""
        Based on the following analysis for the keywords "{keyword_string}", create a comprehensive content brief for an SEO-optimized blog post.{location_context}

        {topics_section}

        Please create a content brief that includes:
        1. Target keyword and 5-7 LSI keywords
        2. Recommended title (H1) that's SEO-optimized and should be used only once in the content.
        3. Meta title (MAXIMUM 60 characters) and meta description (MAXIMUM 150 characters) templates
        4. Suggested heading structure (H2, H3, H4) based on the topics identified
        5. Topics to cover - prioritize major topics first, then include relevant minor topics
        6. Recommended word count
        7. Schema markup recommendations

        Return the response as a JSON object with the following structure:
        {{
            "target_keyword": "string",
            "lsi_keywords": ["string1", "string2", ...],
            "recommended_title": "string",
            "meta_title": "string (MAX 60 characters)",
            "meta_description": "string (MAX 150 characters)",
            "heading_structure": [
                {{"level": "H1", "title": "string", "description": "string"}}
                {{"level": "H2", "title": "string", "description": "string"}},
                {{"level": "H3", "title": "string", "description": "string"}},
                ...
            ],
            "H1_count":1,
            "topics_to_cover": ["topic1", "topic2", ...],
            "recommended_word_count": number,
            "schema_markup": "string",
            "content_angle": "string",
            "target_audience": "string"
        }}
        """
        
        try:
            # Prepare request payload for OpenRouter API
            payload = {
                "model": self.model,  # "openai/gpt-4o"
                "messages": [
                    {"role": "system", "content": "You are an expert SEO content strategist. Create detailed, actionable content briefs based on DOM analysis."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            # Make direct HTTP request to OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # Optional: for OpenRouter analytics
                "X-Title": "Content Brief Agent"  # Optional: for OpenRouter analytics
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            content_brief = json.loads(response_data["choices"][0]["message"]["content"])
            
            # Validate and fix H1 handling
            heading_structure = content_brief.get('heading_structure', [])
            recommended_title = content_brief.get('recommended_title', '')
            
            # Find all H1 items
            h1_items = [h for h in heading_structure if h.get('level', '').upper() == 'H1']
            
            # Ensure exactly one H1
            if len(h1_items) == 0:
                # No H1 found, add one at the beginning using recommended_title
                if recommended_title:
                    h1_item = {"level": "H1", "title": recommended_title, "description": "Main heading for the article"}
                    content_brief['heading_structure'] = [h1_item] + heading_structure
                else:
                    # Create default H1 if no recommended_title
                    h1_item = {"level": "H1", "title": keyword_string.title(), "description": "Main heading for the article"}
                    content_brief['heading_structure'] = [h1_item] + heading_structure
                    content_brief['recommended_title'] = keyword_string.title()
            elif len(h1_items) > 1:
                # Multiple H1s found, keep only the first one
                first_h1_index = next(i for i, h in enumerate(heading_structure) if h.get('level', '').upper() == 'H1')
                first_h1 = heading_structure[first_h1_index]
                
                # Remove all H1s and re-add only the first one at the beginning
                content_brief['heading_structure'] = [
                    h for h in heading_structure if h.get('level', '').upper() != 'H1'
                ]
                content_brief['heading_structure'].insert(0, first_h1)
                h1_items = [first_h1]
            else:
                # Exactly one H1 exists
                h1_item = h1_items[0]
                
                # Ensure H1 is first in heading_structure
                if heading_structure[0] != h1_item:
                    # Move H1 to the beginning
                    content_brief['heading_structure'] = [
                        h for h in heading_structure if h != h1_item
                    ]
                    content_brief['heading_structure'].insert(0, h1_item)
            
            # Ensure H1 title matches recommended_title
            if recommended_title and content_brief['heading_structure']:
                content_brief['heading_structure'][0]['title'] = recommended_title
                content_brief['heading_structure'][0]['level'] = 'H1'
            
            # Set H1_count to 1
            content_brief['H1_count'] = 1
            
            # Validate and truncate meta_title (max 60 characters)
            meta_title = content_brief.get('meta_title', '')
            if meta_title:
                if len(meta_title) > 60:
                    content_brief['meta_title'] = meta_title[:57] + '...'
                else:
                    content_brief['meta_title'] = meta_title
            else:
                # Generate default if missing
                content_brief['meta_title'] = recommended_title[:60] if recommended_title else keyword_string[:60]
            
            # Validate and truncate meta_description (max 150 characters)
            meta_description = content_brief.get('meta_description', '')
            if meta_description:
                if len(meta_description) > 150:
                    content_brief['meta_description'] = meta_description[:147] + '...'
                else:
                    content_brief['meta_description'] = meta_description
            else:
                # Generate default if missing
                content_brief['meta_description'] = f"Discover {keyword_string}. Expert insights and comprehensive guide."[:150]
            
            # Add metadata
            content_brief['dom_analysis_summary'] = {
                'major_topics_count': len(major_topics),
                'minor_topics_count': len(minor_topics),
                'major_topics': major_topics,
                'minor_topics': minor_topics
            }
            
            # Add input metadata
            content_brief['input_metadata'] = {
                'keywords': keyword_string,
                'location': location,
                'keywords_list': keyword_list
            }
            
            return content_brief
            
        except Exception as e:
            print(f"Error creating content brief: {e}")
            # Generate fallback values with proper character limits
            fallback_title = f"Best {keyword_string.title()} - Complete Guide"
            fallback_meta_title = f"Best {keyword_string.title()} - Guide"[:60]
            fallback_meta_description = f"Discover the best {keyword_string} with our comprehensive guide. Expert recommendations and tips."[:150]
            
            return {
                'error': str(e),
                'target_keyword': keyword_string,
                'recommended_title': fallback_title,
                'meta_title': fallback_meta_title,
                'meta_description': fallback_meta_description,
                'recommended_word_count': 2000,
                'heading_structure': [
                    {"level": "H2", "title": f"Top {keyword_string.title()}", "description": "Best options and recommendations"},
                    {"level": "H2", "title": f"How to Choose the Best {keyword_string.title()}", "description": "Selection criteria and tips"},
                    {"level": "H2", "title": f"Benefits of {keyword_string.title()}", "description": "Key advantages and benefits"},
                    {"level": "H2", "title": "Conclusion", "description": "Summary and next steps"}
                ],
                'topics_to_cover': [f"Best {keyword_string}", f"How to choose {keyword_string}", f"Benefits of {keyword_string}"],
                'lsi_keywords': [keyword_string, f"best {keyword_string}", f"top {keyword_string}", f"{keyword_string} guide"],
                'internal_linking_opportunities': [],
                'call_to_action_suggestions': ["Learn more", "Get started", "Contact us"],
                'schema_markup': "Article",
                'content_angle': f"Comprehensive guide to the best {keyword_string}",
                'target_audience': f"People looking for the best {keyword_string}"
            }
    
    def enhance_brief_with_competitor_analysis(self, content_brief: Dict[str, Any], dom_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance content brief with competitor analysis insights from DOM analysis"""
        
        if 'error' in content_brief:
            return content_brief
        
        # Get major/minor topics from DOM analysis
        # Structure: List[Dict[str, Any]] where each dict has {"name": str, "subtopics": List[str]}
        major_topics = dom_analysis.get('major_topics', [])
        minor_topics = dom_analysis.get('minor_topics', [])
        
        competitor_analysis = {
            'major_topics': major_topics,
            'minor_topics': minor_topics,
            'content_gaps': [],
            'improvement_opportunities': []
        }
        
        # Add competitor analysis to brief
        content_brief['competitor_analysis'] = competitor_analysis
        
        return content_brief
    
    def run(self, keywords: str, location: str = None, dom_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main method to run content brief creation
        
        Args:
            keywords: Comma-separated keywords string (e.g., "keyword1, keyword2")
            location: Optional location string (e.g., "United States")
            dom_analysis: Output from dom_analysis_agent.py with structure:
                {
                    "major_topics": List[Dict[str, Any]],  # Each dict: {"name": str, "subtopics": List[str]}
                    "minor_topics": List[Dict[str, Any]]   # Each dict: {"name": str, "subtopics": List[str]}
                }
        """
        print("[INFO] Creating content brief from DOM analysis (major/minor topics format)...")
        
        # Create initial brief
        content_brief = self.create_content_brief(keywords, location, dom_analysis)
        
        # Enhance with competitor analysis
        enhanced_brief = self.enhance_brief_with_competitor_analysis(content_brief, dom_analysis)
        
        print("[SUCCESS] Content brief created successfully")
        
        # Log sample output
        print("\n" + "="*80)
        print("[SAMPLE OUTPUT - ContentBriefAgent]")
        print("="*80)
        print(f"Return type: Dict[str, Any]")
        print(f"Target keyword: {enhanced_brief.get('target_keyword', 'N/A')}")
        print(f"Recommended title: {enhanced_brief.get('recommended_title', 'N/A')[:80]}...")
        print(f"Topics to cover: {len(enhanced_brief.get('topics_to_cover', []))} topics")
        print(f"LSI keywords: {enhanced_brief.get('lsi_keywords', [])[:5]}")
        print(f"Recommended word count: {enhanced_brief.get('recommended_word_count', 'N/A')}")
        print(f"Sample heading structure (first 3):")
        for h in enhanced_brief.get('heading_structure', [])[:3]:
            print(f"  - {h.get('level', 'N/A')}: {h.get('title', 'N/A')[:60]}")
        print("="*80 + "\n")
        
        return enhanced_brief
