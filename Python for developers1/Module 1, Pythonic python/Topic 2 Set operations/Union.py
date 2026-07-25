frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

all_skills = frontend | backend
print(all_skills)

all_skills2 = frontend.union(backend)
print(all_skills2)

frontend = {"HTML", "CSS", "JavaScript"}
backend = {"Python", "Databases", "JavaScript"}

combined1 = backend | frontend
print(combined1)

combined2 = frontend.union(backend)
print(combined2)

server1_packages = {"nginx", "postgresql", "redis", "python3-pip", "curl"}
server2_packages = {"docker", "git", "redis", "nodejs", "curl"}

combined_packages = server1_packages | server2_packages
print(combined_packages)