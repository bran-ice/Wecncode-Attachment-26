trucks = {
    "truck_77": {"chef": "Rosa", "capacity": 80, "downtown_day": "Tuesday"},
    "truck_92": {"chef": "mateo", "capacity": 65, "downtown_day": "Friday"}
}
for truck_id, details in trucks.items():
    chef = details["chef"]
    capacity = details["capacity"]
    print(f"{truck_id}- Chef: {chef} Capacity: {capacity}")

print("Chef for truck_92:", trucks["truck_92"]["chef"])