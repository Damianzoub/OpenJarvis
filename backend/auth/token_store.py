from google.oauth2.credentials import Credentials
from auth.google_auth import SCOPES
creds = Credentials.from_authorized_user_file(
    "token.json",
    SCOPES
)