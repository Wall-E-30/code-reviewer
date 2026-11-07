# Aion Code Reviewer — Official VS Code Extension (APP-03)

AI-native code review with AST-verified diagnostics, repo convention memory, and 1-click QuickFix code replacements directly in Visual Studio Code.

---

## Features

- ⚡ **Pre-Commit Staged Reviews:** Inspect uncommitted changes (`git diff --cached`) instantly without waiting for CI.
- 🎯 **High-Precision Diagnostics:** Low-noise, actionable warnings and errors with line-accurate squiggles in the editor.
- 💡 **1-Click QuickFix:** Apply suggested code fixes with `Ctrl+.` or `Cmd+.` instantly.
- 🧠 **Convention Memory:** Respects your repository's `.aion/conventions.json` to prevent recurring false positives and maintainer nitpicks.
- 🔒 **Local & Offline Inference:** Powered by local Ollama models (`aion-reviewer:latest`) or BYOK endpoints with zero mandatory cloud lock-in.

---

## Extension Commands

Access via Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

| Command | Title | Description |
|---|---|---|
| `aion.reviewStaged` | **Aion: Review Staged Changes** | Reviews all files staged in the local git repository. |
| `aion.reviewCurrentFile` | **Aion: Review Current File** | Analyzes the currently focused source file in editor. |
| `aion.showConventions` | **Aion: Show Repository Conventions** | Prints active team rules and suppressions from `.aion/conventions.json`. |

---

## Configuration Settings

Configure in VS Code Settings (`Ctrl+,` or `settings.json`):

```json
{
  "aion.executablePath": "aion",
  "aion.provider": "ollama",
  "aion.minConfidence": 0.70,
  "aion.maxComments": 5,
  "aion.autoReviewOnSave": false
}
```

---

## Prerequisites

Ensure the `aion` CLI is installed and available in your environment:

```bash
pip install -e .
```

Verify in terminal:

```bash
aion --help
```

