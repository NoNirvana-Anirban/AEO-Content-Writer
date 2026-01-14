import json
import re
from typing import Dict, List, Any
from config import Config
import requests

class SEOOptimizationAgent:
    """Agent responsible for SEO optimization: title, meta description, slug, schemas, and OG tags"""
    
    def __init__(self, model: str = "openai/gpt-4o"):
        self.config = Config()
        self.model = model
        self.api_url = f"{self.config.OPENROUTER_BASE_URL}/chat/completions"
        self.api_key = self.config.OPENROUTER_API_KEY
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title
        
        Args:
            title: Article title
            
        Returns:
            URL-friendly slug (lowercase, no articles, spaces replaced with hyphens)
        """
        if not title:
            return ""
        
        # Remove articles (a, an, the) at the beginning
        title_lower = title.lower().strip()
        articles = ['a ', 'an ', 'the ']
        for article in articles:
            if title_lower.startswith(article):
                title_lower = title_lower[len(article):].strip()
        
        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^\w\s-]', '', title_lower)  # Remove special chars
        slug = re.sub(r'[-\s]+', '-', slug)  # Replace spaces and multiple hyphens with single hyphen
        slug = slug.strip('-')  # Remove leading/trailing hyphens
        
        return slug
    
    def _extract_faqs_from_content(self, content: str) -> List[Dict[str, str]]:
        """Extract FAQs from content by looking for question-answer patterns
        
        Args:
            content: HTML content string
            
        Returns:
            List of FAQ dictionaries with 'question' and 'answer' keys
        """
        faqs = []
        
        # Remove HTML tags for text analysis
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = ' '.join(text_content.split())
        
        # Look for FAQ patterns:
        # 1. Questions followed by answers (Q: ... A: ...)
        qa_pattern = re.compile(r'(?:Q|Question)[:\s]+(.+?)(?:A|Answer)[:\s]+(.+?)(?=(?:Q|Question)[:\s]|$)', re.IGNORECASE | re.DOTALL)
        matches = qa_pattern.findall(text_content)
        for match in matches:
            question = match[0].strip()[:200]
            answer = match[1].strip()[:500]
            if question and answer and len(question) > 10:
                faqs.append({'question': question, 'answer': answer})
        
        # 2. H3/H4 headings that look like questions followed by paragraphs
        question_heading_pattern = re.compile(r'<h[34][^>]*>(.+?\?)</h[34]>', re.IGNORECASE)
        question_headings = question_heading_pattern.findall(content)
        
        for question in question_headings:
            # Find the answer (next paragraph or list after the heading)
            question_escaped = re.escape(question)
            answer_pattern = re.compile(
                rf'<h[34][^>]*>{question_escaped}</h[34]>(.+?)(?=<h[1-4]|$)',
                re.IGNORECASE | re.DOTALL
            )
            answer_match = answer_pattern.search(content)
            if answer_match:
                answer_html = answer_match.group(1)
                # Extract text from answer
                answer_text = re.sub(r'<[^>]+>', ' ', answer_html)
                answer_text = ' '.join(answer_text.split())[:500]
                if answer_text and len(answer_text) > 20:
                    faqs.append({'question': question.strip()[:200], 'answer': answer_text})
        
        return faqs[:10]  # Limit to 10 FAQs
    
    def _generate_article_schema(self, blog_post: Dict[str, Any], content_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Article schema (JSON-LD) with detailed entities
        
        Args:
            blog_post: Blog post dictionary with title, content, etc.
            content_brief: Content brief with keywords, target audience, etc.
            
        Returns:
            Article schema as dictionary
        """
        title = blog_post.get('title', '')
        content = blog_post.get('content', '')
        meta_description = blog_post.get('meta_description', '')
        
        # Extract text content for description
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = ' '.join(text_content.split())
        description = meta_description or text_content[:300] if text_content else ''
        
        # Extract author and date if available
        author = content_brief.get('target_audience', 'Content Team')
        published_date = content_brief.get('published_date', '')
        
        # Build article schema
        # NOTE: Image attribute removed to prevent base64 URLs in schemas (causes 413 errors)
        article_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "author": {
                "@type": "Organization",
                "name": author
            },
            "publisher": {
                "@type": "Organization",
                "name": author
            }
        }
        
        if published_date:
            article_schema["datePublished"] = published_date
            article_schema["dateModified"] = published_date
        
        # Add keywords if available
        keywords = content_brief.get('lsi_keywords', [])
        if keywords:
            article_schema["keywords"] = ', '.join(keywords[:10])
        
        # Add mainEntityOfPage
        article_schema["mainEntityOfPage"] = {
            "@type": "WebPage",
            "@id": "#webpage"
        }
        
        return article_schema
    
    def _generate_faq_schema(self, faqs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate FAQPage schema from FAQs
        
        Args:
            faqs: List of FAQ dictionaries with 'question' and 'answer'
            
        Returns:
            FAQPage schema as dictionary
        """
        if not faqs:
            return None
        
        faq_items = []
        for faq in faqs:
            faq_items.append({
                "@type": "Question",
                "name": faq.get('question', ''),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq.get('answer', '')
                }
            })
        
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_items
        }
        
        return faq_schema
    
    def _generate_og_tags(self, blog_post: Dict[str, Any], slug: str) -> Dict[str, str]:
        """Generate Open Graph meta tags
        
        Args:
            blog_post: Blog post dictionary
            slug: URL slug for the article
            
        Returns:
            Dictionary of OG tag key-value pairs
        """
        title = blog_post.get('title', '')
        meta_description = blog_post.get('meta_description', '')
        content = blog_post.get('content', '')
        
        # Extract first image from content
        image_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
        images = image_pattern.findall(content)
        og_image = images[0] if images else ''
        
        # Build site URL (you may want to make this configurable)
        site_url = getattr(self.config, 'SITE_URL', 'https://example.com')
        og_url = f"{site_url}/{slug}" if slug else site_url
        
        og_tags = {
            "og:title": title[:60],
            "og:description": meta_description[:200] if meta_description else '',
            "og:type": "article",
            "og:url": og_url
        }
        
        if og_image:
            # Convert relative URLs to absolute
            if og_image.startswith('data:'):
                og_tags["og:image"] = og_image
            elif og_image.startswith('http'):
                og_tags["og:image"] = og_image
            else:
                og_tags["og:image"] = f"{site_url}{og_image}"
        
        # Add additional OG tags
        og_tags["og:site_name"] = getattr(self.config, 'SITE_NAME', 'Content Site')
        
        return og_tags
    
    def _optimize_title_and_meta(self, content_brief: Dict[str, Any], blog_post: Dict[str, Any]) -> Dict[str, str]:
        """Optimize title and meta description using AI to ensure character limits
        
        Args:
            content_brief: Content brief with original title and meta
            blog_post: Blog post with content
            
        Returns:
            Dictionary with optimized 'title' and 'meta_description'
        """
        original_title = content_brief.get('recommended_title', blog_post.get('title', ''))
        original_meta = content_brief.get('meta_description', blog_post.get('meta_description', ''))
        content = blog_post.get('content', '')
        
        # Extract text content for context
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = ' '.join(text_content.split())[:1000]  # First 1000 chars for context
        
        prompt = f"""Optimize the following title and meta description for SEO while ensuring strict character limits:

Original Title: {original_title}
Current Title Length: {len(original_title)} characters
REQUIRED: Title must be MAXIMUM 60 characters

Original Meta Description: {original_meta}
Current Meta Description Length: {len(original_meta)} characters
REQUIRED: Meta Description must be MAXIMUM 150 characters

Content Preview (for context):
{text_content}

Please optimize both the title and meta description to:
1. Be compelling and SEO-friendly
2. Include primary keywords naturally
3. Stay within the strict character limits (title: 60 chars max, meta: 150 chars max)
4. Be clear and descriptive

Return a JSON object with this structure:
{{
    "title": "Optimized title (MAX 60 characters)",
    "meta_description": "Optimized meta description (MAX 150 characters)"
}}

Return ONLY valid JSON, no other text."""

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert SEO specialist. Optimize titles and meta descriptions to be compelling, keyword-rich, and within strict character limits."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "SEO Optimization Agent"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            response_data = response.json()
            optimized = json.loads(response_data["choices"][0]["message"]["content"])
            
            # Ensure strict character limits
            title = optimized.get('title', original_title)
            meta_description = optimized.get('meta_description', original_meta)
            
            # Enforce limits
            if len(title) > 60:
                title = title[:57] + '...'
            if len(meta_description) > 150:
                meta_description = meta_description[:147] + '...'
            
            return {
                'title': title,
                'meta_description': meta_description
            }
            
        except Exception as e:
            print(f"Error optimizing title/meta with AI: {e}")
            # Fallback: manual truncation
            title = original_title[:60] if len(original_title) > 60 else original_title
            meta_description = original_meta[:150] if len(original_meta) > 150 else original_meta
            return {
                'title': title,
                'meta_description': meta_description
            }
    
    def run(self, content_brief: Dict[str, Any], blog_post: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to perform SEO optimization
        
        Args:
            content_brief: Content brief from content_brief_agent
            blog_post: Final blog post from layout_agent
            
        Returns:
            Dictionary with SEO optimization data:
            {
                "title": str (optimized, max 60 chars),
                "meta_description": str (optimized, max 150 chars),
                "slug": str (URL-friendly),
                "article_schema": dict (JSON-LD),
                "faq_schema": dict (JSON-LD) or None,
                "og_tags": dict (Open Graph tags)
            }
        """
        if 'error' in blog_post:
            return {
                'error': 'Cannot optimize SEO: blog post has errors',
                **blog_post
            }
        
        if 'error' in content_brief:
            return {
                'error': 'Cannot optimize SEO: content brief has errors',
                **blog_post
            }
        
        try:
            # 1. Optimize title and meta description
            # Use title from blog_post if available, otherwise from content_brief
            current_title = blog_post.get('title') or content_brief.get('recommended_title', '')
            current_meta = blog_post.get('meta_description') or content_brief.get('meta_description', '')
            
            # Update blog_post temporarily for optimization
            temp_blog_post = {**blog_post, 'title': current_title, 'meta_description': current_meta}
            optimized = self._optimize_title_and_meta(content_brief, temp_blog_post)
            title = optimized['title']
            meta_description = optimized['meta_description']
            
            # 2. Generate slug from title
            slug = self._generate_slug(title)
            
            # 3. Generate article schema
            article_schema = self._generate_article_schema(blog_post, content_brief)
            
            # 4. Extract FAQs and generate FAQ schema if present
            content = blog_post.get('content', '')
            faqs = self._extract_faqs_from_content(content)
            faq_schema = self._generate_faq_schema(faqs) if faqs else None
            
            # 5. Generate OG tags
            og_tags = self._generate_og_tags(blog_post, slug)
            
            seo_data = {
                'title': title,
                'meta_title': title,  # Alias for compatibility
                'meta_description': meta_description,
                'slug': slug,
                'article_schema': article_schema,
                'faq_schema': faq_schema,
                'og_tags': og_tags,
                'faqs_detected': len(faqs) if faqs else 0
            }
            
            return seo_data
            
        except Exception as e:
            print(f"Error in SEO optimization: {e}")
            return {
                'error': f'SEO optimization failed: {str(e)}',
                'title': blog_post.get('title', '')[:60],
                'meta_description': blog_post.get('meta_description', '')[:150],
                'slug': self._generate_slug(blog_post.get('title', '')),
                'article_schema': {},
                'faq_schema': None,
                'og_tags': {}
            }

