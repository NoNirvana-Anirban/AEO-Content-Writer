import json
import time
from typing import Dict, List, Any, Optional
from agents.serp_research_agent import SERPResearchAgent
from agents.dom_analysis_agent import DOMAnalysisAgent
from agents.content_brief_agent import ContentBriefAgent
from agents.content_writer_agent import ContentWriterAgent
from agents.content_editor_agent import ContentEditorAgent
from agents.content_presenter_agent import ContentPresenterAgent
from agents.layout_agent import LayoutAgent
from agents.seo_optimization_agent import SEOOptimizationAgent

class WorkflowOrchestrator:
    """Orchestrates the entire SEO content creation workflow"""
    
    def __init__(self):
        self.serp_agent = SERPResearchAgent()
        self.dom_analysis_agent = DOMAnalysisAgent()
        self.brief_agent = ContentBriefAgent()
        self.writer_agent = ContentWriterAgent()
        self.editor_agent = ContentEditorAgent()
        self.presenter_agent = ContentPresenterAgent()
        self.layout_agent = LayoutAgent()
        self.seo_optimization_agent = SEOOptimizationAgent()
        
        # Workflow state
        self.current_state = "idle"
        self.workflow_data = {}
        self.error_log = []
        
        # Progress callback
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set the progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, step, percentage, message, agent_output=None):
        """Update progress if callback is set"""
        if self.progress_callback:
            self.progress_callback('running', step, percentage, message, agent_output=agent_output)
    
    def start_workflow(self, keywords: List[str], method: str = 'serpapi', location: Optional[str] = None) -> Dict[str, Any]:
        """Start the complete SEO content creation workflow
        
        Args:
            keywords: List of search keywords
            method: Search method ('serpapi' or 'webbrowse')
            location: Optional location. If not provided and method is 'serpapi', 
                     defaults to United States.
        """
        
        # Ensure keywords is a list
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        
        if not keywords:
            return self._create_error_response("Invalid keywords", {"error": "At least one keyword is required"})
        
        # Format location info for logging
        if location:
            location_info = f" in {location}"
        elif method == 'serpapi':
            location_info = " in United States (default)"
        else:
            location_info = ""
        
        keywords_str = ', '.join(keywords)
        print(f"[INFO] Starting SEO Content Workflow for {len(keywords)} keyword(s): {keywords_str} using {method}{location_info}")
        
        try:
            # Step 1: URL Research (SERP or Web Browse) - Loop through all keywords
            agent_name = "OpenAI Web Search" if method == 'webbrowse' else "SERP API"
            print(f"Step 1: {agent_name}")
            self.current_state = "url_research"
            self._update_progress(agent_name, 10, f"Starting {agent_name} for {len(keywords)} keyword(s){location_info}")
            
            # Choose the appropriate agent based on method
            if method == 'webbrowse':
                from agents.web_browse_agent import WebBrowseAgent
                url_agent = WebBrowseAgent()
            else:
                url_agent = self.serp_agent
            
            # Set progress callback for URL agent
            url_agent.set_progress_callback(lambda msg: self._update_progress(agent_name, 15, msg))
            
            # Collect URLs from all keywords
            all_urls = []
            keyword_urls_map = {}  # Track URLs per keyword for logging
            
            for idx, keyword in enumerate(keywords, 1):
                self._update_progress(agent_name, 10 + (idx * 5 // len(keywords)), 
                                    f"Searching keyword {idx}/{len(keywords)}: {keyword}")
                
                # For SERP API: pass location if provided, otherwise defaults to United States
                # For Web Browse: location is not used
                if method == 'serpapi':
                    keyword_urls = url_agent.run(keyword, location=location)
                else:
                    keyword_urls = url_agent.run(keyword)
                
                # Store top 5 URLs per keyword (agent already returns top 5)
                keyword_urls_map[keyword] = keyword_urls
                all_urls.extend(keyword_urls)
                
                print(f"[INFO] Keyword '{keyword}': Found {len(keyword_urls)} URLs")
            
            # Remove duplicate URLs while preserving order
            seen = set()
            unique_urls = []
            for url in all_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            duplicates_removed = len(all_urls) - len(unique_urls)
            print(f"[INFO] Total URLs collected: {len(all_urls)}, Duplicates removed: {duplicates_removed}, Unique URLs: {len(unique_urls)}")
            
            if not unique_urls:
                error_msg = f"{agent_name} failed: No URLs found for any keyword"
                self.error_log.append(error_msg)
                print(f"[ERROR] {error_msg}")
                print(f"[ERROR] Check console logs above for detailed error information from {agent_name} agent")
                return self._create_error_response(f"{agent_name} failed", {"error": "No URLs found", "method": method, "agent": agent_name})
            
            self.workflow_data['serp_urls'] = unique_urls
            self.workflow_data['keyword_urls_map'] = keyword_urls_map  # Store per-keyword URLs for reference
            self._update_progress(agent_name, 20, f"Found {len(unique_urls)} unique URLs from {len(keywords)} keyword(s) ({duplicates_removed} duplicates removed)")
            
            # Step 2: DOM Analysis
            print("Step 2: DOM Analysis")
            self.current_state = "dom_analysis"
            self._update_progress("DOM Analysis", 25, f"Analyzing DOM content from {len(unique_urls)} unique URLs...")
            
            # Set progress callback for DOM analysis agent
            self.dom_analysis_agent.set_progress_callback(lambda msg: self._update_progress("DOM Analysis", 30, msg))
            
            dom_analysis = self.dom_analysis_agent.run(unique_urls)
            
            if not dom_analysis or (isinstance(dom_analysis, dict) and not dom_analysis.get('major_topics') and not dom_analysis.get('minor_topics')):
                self.error_log.append("DOM Analysis failed: No topics extracted")
                self._update_progress("DOM Analysis", 35, "Warning: Limited topics extracted, continuing with available data...")
            
            self.workflow_data['dom_analysis'] = dom_analysis
            major_topics_count = len(dom_analysis.get('major_topics', []))
            minor_topics_count = len(dom_analysis.get('minor_topics', []))
            self._update_progress("DOM Analysis", 40, f"Extracted {major_topics_count} major topics and {minor_topics_count} minor topics", 
                                 agent_output={'agent_name': 'dom_analysis', 'output': dom_analysis})
            
            # Step 3: Content Brief Creation
            print("Step 3: Content Brief Creation")
            self.current_state = "brief_creation"
            self._update_progress("Content Brief", 45, "Creating content brief from DOM analysis...")
            
            # Prepare inputs for content brief agent
            keywords_string = ', '.join(keywords)
            
            content_brief = self.brief_agent.run(
                keywords=keywords_string,
                location=location,
                dom_analysis=dom_analysis
            )
            
            if 'error' in content_brief:
                self.error_log.append(f"Content Brief failed: {content_brief['error']}")
                return self._create_error_response("Content Brief failed", content_brief)
            
            self.workflow_data['content_brief'] = content_brief
            self._update_progress("Content Brief", 50, "Content brief created with topic analysis and structure...",
                                 agent_output={'agent_name': 'content_brief', 'output': content_brief})
            
            # Step 4: Content Writing
            print("Step 4: Content Writing")
            self.current_state = "content_writing"
            self._update_progress("AI Writing", 55, "Generating SEO-optimized content with AI...")
            
            blog_post = self.writer_agent.run(content_brief)
            
            if 'error' in blog_post:
                self.error_log.append(f"Content Writing failed: {blog_post['error']}")
                return self._create_error_response("Content Writing failed", blog_post)
            
            self.workflow_data['blog_post'] = blog_post
            content = blog_post.get('content', '')
            word_count = len(content.split()) if content else 0
            self._update_progress("AI Writing", 70, f"Content generated successfully! Word count: {word_count}",
                                 agent_output={'agent_name': 'content_writer', 'output': blog_post})
            
            # Step 4.5: Content Editing
            print("Step 4.5: Content Editing")
            self.current_state = "content_editing"
            self._update_progress("Content Editor", 72, "Editing content to match tone guidelines...")
            
            edited_blog_post = self.editor_agent.run(blog_post)
            
            if 'error' in edited_blog_post:
                self.error_log.append(f"Content Editing failed: {edited_blog_post['error']}")
                # Continue with original content if editing fails
                self._update_progress("Content Editor", 75, "Content editing skipped due to error, using original content")
            else:
                blog_post = edited_blog_post  # Update blog_post to edited version
                self.workflow_data['blog_post'] = edited_blog_post
                self._update_progress("Content Editor", 75, "Content edited to match tone guidelines",
                                     agent_output={'agent_name': 'content_editor', 'output': edited_blog_post})
            
            # Step 4.6: Content Presentation Analysis
            print("Step 4.6: Content Presentation Analysis")
            self.current_state = "content_presentation"
            self._update_progress("Content Presenter", 77, "Analyzing content for visual element requirements...")
            
            blog_post_with_requirements = self.presenter_agent.run(blog_post)
            
            if 'error' in blog_post_with_requirements:
                self.error_log.append(f"Content Presentation Analysis failed: {blog_post_with_requirements['error']}")
                # Continue without visual requirements if analysis fails
                self._update_progress("Content Presenter", 78, "Visual requirements analysis skipped")
            else:
                blog_post = blog_post_with_requirements  # Update blog_post with requirements
                self.workflow_data['blog_post'] = blog_post_with_requirements
                requirements_count = len(blog_post_with_requirements.get('visual_requirements', []))
                self._update_progress("Content Presenter", 78, f"Created {requirements_count} visual element requirements",
                                     agent_output={'agent_name': 'content_presenter', 'output': blog_post_with_requirements})
            
            # Step 4.7: Layout Creation (Generate and Place Visual Elements)
            print("Step 4.7: Layout Creation")
            self.current_state = "layout_creation"
            self._update_progress("Layout Agent", 79, "Generating visual elements and creating final layout...")
            
            final_blog_post = self.layout_agent.run(blog_post)
            
            if 'error' in final_blog_post:
                self.error_log.append(f"Layout creation failed: {final_blog_post['error']}")
                # Continue with content without visuals if layout fails
                self._update_progress("Layout Agent", 80, "Layout creation skipped, using content without visuals")
            else:
                blog_post = final_blog_post  # Update blog_post with final layout
                self.workflow_data['blog_post'] = final_blog_post
                generated_count = len([e for e in final_blog_post.get('visual_elements_generated', []) if e.get('status') == 'success'])
                total_requirements = len(blog_post.get('visual_requirements', []))
                self._update_progress("Layout Agent", 80, f"Layout completed: {generated_count}/{total_requirements} visual elements generated",
                                     agent_output={'agent_name': 'layout_agent', 'output': final_blog_post})
            
            # Step 4.8: SEO Optimization (Title, Meta, Slug, Schemas, OG Tags)
            print("Step 4.8: SEO Optimization")
            self.current_state = "seo_optimization"
            self._update_progress("SEO Optimization", 82, "Optimizing SEO elements: title, meta, slug, schemas, OG tags...")
            
            seo_optimization = self.seo_optimization_agent.run(content_brief, blog_post)
            
            if 'error' in seo_optimization:
                self.error_log.append(f"SEO Optimization failed: {seo_optimization['error']}")
                self._update_progress("SEO Optimization", 83, "SEO optimization skipped due to error")
            else:
                self.workflow_data['seo_optimization'] = seo_optimization
                # Update blog_post with optimized title and meta
                blog_post['title'] = seo_optimization.get('title', blog_post.get('title', ''))
                blog_post['meta_title'] = seo_optimization.get('meta_title', blog_post.get('meta_title', ''))
                blog_post['meta_description'] = seo_optimization.get('meta_description', blog_post.get('meta_description', ''))
                self.workflow_data['blog_post'] = blog_post
                self._update_progress("SEO Optimization", 83, f"SEO optimization completed: slug generated, {len(seo_optimization.get('og_tags', {}))} OG tags, schemas created",
                                     agent_output={'agent_name': 'seo_optimization', 'output': seo_optimization})
            
            # Step 5: Prepare for Review
            print("Step 5: Preparing for Review")
            self.current_state = "ready_for_review"
            self._update_progress("Finalizing", 90, "Preparing content for review and editing...")
            
            workflow_result = {
                'success': True,
                'keyword': keyword,
                'current_state': self.current_state,
                'workflow_data': self.workflow_data,
                'message': 'Workflow completed successfully. Ready for review.'
            }
            
            print("[SUCCESS] Workflow completed successfully")
            return workflow_result
            
        except Exception as e:
            error_msg = f"Workflow failed at step: {self.current_state}, Error: {str(e)}"
            self.error_log.append(error_msg)
            print(f"[ERROR] {error_msg}")
            
            return self._create_error_response("Workflow failed", {'error': str(e)})
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        
        return {
            'current_state': self.current_state,
            'workflow_data_keys': list(self.workflow_data.keys()),
            'error_log': self.error_log,
            'has_serp_data': 'serp_urls' in self.workflow_data,
            'has_dom_analysis': 'dom_analysis' in self.workflow_data,
            'has_brief': 'content_brief' in self.workflow_data,
            'has_content': 'blog_post' in self.workflow_data,
            'has_seo_analysis': 'seo_analysis' in self.workflow_data
        }
    
    def _create_error_response(self, message: str, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized error response"""
        
        return {
            'success': False,
            'error': message,
            'error_data': error_data,
            'current_state': self.current_state,
            'workflow_data': self.workflow_data,
            'error_log': self.error_log
        }
    
    def reset_workflow(self):
        """Reset workflow state"""
        
        self.current_state = "idle"
        self.workflow_data = {}
        self.error_log = []
        print("[INFO] Workflow reset")
