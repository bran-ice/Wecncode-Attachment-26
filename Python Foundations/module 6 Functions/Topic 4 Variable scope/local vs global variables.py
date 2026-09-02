total = 100

def make_local():
    total = 200
    print("inside make_local, total =", total)

def read_global():
    print("inside read_global, total =", total)

make_local()
read_global()
print("outside, total =", total)

total = 100

store_name = "Khetias"
def welcome():
    print(f"Welcome to {store_name}")

def today_earning(sale_list):
    today_earning = sum(sale_list)
    print(f"Total earnings for today at {store_name} is ${today_earning:,.2f}")
    return today_earning