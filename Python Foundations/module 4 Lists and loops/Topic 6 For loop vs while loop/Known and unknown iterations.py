customers = ["Acme Co", "BrightApps", "CloudNine"]

for customer in customers:
    print("Generate invoice for", customer)
    print("Send invoice email to", customer)

customers = ["Acme Co", "BrightApps", "CloudNine"]

for customer in customers:
    print("Processing", customer)
    while True:  # repeat until the condition changes
        answer = input("Charge succeeded? (y/n/c) ")
        if answer == "y":
            print("Charge successful for", customer)
            break
        if answer == "c":
            print("Operator canceled retries for", customer)
            break
        print("Retrying charge for", customer)