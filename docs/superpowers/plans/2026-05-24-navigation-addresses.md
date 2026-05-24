# Navigation Address Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Hermes navigation parsing so full street addresses and long destination phrases are recognized reliably and routed to the phone Maps flow.

**Architecture:** Keep the change small and centered on the backend natural-language parser. Navigation intent should remain a single command type (`navigate_to`) with a destination string that preserves address punctuation and number details. Add narrow tests for the parser and command formatting so the phone and backend stay aligned without changing the existing voice, photo, or location flows.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, Kotlin/Android stays unchanged for this refinement.

---

### Task 1: Tighten navigation parsing

**Files:**
- Modify: `backend/app/natural_commands.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_navigation_parser_keeps_full_address(client, admin_user):
    ...
    res = client.post(
        "/api/v1/commands/natural",
        json={"text": "Ei Jarvis, me leva para Rua Oscar Freire, 123, São Paulo - SP"},
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["command"]["payload"]["destination"] == "Rua Oscar Freire, 123, São Paulo - SP"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_api.py -k navigation -v`
Expected: fail because the current parser trims destination text too aggressively for long addresses.

- [ ] **Step 3: Write minimal implementation**

```python
def _extract_navigation_destination(text: str) -> str:
    text = re.sub(r"^(ei|oi|ok|hey)\s+(jarvis|hermes)[,:\-\s]*", "", text, flags=re.I)
    match = re.search(
        r"(?:me\s+)?(?:leva|levar|navega|navegar|abre|abrir|vai|ir|mostra|mostrar)\s+(?:para|pra|pro|até|a|ao|à)?\s*(.+)$",
        text,
        flags=re.I,
    )
    if match:
        return match.group(1).strip(" ,.:;-")
    return text.strip(" ,.:;-")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_api.py -k navigation -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/natural_commands.py backend/tests/test_api.py docs/superpowers/plans/2026-05-24-navigation-addresses.md
git commit -m "refine navigation address parsing"
```

### Task 2: Preserve existing navigation summaries

**Files:**
- Modify: `backend/app/command_wait.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_navigation_summary_formats_long_destination():
    message = format_command_result_message(
        device_name="HermesPhone",
        command_type="navigate_to",
        status="done",
        result={"destination": "Rua Oscar Freire, 123, São Paulo - SP", "opened_url": "google.navigation:q=Rua%20Oscar%20Freire"},
    )
    assert "Rua Oscar Freire, 123, São Paulo - SP" in message
    assert "google.navigation" in message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_api.py -k navigation_summary -v`
Expected: fail if the summary drops address detail.

- [ ] **Step 3: Write minimal implementation**

```python
if command_type == "navigate_to":
    detail = result or {}
    destination = detail.get("destination") or "destino"
    if detail.get("opened_url"):
        return f"Navegação aberta em {device_name} para {destination}: {detail.get('opened_url')}"
    return f"Navegação aberta em {device_name} para {destination}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_api.py -k navigation_summary -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/command_wait.py backend/tests/test_api.py docs/superpowers/plans/2026-05-24-navigation-addresses.md
git commit -m "preserve navigation address summaries"
```

### Task 3: Validate backend and publish

**Files:**
- Modify: none

- [ ] **Step 1: Run the focused backend test set**

Run: `PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_api.py backend/tests/test_google_workspace.py`
Expected: all tests pass.

- [ ] **Step 2: Run diff hygiene**

Run: `git diff --check`
Expected: no whitespace or patch formatting errors.

- [ ] **Step 3: Push to staging**

```bash
git push origin staging
```
