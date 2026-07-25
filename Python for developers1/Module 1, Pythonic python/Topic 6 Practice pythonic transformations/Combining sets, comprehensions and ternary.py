records = [
    {'item': 'heirloom_tomato', 'score': 92},
    {'item': 'organic_kale', 'score': 78},
    {'item': 'conventional_potato', 'score': 85},
    {'item': 'organic_carrot', 'score': 67},
    {'item': 'heirloom_tomato', 'score': 88}
]

unique_items = {r['item'] for r in records}
print(f"Unique items inspected: {unique_items}")

classifications = ['pass' if r['score'] >= 80 else 'fail' for r in records]

average_score = sum(r['score'] for r in records) / len(records)

for i in range(len(records)):
    print(f"{records[i]['item']}: {classifications[i]}")

print(f"Average score: {average_score}")