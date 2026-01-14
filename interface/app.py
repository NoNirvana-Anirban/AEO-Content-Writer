from flask import Flask, render_template, request, jsonify, session, Response
import json
import time
import threading
from typing import Dict, Any
from workflow.orchestrator import WorkflowOrchestrator
from config import Config

app = Flask(__name__)
app.secret_key = 'seo-content-workflow-secret-key'

# Global orchestrator instance
orchestrator = WorkflowOrchestrator()
config = Config()

# Global progress tracking
progress_data = {
    'status': 'idle',
    'current_step': '',
    'progress_percentage': 0,
    'messages': [],
    'error': None,
    'agent_outputs': {}  # Store outputs from each agent
}
progress_lock = threading.Lock()

# Global workflow result data
workflow_result_data = {'keyword': '', 'workflow_data': None}

# Global variable to store pending WordPress content for MCP call
pending_wordpress_content = {}

# Global variable to store completed WordPress posts
completed_wordpress_posts = {
    'id': 1290,
    'title': 'Proper MCP Integration Test',
    'status': 'draft',
    'url': 'https://nonirvanadigital.com/?p=1290',
    'edit_url': 'https://nonirvanadigital.com/wp-admin/post.php?post=1290&action=edit',
    'slug': 'proper-mcp-integration-test',
    'created': '2025-10-22T15:00:54'
}

@app.route('/test')
def test():
    """Test endpoint to verify the app is working"""
    return jsonify({'status': 'ok', 'message': 'Flask app is working'})

@app.route('/')
def index():
    """Main page with keyword input"""
    return render_template('index.html')

@app.route('/progress')
def progress():
    """Server-Sent Events endpoint for real-time progress updates"""
    def generate():
        while True:
            with progress_lock:
                data = progress_data.copy()
            
            # Format as SSE
            yield f"data: {json.dumps(data)}\n\n"
            
            # If workflow is complete or failed, break the loop
            if data['status'] in ['completed', 'failed']:
                break
                
            time.sleep(0.5)  # Update every 500ms
    
    return Response(generate(), mimetype='text/event-stream')

def update_progress(status, step, percentage, message=None, error=None, agent_output=None):
    """Update progress data"""
    with progress_lock:
        progress_data['status'] = status
        progress_data['current_step'] = step
        progress_data['progress_percentage'] = percentage
        if message:
            progress_data['messages'].append({
                'timestamp': time.time(),
                'message': message
            })
        if error:
            progress_data['error'] = error
        if agent_output:
            # Store agent output with agent name as key
            agent_name = agent_output.get('agent_name', 'unknown')
            progress_data['agent_outputs'][agent_name] = agent_output.get('output', {})

@app.route('/start-workflow', methods=['POST'])
def start_workflow():
    """Start the SEO content workflow"""
    try:
        data = request.get_json()
        # Support both single keyword (backward compatibility) and keywords array
        keywords = data.get('keywords', [])
        keyword = data.get('keyword', '').strip()  # Backward compatibility
        
        # If keywords array is provided, use it; otherwise parse single keyword
        if keywords and isinstance(keywords, list):
            keywords = [k.strip() for k in keywords if k.strip()]
        elif keyword:
            # Parse comma-separated keywords
            keywords = [k.strip() for k in keyword.split(',') if k.strip()]
        else:
            return jsonify({'error': 'At least one keyword is required'}), 400
        
        if not keywords:
            return jsonify({'error': 'At least one keyword is required'}), 400
        
        method = data.get('method', 'serpapi')  # Default to serpapi
        location = data.get('location', '')  # Optional location
        location_id = data.get('location_id', '')  # Optional location ID
        
        # Reset progress
        with progress_lock:
            progress_data['status'] = 'running'
            progress_data['current_step'] = f'Starting workflow with {method}'
            progress_data['progress_percentage'] = 0
            progress_data['messages'] = []
            progress_data['error'] = None
            progress_data['agent_outputs'] = {}  # Reset agent outputs
        
        # Store workflow data globally for session handling
        global workflow_result_data
        workflow_result_data = {
            'keywords': keywords,
            'keyword': ', '.join(keywords),  # For backward compatibility
            'workflow_data': None, 
            'method': method,
            'location': location if location else None,
            'location_id': location_id if location_id else None
        }
        
        # Start workflow in a separate thread
        def run_workflow():
            try:
                # Set progress callback
                orchestrator.set_progress_callback(update_progress)
                
                # Pass keywords list and location if provided
                result = orchestrator.start_workflow(keywords, method, location=location if location else None)
                
                if result.get('success'):
                    workflow_result_data['workflow_data'] = result['workflow_data']
                    update_progress('completed', 'Workflow completed', 100, 'Workflow completed successfully!')
                else:
                    update_progress('failed', 'Workflow failed', 0, error=result.get('error', 'Unknown error'))
            except Exception as e:
                update_progress('failed', 'Workflow failed', 0, error=str(e))
        
        # Start workflow in background
        thread = threading.Thread(target=run_workflow)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': f'Workflow started with {method}'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update-content', methods=['POST'])
def update_content_endpoint():
    """Update content during review with AI assistance"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        current_content = data.get('content', '')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not current_content:
            return jsonify({'error': 'No content found to edit'}), 400
        
        # Simple AI response for now - you can integrate with OpenAI API here
        ai_response = f"I understand you want to: {user_message}. Here's my suggestion: Consider improving the content structure and adding more relevant keywords."
        
        return jsonify({
            'success': True,
            'ai_response': ai_response,
            'updated_content': {
                'content': current_content  # For now, return the same content
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/review')
def review():
    """Review page with content editing interface"""
    global workflow_result_data
    
    workflow_data = workflow_result_data.get('workflow_data')
    keyword = workflow_result_data.get('keyword')
    
    if not workflow_data:
        return render_template('index.html', error='No workflow data found. Please start a new workflow.')
    
    return render_template('review.html', 
                         workflow_data=workflow_data, 
                         keyword=keyword)


@app.route('/chat-edit', methods=['POST'])
def chat_edit():
    """Handle chat-based content editing"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get current content
        workflow_data = session.get('workflow_data', {})
        blog_post = workflow_data.get('blog_post', {})
        
        if not blog_post:
            return jsonify({'error': 'No content found to edit'}), 400
        
        # Process edit request with AI
        edit_result = process_chat_edit(user_message, blog_post)
        
        if edit_result.get('success'):
            # Update content
            updated_content = edit_result.get('updated_content', {})
            result = orchestrator.update_content(updated_content)
            
            if result.get('success'):
                session['workflow_data']['blog_post'].update(updated_content)
                session['workflow_data']['seo_analysis'] = result['seo_analysis']
                
                return jsonify({
                    'success': True,
                    'updated_content': updated_content,
                    'seo_analysis': result['seo_analysis'],
                    'ai_response': edit_result.get('ai_response', ''),
                    'message': 'Content updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to update content')
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': edit_result.get('error', 'Failed to process edit request')
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/publish', methods=['POST'])
def publish():
    """Publish content to WordPress"""
    try:
        # Publish to WordPress
        result = orchestrator.publish_to_wordpress()
        
        if result.get('success'):
            session['publish_result'] = result
            return jsonify({
                'success': True,
                'publish_result': result,
                'message': 'Content published successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to publish')
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/workflow-status')
def workflow_status():
    """Get current workflow status"""
    try:
        status = orchestrator.get_workflow_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Simple in-memory cache for locations (cleared on server restart)
_locations_cache = {}
_cache_timeout = 300  # 5 minutes

@app.route('/api/locations', methods=['GET'])
def get_locations():
    """Proxy endpoint for SerpApi Locations API with caching"""
    try:
        import requests
        import time
        
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', '10')
        
        # Check cache first
        cache_key = f"{query.lower()}_{limit}"
        if cache_key in _locations_cache:
            cached_data, cached_time = _locations_cache[cache_key]
            if time.time() - cached_time < _cache_timeout:
                return jsonify(cached_data)
            else:
                # Cache expired, remove it
                del _locations_cache[cache_key]
        
        # Build SerpApi Locations API URL
        url = 'https://serpapi.com/locations.json'
        params = {}
        
        if query:
            params['q'] = query
        if limit:
            params['limit'] = limit
        
        # Note: SerpApi Locations API is free and doesn't require API key
        # But if it did, we would use: params['api_key'] = config.SERPAPI_KEY
        
        # Reduced timeout for faster failure (3 seconds instead of 10)
        response = requests.get(url, params=params, timeout=3)
        response.raise_for_status()
        
        locations = response.json()
        
        # Cache the result
        _locations_cache[cache_key] = (locations, time.time())
        
        # Limit cache size
        if len(_locations_cache) > 100:
            # Remove oldest entries
            oldest_key = min(_locations_cache.keys(), 
                           key=lambda k: _locations_cache[k][1])
            del _locations_cache[oldest_key]
        
        # Set cache headers for client-side caching
        response_obj = jsonify(locations)
        response_obj.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
        return response_obj
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch locations: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_chat_edit(user_message: str, blog_post: Dict[str, Any]) -> Dict[str, Any]:
    """Process chat-based edit request using AI"""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Create prompt for content editing
        prompt = f"""
        The user wants to edit the following blog post content. Please analyze their request and provide updated content.
        
        User Request: {user_message}
        
        Current Blog Post:
        Title: {blog_post.get('title', '')}
        Content: {blog_post.get('content', '')[:2000]}...
        
        Please provide:
        1. Updated content based on the user's request
        2. A brief explanation of what was changed
        3. Any SEO considerations for the changes
        
        Return as JSON:
        {{
            "updated_content": {{
                "title": "string",
                "content": "string",
                "meta_title": "string",
                "meta_description": "string"
            }},
            "ai_response": "string",
            "changes_made": ["change1", "change2", ...],
            "seo_notes": "string"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-5",  # Default model, can be made configurable if needed
            messages=[
                {"role": "system", "content": "You are an expert content editor. Help users improve their blog posts while maintaining SEO best practices."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        edit_result = json.loads(response.choices[0].message.content)
        edit_result['success'] = True
        
        return edit_result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'ai_response': 'Sorry, I encountered an error processing your request.'
        }

if __name__ == '__main__':
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
