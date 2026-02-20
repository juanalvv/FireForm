def validate_json(data: dict, expected_fields: list):
    """
    Validate that:
    - All expected fields exist
    - No value is None
    - No value is "-1"
    """

    errors = []

    for field in expected_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")
        else:
            value = data[field]

            if value is None or value == "-1":
                errors.append(f"Invalid value for field: {field}")

    if errors:
        print("[VALIDATION WARNINGS]")
        for e in errors:
            print(" -", e)
    else:
        print("[VALIDATION SUCCESS] All fields valid.")

    return data