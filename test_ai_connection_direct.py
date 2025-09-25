"""
Test connection to AI services with proper environment loading.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force load environment variables from .env file
env_path = Path("D:/tuanns2/Source Code/AI/Gmail-Agent/.env")
load_dotenv(dotenv_path=env_path, override=True, verbose=True)

print("\n=== ENVIRONMENT VARIABLES ===")
print(f"GOOGLE_API_KEY: {'Present' if os.getenv('GOOGLE_API_KEY') else 'Missing'}")
print(f"OPENAI_API_KEY: {'Present' if os.getenv('OPENAI_API_KEY') else 'Missing'}")
print(f"GMAIL_PROXY_ENABLED: {os.getenv('GMAIL_PROXY_ENABLED')}")
print(f"GMAIL_PROXY_HTTP: {os.getenv('GMAIL_PROXY_HTTP')}")

# Apply proxy settings
if os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true":
    http_proxy = os.getenv("GMAIL_PROXY_HTTP", "")
    os.environ["HTTP_PROXY"] = http_proxy
    os.environ["HTTPS_PROXY"] = http_proxy  # Use HTTP proxy for HTTPS too
    print(f"Using proxy: {http_proxy}")

print("\n=== TESTING GOOGLE GEMINI ===")
try:
    import google.generativeai as genai
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found!")
    else:
        print(f"Configuring with API key: {api_key[:5]}...{api_key[-4:]}")
        genai.configure(api_key=api_key)

        # Try simple test with increased timeout
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("Sending test request (this may take a moment)...")
        response = model.generate_content("Say hello", request_options={"timeout": 90})
        print(f"Response: {response.text}")
        print("✓ Google Gemini connection successful!")
except Exception as e:
    print(f"✗ Error with Google Gemini: {str(e)}")

print("\n=== TESTING OPENAI ===")
try:
    import openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found!")
    else:
        print(f"Configuring with API key: {api_key[:5]}...{api_key[-4:]}")
        openai.api_key = api_key

        # Set proxy for OpenAI if enabled
        if os.getenv("GMAIL_PROXY_ENABLED", "False").lower() == "true":
            openai.proxy = http_proxy
            print(f"Using proxy for OpenAI: {http_proxy}")

        # Try simple API call
        print("Sending test request (this may take a moment)...")
        try:
            # Try new API style first
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10,
                timeout=90
            )
            print(f"Response: {response.choices[0].message.content}")
        except (ImportError, AttributeError):
            # Fall back to old API style
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10
            )
            print(f"Response: {response.choices[0].message.content}")

        print("✓ OpenAI connection successful!")
except Exception as e:
    print(f"✗ Error with OpenAI: {str(e)}")

print("\nTest completed")
