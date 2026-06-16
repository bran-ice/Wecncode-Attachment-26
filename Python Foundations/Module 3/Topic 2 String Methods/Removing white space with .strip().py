s = "  alice  "
print("'" + s + "'")
print("'" + s.strip() + "'")

s = "\n\tbob  \n"
print("'" + s + "'")
print("'" + s.strip() + "'")

number =  "  +1-555-1234  "
clean_number = number.strip()
print("Calling" , clean_number)