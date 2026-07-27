def make_range_validator(field, min_val, max_val):
    def checker(record):
        value = record.get(field)
        if value is None:
            return False
        return min_val <= value <= max_val
    return checker


def make_length_validator(field, max_length):
    def checker(record):
        value = record.get(field)
        if value is None:
            return False
        return len(str(value)) <= max_length
    return checker


def make_required_validator(*fields):
    def checker(record):
        for field in fields:
            if field not in record:
                return False
            val = record[field]
            if val is None or val == "":
                return False
        return True
    return checker


def validate_record(record, validators):
    return all(validator(record) for validator in validators)


def format_record(record):
    return f"Employee: {record.get('name')} (ID: {record.get('id')}, Age: {record.get('age')}, Username: {record.get('username')})"


if __name__ == "__main__":
    validators_list = [
        make_required_validator("id", "name", "age", "username"),
        make_range_validator("age", 18, 65),
        make_length_validator("username", 12)
    ]

    employees = [
        {"id": 1, "name": "Alice Smith", "age": 30, "username": "alice_s"},
        {"id": 2, "name": "Bob Jones", "age": 70, "username": "bobjones"},
        {"id": 3, "name": "Charlie Brown", "age": 25, "username": "charlie_brown_very_long"},
        {"id": 4, "name": "Diana Prince", "age": 28, "username": "diana"},
        {"id": 5, "name": "Ethan Hunt", "age": 40, "username": "ethan"},
        {"id": 6, "name": "Fiona Glenanne", "age": 35, "username": "fiona"}
    ]

    passed_records = list(filter(lambda r: validate_record(r, validators_list), employees))
    failed_records = list(filter(lambda r: not validate_record(r, validators_list), employees))

    formatted_passed = list(map(format_record, passed_records))
    formatted_failed = list(map(format_record, failed_records))

    print(f"Total processed: {len(employees)}")
    print(f"Pass count: {len(passed_records)}")
    print(f"Fail count: {len(failed_records)}")
    
    print("\nPassed Records:")
    for record in formatted_passed:
        print(record)

    print("\nFailed Records:")
    for record in formatted_failed:
        print(record)