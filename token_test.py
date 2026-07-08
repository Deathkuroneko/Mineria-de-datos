import requests

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

CLIENT_ID = "ekkd-api-client"
CLIENT_SECRET = "0hxu5eVaza4rmdimK79qXdKbwzIwtUtH"

r = requests.post(
    TOKEN_URL,
    data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    timeout=30
)

print("Estado:", r.status_code)
print(r.text)
