from unittest.mock import patch, MagicMock
from api.db.models import Template
from sqlmodel import Session

from conftest import engine


def _seed_template(template_id: int = 1) -> None:
    """Insert a minimal template so fill_form can find it."""
    with Session(engine) as session:
        tpl = Template(
            id=template_id,
            name="Test Template",
            fields={"name": "string"},
            pdf_path="test.pdf",
        )
        session.add(tpl)
        session.commit()


# --- Bug #82: exception handler returns JSON 404 --------------------------

def test_fill_form_template_not_found(client):
    """AppError should be caught by the registered handler and return 404 JSON."""
    response = client.post(
        "/forms/fill",
        json={"template_id": 9999, "input_text": "hello"},
    )
    assert response.status_code == 404
    assert response.json() == {"error": "Template not found"}


# --- Bug #83: single query, happy path ------------------------------------

@patch("api.routes.forms.Controller")
def test_fill_form_success(mock_controller_cls, client):
    _seed_template(template_id=1)

    mock_controller = MagicMock()
    mock_controller.fill_form.return_value = "/outputs/filled.pdf"
    mock_controller_cls.return_value = mock_controller

    response = client.post(
        "/forms/fill",
        json={"template_id": 1, "input_text": "John Doe"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == 1
    assert data["input_text"] == "John Doe"
    assert data["output_pdf_path"] == "/outputs/filled.pdf"

    # Controller.fill_form should have been called exactly once
    mock_controller.fill_form.assert_called_once()


@patch("api.routes.forms.get_template")
@patch("api.routes.forms.Controller")
def test_fill_form_queries_db_once(mock_controller_cls, mock_get_template, client):
    """Regression: get_template must be called only once per request (#83)."""
    mock_get_template.return_value = MagicMock(
        fields={"name": "string"}, pdf_path="test.pdf"
    )
    mock_controller = MagicMock()
    mock_controller.fill_form.return_value = "/outputs/filled.pdf"
    mock_controller_cls.return_value = mock_controller

    response = client.post(
        "/forms/fill",
        json={"template_id": 1, "input_text": "hello"},
    )
    assert response.status_code == 200
    mock_get_template.assert_called_once()
