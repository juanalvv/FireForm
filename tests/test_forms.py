from src.controller import Controller


def test_submit_form_template_not_found_returns_404(client):
    response = client.post(
        "/forms/fill",
        json={"template_id": 99999, "input_text": "test input"},
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Template not found"}


def test_submit_form_success_returns_output_path(client, monkeypatch):
    def fake_fill_form(self, user_input, fields, pdf_form_path):
        return "src/inputs/fake_output.pdf"

    monkeypatch.setattr(Controller, "fill_form", fake_fill_form)

    template_payload = {
        "name": "Template for form test",
        "pdf_path": "src/inputs/file.pdf",
        "fields": {
            "Employee's name": "string",
            "Employee's job title": "string",
        },
    }

    template_res = client.post("/templates/create", json=template_payload)
    assert template_res.status_code == 200
    template_id = template_res.json()["id"]

    response = client.post(
        "/forms/fill",
        json={
            "template_id": template_id,
            "input_text": "Employee's name is John Doe. Job title is manager.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template_id
    assert data["output_pdf_path"] == "src/inputs/fake_output.pdf"
