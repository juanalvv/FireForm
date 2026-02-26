from unittest.mock import patch, MagicMock


def test_create_template_success(client):
    payload = {
        "name": "Template 1",
        "pdf_path": "src/inputs/file.pdf",
        "fields": {
            "Employee's name": "string",
            "Employee's job title": "string",
            "Employee's department supervisor": "string",
            "Employee's phone number": "string",
            "Employee's email": "string",
            "Signature": "string",
            "Date": "string",
        },
    }

    with patch("api.routes.templates.Controller") as mock_controller_cls:
        mock_controller = MagicMock()
        mock_controller.create_template.return_value = "src/inputs/file.pdf"
        mock_controller_cls.return_value = mock_controller

        response = client.post("/templates/create", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Template 1"
    assert data["fields"] == payload["fields"]
    assert data["id"] is not None


def test_create_template_missing_fields(client):
    """Omitting required fields should return 422."""
    response = client.post("/templates/create", json={"name": "Bad"})
    assert response.status_code == 422
