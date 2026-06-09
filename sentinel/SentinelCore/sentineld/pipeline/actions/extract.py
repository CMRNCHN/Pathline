import re

def extract_actions(text):
    actions = []

    if re.search(r"meeting|call|schedule", text, re.I):
        actions.append({
            "type": "calendar",
            "title": text,
            "confidence": 0.7
        })

    if re.search(r"need to|remember|follow up", text, re.I):
        actions.append({
            "type": "task",
            "title": text,
            "confidence": 0.7
        })

    if re.search(r"decided|we agreed", text, re.I):
        actions.append({
            "type": "decision",
            "title": text,
            "confidence": 0.8
        })

    return actions
