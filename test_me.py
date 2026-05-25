import requests

baseURL = "http://localhost:8000/api/v1"

# 1. Login
login_data = {
    "email": "cliente@casilleros.com",
    "password": "cliente123"
}
resp = requests.post(f"{baseURL}/auth/login", json=login_data)
print("Login status:", resp.status_code)
token = resp.json().get("access_token")

# 2. Get /users/me
headers = {"Authorization": f"Bearer {token}"}
resp2 = requests.get(f"{baseURL}/users/me", headers=headers)
print("/users/me:", resp2.json())

# 3. Get /lockers
resp3 = requests.get(f"{baseURL}/lockers", headers=headers)
lockers = resp3.json()
print("Lockers:")
for l in lockers:
    if l.get("assigned_user_id"):
        print(l.get("locker_number"), "assigned to", l.get("assigned_user_id"))

