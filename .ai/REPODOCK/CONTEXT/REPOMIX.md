# REPOMIX NOTES

Use Repomix to create a compact project context dump for AI handoff.

## Recommended command
```bash
repomix . --output .ai/repomix-output.txt --ignore-file .ai/.repomixignore
```

## Before sharing with AI
- Review for secrets, credentials, tokens.
- Check that `.ai/.repomixignore` excludes everything sensitive.
- The output file (`.ai/repomix-output.txt`) is gitignored by default.
