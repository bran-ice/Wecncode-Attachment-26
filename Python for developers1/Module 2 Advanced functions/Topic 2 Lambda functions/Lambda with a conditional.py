classify = lambda x: "even" if x % 2 == 0 else "odd"
print(classify(7))

transaction = lambda amount: "credit" if amount >= 0 else "debit"
print(transaction(450))