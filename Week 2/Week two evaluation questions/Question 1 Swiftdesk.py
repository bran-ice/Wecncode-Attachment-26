name = input("Enter the customers name").strip()
email = input("Enter the email").strip()
department = input("Enter the department").strip()
summary = input("Enter a sentence summary").strip()

normalised_name = name.title()
parts = normalised_name.split()
initials = (parts[0][0] + parts[1][0]).upper()

normalised_email = email.lower()
email_user, email_domain = normalised_email.split("@")

normalised_department = department.upper().replace(" ", "_")
ticket_ref = f"{initials}-{normalised_department}"

if len(summary) > 20:
   preview = summary[:20] + "..."
else:
   preview = summary

print(f"Customer: {normalised_name}")
print(f"Initials: {initials}")
print(f"Email user: {email_user}")
print(f"Email domain: {email_domain}")
print(f"Department: {normalised_department}")
print(f"Ticket Ref: {ticket_ref}")
print(f"Summary preview: {preview}")


name = "allan  john TURING"
print(name)
name = name.lower().title()
print(name)
space = name.find(" ")

print(space)
print(name[0])
print(name[space+1])