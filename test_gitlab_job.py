#!/usr/bin/env python
"""
Test script for GitLab job log extraction functionality.
This script demonstrates how to use the extract_logs_from_gitlab_job_url function.
"""

import os
import sys
import logging
import urllib3
from pprint import pprint

# Disable SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the function
from gmail_agent.gitlab_operations import extract_logs_from_gitlab_job_url

def main():
    """Main function to test the GitLab job log extraction"""
    # Test URLs - replace with actual URLs you want to test
    test_job_url = "https://10.53.252.149/aiot/2025.kh042-amrm/backend/amrm-framework-core/-/jobs/984933"

    # You can provide a token directly or it will use the one from environment variables
    # Uncomment and modify the line below to use a specific token
    gitlab_token = "bidv-xMuzW4HUdoyd1gHdg9v_"

    print("Testing GitLab job log extraction...")
    print(f"Job URL: {test_job_url}")

    # Call the function
    result = extract_logs_from_gitlab_job_url(test_job_url, token=gitlab_token)

    # Print the result
    print("\nResult:")
    if result["success"]:
        print("✅ Successfully retrieved job logs")
        print(f"Status Code: {result.get('status_code')}")
        print("\nLog Preview:")
        print("-" * 50)
        print(result.get("logs_preview", "No logs available"))
        print("-" * 50)

        # Save logs to file if needed
        if result.get("logs"):
            log_file = "gitlab_job_logs.txt"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(result["logs"])
            print(f"\nComplete logs saved to {log_file}")
    else:
        print("❌ Failed to retrieve job logs")
        print(f"Error: {result.get('error')}")
        print(f"Status Code: {result.get('status_code', 'N/A')}")
        if result.get("response_content"):
            print("\nResponse content:")
            print(result["response_content"])

if __name__ == "__main__":
    main()
