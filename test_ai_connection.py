"""
Test script to check AI model connectivity.
"""
import os
import sys
from dotenv import load_dotenv

# Ensure we load environment variables
load_dotenv(verbose=True)

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Print environment variables for debugging
print("Environment variables:")
print(f"GOOGLE_API_KEY present: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
print(f"OPENAI_API_KEY present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"GMAIL_PROXY_ENABLED: {os.getenv('GMAIL_PROXY_ENABLED')}")
print(f"GMAIL_PROXY_HTTP: {os.getenv('GMAIL_PROXY_HTTP')}")
print(f"GMAIL_PROXY_HTTPS: {os.getenv('GMAIL_PROXY_HTTPS')}")

# Configure proxy for the session
if os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true":
    http_proxy = os.getenv("GMAIL_PROXY_HTTP", "")
    https_proxy = os.getenv("GMAIL_PROXY_HTTPS", "")

    os.environ["HTTP_PROXY"] = http_proxy
    os.environ["HTTPS_PROXY"] = https_proxy
    print(f"Using proxy: HTTP={http_proxy}, HTTPS={https_proxy}")

# Test Google Gemini API
try:
    print("\n=== Testing Google Gemini API ===")
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment variables!")
        sys.exit(1)

    print(f"Configuring Gemini with API key: {api_key[:5]}...{api_key[-4:]}")
    genai.configure(api_key=api_key)

    # Configure proxy for Google API client
    try:
        import google.auth.transport.requests
        import httplib2
        import socks

        if os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true":
            print("Setting up proxy for Google API client...")
            proxy_url = os.getenv("GMAIL_PROXY_HTTP", "")
            if proxy_url:
                try:
                    proxy_parts = proxy_url.split('://')
                    if len(proxy_parts) > 1:
                        host_port = proxy_parts[1].split(':')
                        if len(host_port) > 1:
                            proxy_host = host_port[0]
                            proxy_port = int(host_port[1])
                            print(f"Proxy details - Host: {proxy_host}, Port: {proxy_port}")

                            # Create HTTP object with proxy
                            http = httplib2.Http(
                                proxy_info=httplib2.ProxyInfo(
                                    httplib2.socks.PROXY_TYPE_HTTP,
                                    proxy_host,
                                    proxy_port
                                )
                            )
                            print("Successfully created HTTP object with proxy")
                except Exception as e:
                    print(f"Error setting up proxy: {str(e)}")
    except ImportError:
        print("Could not import required modules for proxy configuration")

    # Test model connection
    print("Testing connection to Gemini model...")
    models = genai.list_models()
    print(f"Available models: {[m.name for m in models]}")

    # Test generation
    print("Testing text generation...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say hello in 5 words")
    print(f"Response: {response.text}")
    print("Gemini API test completed successfully!")

except Exception as e:
    print(f"Error testing Gemini API: {str(e)}")

# Test OpenAI API
try:
    print("\n=== Testing OpenAI API ===")
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables!")
        sys.exit(1)

    print(f"Configuring OpenAI with API key: {api_key[:5]}...{api_key[-4:]}")
    openai.api_key = api_key

    # Configure proxy for OpenAI
    if os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true":
        proxy_url = os.getenv("GMAIL_PROXY_HTTPS", "")
        print(f"Setting up proxy for OpenAI: {proxy_url}")
        openai.proxy = proxy_url

    # Test connection
    print("Testing connection to OpenAI...")
    # Use appropriate call depending on OpenAI version
    try:
        # New API style (v1)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in 5 words"}],
            max_tokens=20
        )
        result = response.choices[0].message.content
    except (ImportError, AttributeError):
        # Old API style
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in 5 words"}],
            max_tokens=20
        )
        result = response.choices[0].message.content

    print(f"Response: {result}")
    print("OpenAI API test completed successfully!")

except Exception as e:
    print(f"Error testing OpenAI API: {str(e)}")

print("\nTest completed.")
