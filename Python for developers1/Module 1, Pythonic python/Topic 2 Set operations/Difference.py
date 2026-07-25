frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

only_frontend = frontend - backend
print(only_frontend)

only_frontend2 = frontend.difference(backend)
print(only_frontend2)

frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

backend_only = backend - frontend
print(backend_only)

registered = {"Edwin", "Sifuna", "Baddie", "Zuena"}
attendees = {"Zuena", "Baddie"}
registered_only = registered.difference(attendees)