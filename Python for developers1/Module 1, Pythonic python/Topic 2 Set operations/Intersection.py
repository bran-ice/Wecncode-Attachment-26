frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

shared1 = frontend & backend
print(shared1)

shared2 = frontend.intersection(backend)
print(shared2)