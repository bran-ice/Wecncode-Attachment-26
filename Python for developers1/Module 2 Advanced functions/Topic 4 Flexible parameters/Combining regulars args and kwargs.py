def create_profile(name, *skills, **details):
    print("Name:", name)
    print("Skills (tuple):", skills)
    print("Details (dict):", details)
    return {"name": name, "skills": skills, "details": details}

print(create_profile("Alice", "Python", "SQL", location="NYC", subscribed=True))
def create_profile(name, *skills, **details):
    print("Name:", name)
    print("Skills (tuple):", skills)
    print("Details (dict):", details)
    return {"name": name, "skills": skills, "details": details}

print(create_profile("Bob", location="LA", subscribed=False))

def record_books(title, *authors, **metadata):
    print("Title:", title)
    print("Number(tuple):", authors)
    print("Metadata(dict):", metadata)
    return{"title": title, "number": authors, "metadata": metadata}
print(record_books("Electronics", "Alice Smith", "Bob Jones", year=2006))