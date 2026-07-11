import requests

print("Probando OpenSky...")

try:
    r = requests.get(
        "https://auth.opensky-network.org",
        timeout=30
    )

    print("Código:", r.status_code)

except Exception as e:
    print("Error:")
    print(e)