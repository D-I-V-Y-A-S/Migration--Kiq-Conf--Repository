import base64
import urllib.parse

email = 
api_token = 

# Combine email and token
auth_string = f"{email}:{api_token}"

# Base64 encode
auth_bytes = base64.b64encode(auth_string.encode("utf-8"))
auth_base64 = auth_bytes.decode("utf-8")

# Optional: URL encode the Base64 string (usually not needed in headers)
auth_base64_url = urllib.parse.quote(auth_base64)

# Use in headers
headers = {
    "Authorization": f"Basic {auth_base64}",
    "Content-Type": "application/json"
}

print("Base64 Auth:", auth_base64)
print("URL Encoded Auth:", auth_base64_url)
