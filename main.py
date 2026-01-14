#!/usr/bin/env python3
"""
SEO Content Agentic Workflow - Main Application Entry Point

This is the main entry point for the SEO content creation workflow.
It provides both CLI and web interface access to the agentic workflow.
"""

import argparse
import sys
import webbrowser
import time
import threading
from typing import Dict, Any

from workflow.orchestrator import WorkflowOrchestrator
from interface.app import app
from config import Config

def run_cli_workflow(keyword: str) -> Dict[str, Any]:
    """Run the workflow in CLI mode"""
    
    print(f"[STARTING] SEO Content Workflow for keyword: '{keyword}'")
    print("=" * 60)
    
    orchestrator = WorkflowOrchestrator()
    
    try:
        # Start workflow
        result = orchestrator.start_workflow(keyword)
        
        if result.get('success'):
            print("\n[SUCCESS] Workflow completed successfully!")
            print("\n[INFO] Workflow Summary:")
            print(f"   Keyword: {result['keyword']}")
            print(f"   State: {result['current_state']}")
            
            # Display SERP analysis summary
            serp_data = result['workflow_data'].get('serp_analysis', {})
            if serp_data:
                print(f"\n[INFO] SERP Analysis:")
                print(f"   Pages analyzed: {serp_data.get('total_pages_analyzed', 0)}")
                print(f"   Average word count: {serp_data.get('average_word_count', 0)}")
                print(f"   Common patterns: {', '.join(serp_data.get('common_title_words', [])[:5])}")
            
            # Display content brief summary
            brief_data = result['workflow_data'].get('content_brief', {})
            if brief_data:
                print(f"\n[INFO] Content Brief:")
                print(f"   Target keyword: {brief_data.get('target_keyword', '')}")
                print(f"   Recommended title: {brief_data.get('recommended_title', '')}")
                print(f"   Recommended word count: {brief_data.get('recommended_word_count', 0)}")
                print(f"   LSI keywords: {', '.join(brief_data.get('lsi_keywords', [])[:5])}")
            
            # Display blog post summary
            blog_data = result['workflow_data'].get('blog_post', {})
            if blog_data:
                print(f"\n[INFO] Generated Content:")
                print(f"   Title: {blog_data.get('title', '')}")
                print(f"   Word count: {blog_data.get('seo_analysis', {}).get('word_count', 0)}")
                print(f"   Keyword density: {blog_data.get('seo_analysis', {}).get('keyword_density', 0)}%")
                print(f"   Readability: {blog_data.get('seo_analysis', {}).get('readability', {}).get('score', 'Unknown')}")
                print(f"   SEO score: {blog_data.get('seo_analysis', {}).get('seo_score', 0)}/100")
            
            # Display SEO suggestions
            suggestions = result.get('seo_suggestions', [])
            if suggestions:
                print(f"\n[INFO] SEO Suggestions:")
                for i, suggestion in enumerate(suggestions[:5], 1):
                    print(f"   {i}. {suggestion}")
            
            print(f"\n[INFO] To review and edit the content, visit: http://localhost:3000")
            print(f"[INFO] To publish to WordPress, use the web interface")
            
            return result
            
        else:
            print(f"\n[ERROR] Workflow failed: {result.get('error', 'Unknown error')}")
            if result.get('error_log'):
                print("\nError log:")
                for error in result['error_log']:
                    print(f"   - {error}")
            return result
            
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        return {'success': False, 'error': str(e)}

def run_web_interface():
    """Run the web interface"""
    
    config = Config()
    
    print(f"[INFO] Starting web interface...")
    print(f"   URL: http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"   Debug mode: {config.FLASK_DEBUG}")
    
    # Don't auto-open browser to prevent constant opening issues
    print(f"[INFO] Web interface ready at: http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"[INFO] Open this URL in your browser manually")
    
    # Start Flask app
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='SEO Content Agentic Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --keyword "best SEO tools 2024"     # Run CLI workflow
  python main.py --web                               # Start web interface
  python main.py --keyword "AI content" --web        # Run workflow then start web interface
        """
    )
    
    parser.add_argument(
        '--keyword', '-k',
        type=str,
        help='Target keyword for SEO content creation'
    )
    
    parser.add_argument(
        '--web', '-w',
        action='store_true',
        help='Start web interface'
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run in CLI mode (default if keyword provided)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.keyword and not args.web:
        print("[ERROR] Please provide either --keyword or --web option")
        print("Use --help for more information")
        sys.exit(1)
    
    # Check configuration
    config = Config()
    if not config.OPENAI_API_KEY:
        print("[ERROR] OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in the .env file")
        sys.exit(1)
    
    if not config.SERPAPI_KEY:
        print("[ERROR] SERPAPI_KEY not found in environment variables")
        print("Please set your SerpAPI key in the .env file")
        sys.exit(1)
    
    print("[INFO] SEO Content Agentic Workflow")
    print("=" * 40)
    
    # Run CLI workflow if keyword provided
    if args.keyword:
        result = run_cli_workflow(args.keyword)
        
        # If web interface requested, start it after CLI
        if args.web:
            print("\n" + "=" * 60)
            run_web_interface()
    
    # Run web interface only
    elif args.web:
        run_web_interface()

if __name__ == '__main__':
    main()
