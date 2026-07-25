frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

unique_to_each = frontend ^ backend
print(unique_to_each)

unique_to_each2 = frontend.symmetric_difference(backend)
print(unique_to_each2)
frontend = {"HTML", "CSS", "JavaScript", "TypeScript"}
backend = {"Python", "JavaScript", "TypeScript", "Go"}

unique_to_each = frontend ^ backend
print(unique_to_each)