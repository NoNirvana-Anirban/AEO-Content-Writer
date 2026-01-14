# SEO Content Creation Agent - Start Script
Write-Host "Starting SEO Content Creation Agent..." -ForegroundColor Green
Write-Host ""
Write-Host "Using Python 3.11.3" -ForegroundColor Yellow
Write-Host "Web Interface: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Red
Write-Host ""

# Start the Flask app
& "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe" main.py --web
