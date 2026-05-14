import sys,os 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.google_auth import get_credentials

creds = get_credentials()
print("Authentication successful. Credentials obtained:")
print(f"Access Token: {creds.token}")
print(f"Refresh Token: {creds.refresh_token}")
print(f"Token Expiry: {creds.expiry}")
print("Scopes: ", creds.scopes)