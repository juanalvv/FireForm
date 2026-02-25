def validate_json(data: dict, expected_fields: list):
    """
    Ensures:
    - All expected fields exist in the output JSON
    - Missing fields are set to None
    - Invalid values ("-1", empty string) are normalized to None
    """

    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    if not isinstance(expected_fields, list):
        raise TypeError("expected_fields must be a list")

    validated = {}

    for field in expected_fields:
        value = data.get(field)

        if value in (None, "", "-1"):
            validated[field] = None
        else:
            validated[field] = value

    return validated