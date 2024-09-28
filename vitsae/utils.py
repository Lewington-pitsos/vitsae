import json
import sys

def load_credentials(credentials_path='.credentials.json'):
    """
    Load credentials and configuration from a JSON file.
    """
    try:
        with open(credentials_path) as f:
            credentials = json.load(f)
        return credentials
    except Exception as e:
        print(f"Error loading credentials from {credentials_path}: {e}")
        sys.exit(1)
