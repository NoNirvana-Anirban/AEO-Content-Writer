# SEO Content Creation Agent

An agentic workflow for creating SEO-optimized blog posts from keywords using OpenAI and WordPress MCP integration.

## Features

- **SERP Research**: Analyze top-ranking pages using SerpAPI or OpenAI Web Search
- **Content Brief Generation**: Create structured content briefs based on competitor analysis
- **AI Content Writing**: Generate SEO-optimized content with proper formatting
- **Interactive Review**: Edit content with AI assistant help
- **WordPress Integration**: Save posts as drafts to WordPress using MCP

## Quick Start

### Option 1: Batch File (Recommended)
```bash
# Start the application
start_app.bat

# Stop the application
stop_app.bat
```

### Option 2: PowerShell Script
```powershell
# Start the application
.\start_app.ps1
```

### Option 3: Manual Start
```bash
# Using full Python path
"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe" main.py --web
```

## Web Interface

Once started, open your browser and go to:
- **Main Interface**: http://localhost:3000
- **Review Interface**: http://localhost:3000/review

## Configuration

Make sure your `.env` file contains:
```
OPENAI_API_KEY=your_openai_api_key
SERPAPI_KEY=your_serpapi_key
WORDPRESS_DOMAIN=your_wordpress_domain
WORDPRESS_USER=your_wordpress_username
WORDPRESS_PASSWORD=your_wordpress_app_password
```

## Troubleshooting

### Issue: "Python was not found"
**Solution**: Use the batch file or PowerShell script which includes the full Python path.

### Issue: "localhost constantly opening"
**Solution**: 
1. Run `stop_app.bat` to stop all processes
2. Use `start_app.bat` to start cleanly
3. Debug mode is disabled to prevent auto-reload issues

### Issue: "Port 3000 already in use"
**Solution**: 
1. Run `stop_app.bat` to stop existing processes
2. Or change the port in `config.py`

## Workflow

1. **Enter Keyword**: Input your target keyword
2. **Choose Research Method**: SerpAPI or OpenAI Web Search
3. **Review Content**: Edit and improve with AI assistance
4. **Save to WordPress**: Posts are saved as drafts

## WordPress MCP Integration

The application uses real WordPress MCP integration:
- Posts are saved as drafts (not published)
- Proper slugs are generated automatically
- SEO metadata is added via Yoast
- Real post IDs and URLs are created

## Support

For issues or questions, check the troubleshooting section above.