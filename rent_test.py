import requests

baseURL = "http://localhost:8000/api/v1"

# 1. Login
login_data = {
    "email": "cliente@casilleros.com",
    "password": "cliente123"
}
resp = requests.post(f"{baseURL}/auth/login", json=login_data)
token = resp.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. Get Locker C-1 ID
resp = requests.get(f"{baseURL}/lockers", headers=headers)
lockers = resp.json()
c1 = next(l for l in lockers if l["locker_number"] == "C-1")
c1_id = c1["id"]

# 3. Rent Locker C-1
print(f"Renting C-1 (ID {c1_id})...")
rent_data = {"hours": 2}
resp = requests.post(f"{baseURL}/lockers/{c1_id}/rent-public", data=rent_data, headers=headers)
print("Rent response:", resp.json())

# 4. Check Lockers
resp = requests.get(f"{baseURL}/lockers", headers=headers)
lockers = resp.json()
for l in lockers:
    if l["locker_number"] == "C-1":
        print("C-1 status:", l["status"])
        print("C-1 assigned to:", l["assigned_user_id"])
