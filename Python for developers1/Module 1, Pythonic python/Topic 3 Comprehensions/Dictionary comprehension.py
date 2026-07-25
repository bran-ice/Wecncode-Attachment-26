names = ["Ana", "Brian", "Claire"]
name_lengths = {name: len(name) for name in names}
print(name_lengths)
names = ["Ana", "Brian", "Claire"]
name_lengths = {name.upper(): len(name) for name in names}
print(name_lengths)

emails = ["alice@example.com", "bob@mail.org", "carol@school.edu"]
username_to_domain = {email.split("@")[0]: email.split("@")[1] for email in emails}
print(username_to_domain)
 
filenames = ["report.pdf", "photo.jpg", "archive.tar.gz", "notes.txt"]
ext_map = {f: f.split(".")[-1] for f in filenames}
print(ext_map)