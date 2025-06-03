import os
import requests
import binascii
from hashlib import sha256 as SHA256
from Crypto.Hash import HMAC
from dotenv import load_dotenv
from Crypto.Hash import SHA256, HMAC
# Load variables from .env into the environment
load_dotenv()

BASE_URL = "https://rest.opt.knoiq.co/api/v1"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # Public access key
SITE_ID = os.getenv("SITE_ID")  # KnowledgeIQ site ID
USER_TYPE = "Admin"  # Either 'admin' or 'public'
SECRET_KEY = os.getenv("SECRET_KEY")

def get_auth_challenge():
    try:
        url = f"{BASE_URL}/auth/challenge"
        payload = {
            "accessToken": ACCESS_TOKEN,
            "siteId": SITE_ID,
            "userType": USER_TYPE
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, verify=False)
        if response.status_code == 200:
            challenge_token = response.json().get("challengeString")
            return challenge_token
    except requests.exceptions.RequestException as e:
        print("[:x:] Failed to get challenge:", str(e))
        return None
    except Exception as e:
        print("[:x:] Unexpected error while getting challenge:", str(e))
        return None

def generate_signature(challenge_token):
    """Step 2: Generate HMAC-SHA256 signature and encode it in Base64"""
    try:
        hex_bytes = bytes.fromhex(SECRET_KEY)
        secret_b64 = binascii.b2a_base64(hex_bytes).decode("utf-8").strip()
        secret_key_encoded = binascii.a2b_base64(secret_b64)
        hash_value = HMAC.new(secret_key_encoded, challenge_token.encode("utf-8"), digestmod=SHA256)
        signature = binascii.b2a_base64(hash_value.digest()).decode("utf-8").strip()
        return signature
    except Exception as e:
        print("[:x:] Failed to generate signature:", str(e))
        return None

def get_auth_token(challenge_token, signature):
    """Step 3: Exchange the challenge and signature for an authentication token"""
    try:
        url = f"{BASE_URL}/auth/token"
        payload = {
            "challenge": challenge_token,
            "signature": signature
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        auth_token = response.json().get("token")
        print(auth_token)
        print("[:white_check_mark:] Authentication successful! Token received.")
        return auth_token
    except requests.exceptions.RequestException as e:
        print("[:x:] Authentication failed:", str(e))
        return None
    except Exception as e:
        print("[:x:] Unexpected error during authentication:", str(e))
        return None

# Main authentication flow
try:
    challenge = get_auth_challenge()
    if challenge:
        signature = generate_signature(challenge)
        if signature:
            auth_token = get_auth_token(challenge, signature)
        else:
            print("[:x:] Signature generation failed.")
    else:
        print("[:x:] Challenge retrieval failed.")
except Exception as e:
    print("[:x:] Critical error in authentication flow:", str(e))


#Source pages fetching 
response=requests.get(source_url,headers=headers_1)
if response.status_code == 200:
    try:
        data = response.json()
        fields = data.get("fields", []) 
        Document_Id = data['detail']['id']
        Created_by=data['detail']['createdByPerson']
        print(Document_Id,Created_by)
        confluence_email=getuserEmail(Created_by)
        print("Mapped email:", confluence_email)
        title = get_document_title(fields)
        print("Document Title:", title)
    except ValueError:
        print("Failed to parse JSON.")
else:
    print(f"Request failed with status code: {response.status_code}")
