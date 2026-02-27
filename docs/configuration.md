# Configuration

FireForm uses **environment variables** for runtime configuration. All values
are validated at application startup — if a variable is set but invalid the
application will refuse to start and print a clear error message.

## Environment variables

| Variable | Default | Rules |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Must start with `http://` or `https://` |
| `OLLAMA_API_PATH` | `/api/generate` | Must start with `/` |
| `OUTPUT_PDF_SUFFIX` | `_filled.pdf` | Must end with `.pdf` |

### Example `.env`

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_API_PATH=/api/generate
OUTPUT_PDF_SUFFIX=_filled.pdf
```

## How validation works

`src/config.py` exposes two public helpers:

- **`validate_config()`** — checks the three variables listed above and raises
  `ValueError` with a descriptive message when a value is invalid.  This is
  called once during API startup (in `api/main.py`).
- **`build_ollama_url()`** — builds the full Ollama endpoint URL using
  `urllib.parse.urljoin()` so that trailing/leading slashes never produce a
  double-slash bug (e.g. `http://host//api/generate`).

## Running the validation tests

```bash
pytest tests/test_config.py -v
```
