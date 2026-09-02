def summarize(names: list[str], prices: dict[str, int]) -> None:
    print("Names:", names)
    print("Prices:", prices)
    print("Total:", sum(prices.values()))

users: list[str] = ["alice", "bob", "carol"]
catalog: dict[str, int] = {"A1": 30, "B2": 45}

summarize(users, catalog)
def summarize(names: list[str], prices: dict[str, float], discounts: set[float]) -> None:
    print("Names:", names)
    print("Prices:", prices)
    print("Total:", sum(prices.values()))
    print("Max discount:", max(discounts))

users: list[str] = ["alice", "bob", "carol"]
catalog: dict[str, float] = {"A1": 30.0, "B2": 45.5}
discounts: set[float] = {0.05, 0.10}

summarize(users, catalog, discounts)
def inventory_check(products: list[str], stock: dict[str, int], discontinued: set[str]) -> None:
    low_stock: list[str] = []
    for pid in products:
        if stock[pid] < 5:
            low_stock.append(pid)
    available: list[str] = [pid for pid in products if pid not in discontinued]
    print("Low stock:", low_stock)
    print("Available (excluding discontinued):", available)

products: list[str] = ["P100", "P101", "P102", "P103"]
stock: dict[str, int] = {"P100": 10, "P101": 3, "P102": 0, "P103": 6}
discontinued: set[str] = {"P102"}

inventory_check(products, stock, discontinued)