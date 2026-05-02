# IVR Assessor Backend

## Quick Start

Create a local virtual environment and install the package in editable mode:

```bash
cd backend/python
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run the CLI from anywhere after activation:

```bash
python -m ivr_assessor.cli version
python -m ivr_assessor.cli --help
```

Run the test suite:

```bash
python -m pytest -q
```
