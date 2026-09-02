grid = [
     ["Riverside Inn", "Greenfield LLC", "Sunset Weddings", "Oak & Vine", "Maple Events"],
     [1200, 950, 1500, 1100, 800]
]
total = 0
for name, cost in zip(grid[0], grid[1]):
            print(f"{name}, {cost}")
            total += cost
            running_total = total
print("Highest package cost:", max(grid[1]))
print("Total package cost:", running_total)