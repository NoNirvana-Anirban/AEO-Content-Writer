#!/usr/bin/env python3
"""
Test the mcp-wordpress-remote proxy connection manually
This helps diagnose connection issues before using MCP
"""

import subprocess
import os
import sys
import shutil
from config import Config

def test_proxy_connection():
    """Test if the proxy can connect to WordPress"""
    print("=" * 60)
    print("Testing mcp-wordpress-remote Proxy Connection")
    print("=" * 60)
    
    config = Config()
    wp_url = f"https://{config.WORDPRESS_DOMAIN}".rstrip('/')
    username = config.WORDPRESS_USER
    password = config.WORDPRESS_PASSWORD
    
    print(f"\nWordPress URL: {wp_url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    
    if not password:
        print("\n✗ ERROR: WORDPRESS_PASSWORD not set in .env")
        return False
    
    # Test 1: Check if npx can run the proxy
    print("\n[1] Testing npx availability...")
    npx_path = shutil.which('npx')
    if npx_path:
        print(f"Found npx at: {npx_path}")
    
    try:
        # On Windows, use shell=True for better compatibility
        result = subprocess.run(
            ['npx', '--version'], 
            capture_output=True, 
            text=True, 
            timeout=10,
            shell=True  # Required on Windows
        )
        if result.returncode == 0:
            print(f"✓ npx is available (version: {result.stdout.strip()})")
        else:
            print(f"✗ npx check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ npx check failed: {str(e)}")
        # Try common Windows paths
        common_paths = [
            r"C:\Program Files\nodejs\npx.cmd",
            r"C:\Program Files (x86)\nodejs\npx.cmd",
        ]
        for path in common_paths:
            if os.path.exists(path):
                print(f"Found npx at: {path}")
                try:
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10, shell=True)
                    if result.returncode == 0:
                        print(f"✓ npx works from: {path} (version: {result.stdout.strip()})")
                        break
                except:
                    continue
        else:
            return False
    
    # Test 2: Try to download/run the proxy (it will try to connect)
    print("\n[2] Testing proxy connection (this will timeout if WordPress MCP is not installed)...")
    print("    This may take 10-20 seconds...")
    
    env = os.environ.copy()
    env.update({
        "WP_API_URL": wp_url,
        "WP_API_USERNAME": username,
        "WP_API_PASSWORD": password
    })
    
    try:
        # Run the proxy with a timeout - it should try to connect
        # We'll send a simple command and see if it responds
        # On Windows with shell=True, use string command
        if sys.platform == 'win32':
            cmd = 'npx -y @automattic/mcp-wordpress-remote@latest'
        else:
            cmd = ['npx', '-y', '@automattic/mcp-wordpress-remote@latest']
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            shell=(sys.platform == 'win32')  # Use shell on Windows
        )
        
        # Send a simple JSON-RPC initialize request
        init_request = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}\n'
        
        try:
            stdout, stderr = process.communicate(input=init_request, timeout=15)
            
            if process.returncode == 0:
                print("✓ Proxy responded successfully!")
                print(f"Response: {stdout[:200]}...")
                return True
            else:
                print(f"✗ Proxy failed with return code: {process.returncode}")
                if stderr:
                    print(f"Error output: {stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            print("⚠ Proxy is running but not responding (this might mean WordPress MCP plugin is not installed)")
            print("   The proxy is waiting for WordPress MCP to respond")
            process.kill()
            return False
            
    except Exception as e:
        print(f"✗ Proxy test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_proxy_connection()
        if success:
            print("\n✓ Proxy connection test passed!")
            sys.exit(0)
        else:
            print("\n✗ Proxy connection test failed")
            print("\nTroubleshooting:")
            print("1. Verify WordPress MCP plugin is installed and active")
            print("2. Check that application password is correct")
            print("3. Verify WordPress site is accessible")
            print("4. Check WordPress error logs for MCP-related errors")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

