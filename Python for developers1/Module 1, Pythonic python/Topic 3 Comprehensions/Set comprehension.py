names = ["Ana", "Brian", "Claire", "Alice", "Bob"]
initials = {name[0] for name in names}
print(initials)
names = ["anna", "Brian", "claire", "Alice", "bob"]
initials = {name[0].upper() for name in names}
print(initials)

reviews = [
    "Great product",
    "Not what I expected",
    "Excellent value for money",
    "Great product",
    "Too expensive"
]
unique_word_counts = {len(review.split()) for review in reviews}
print(unique_word_counts)