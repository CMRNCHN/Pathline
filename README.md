<!-- cspell:ignore pytest -->

# IVR Suite

This repository now keeps one master tree:

- `backend/python` - the Python IVR assessor CLI, tests, and docs

Run it from the repo root with:

```bash
./run_ivr_assessor.sh --help
```

Or work directly in the backend package:

```bash
cd backend/python
python -m pytest -q
```

## Development

### Prerequisites

- Python 3.11+
- `pip` or `uv`

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-repo/IVRSuite.git
   cd IVRSuite
   ```

2. Install dependencies:

   ```bash
   pip install -e backend/python
   ```

### Project Structure

- `backend/python/src`: Core logic for IVR assessment.
- `backend/python/tests`: Suite of unit and integration tests.
- `docs`: Additional documentation and architecture diagrams.
