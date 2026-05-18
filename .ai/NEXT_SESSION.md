# NEXT SESSION

Before making changes:

1. Read:
- AGENTS.md
- CODEX.md
- .ai/PROJECT_STATE.md
- .ai/ARCHITECTURE_RULES.md

2. Run:
.venv/bin/pytest tests/test_architecture.py -q

3. Inspect:
- infrastructure/config/paths.py
- tests/test_architecture.py

4. Focus:
- removing replay/runtime path leakage from analyst
- reducing tolerated topology violations incrementally
