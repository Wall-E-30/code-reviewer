"""
bench/generator/injector.py

Deterministic AST and structural bug injector for Aion-Bench (BENCH-02).
Mutates valid Python and TypeScript/JavaScript code by injecting logic bugs,
security vulnerabilities, resource leaks, and off-by-one errors with
exact ground-truth line anchors.
"""

from __future__ import annotations

import ast
import difflib
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from bench.schema import (
    BenchmarkCase,
    FindingCategory,
    FindingSeverity,
    GroundTruthFinding,
)


def compute_modified_line_range(original_code: str, modified_code: str) -> Tuple[int, int]:
    """
    Compute 1-indexed [line_start, line_end] span in modified_code that reflects mutations.
    """
    orig_lines = original_code.splitlines(keepends=True)
    mod_lines = modified_code.splitlines(keepends=True)

    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    changed_starts: List[int] = []
    changed_ends: List[int] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            start = j1 + 1
            end = max(j1 + 1, j2)
            changed_starts.append(start)
            changed_ends.append(end)
        elif tag == "delete":
            # Deletion anchor is the line in modified_code immediately adjacent
            anchor = max(1, j1 + 1 if j1 < len(mod_lines) else len(mod_lines))
            changed_starts.append(anchor)
            changed_ends.append(anchor)

    if not changed_starts:
        return 1, 1

    return min(changed_starts), max(changed_ends)


def generate_unified_diff(original_code: str, modified_code: str, file_path: str) -> str:
    """Generate standard unified diff formatted string."""
    orig_lines = original_code.splitlines(keepends=True)
    mod_lines = modified_code.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
    )
    return "".join(diff_lines)


# =====================================================================
# Python Mutation Implementations
# =====================================================================

def mutate_invert_comparison_python(code: str) -> Tuple[str, str, str]:
    """Inverts comparison and boolean operators in Python code."""
    # Look for comparison operators first (multi-char first, then single-char)
    comp_replacements = [
        (r"(?<![=><!])==(?![=])", "!=", "Changed '==' to '!='"),
        (r"(?<![=><!])!=(?![=])", "==", "Changed '!=' to '=='"),
        (r"(?<![=><!])>=(?![=])", "<", "Changed '>=' to '<'"),
        (r"(?<![=><!])<=(?![=])", ">", "Changed '<=' to '>'"),
        (r"(?<![=><!])>(?![=])", "<=", "Changed '>' to '<='"),
        (r"(?<![=><!])<(?![=])", ">=", "Changed '<' to '>='"),
        (r"\bnot\s+in\b", "in", "Changed 'not in' to 'in'"),
        (r"(?<!\bnot\s)\bin\b", "not in", "Changed 'in' to 'not in'"),
        (r"\band\b", "or", "Changed 'and' to 'or'"),
        (r"\bor\b", "and", "Changed 'or' to 'and'"),
    ]

    for pattern, repl, desc in comp_replacements:
        # Avoid mutating comments or docstrings by checking line-by-line
        lines = code.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            match = re.search(pattern, line)
            if match:
                new_line = line[: match.start()] + repl + line[match.end() :]
                lines[idx] = new_line
                mutated = "\n".join(lines)
                if not code.endswith("\n"):
                    pass
                else:
                    mutated += "\n"
                return (
                    mutated,
                    f"Inverted comparison operator: {desc}, reversing branch logic.",
                    "Restore original operator.",
                )

    raise ValueError("No invertible comparison operator found in code.")


def mutate_off_by_one_python(code: str) -> Tuple[str, str, str]:
    """Introduces off-by-one errors in ranges or slice boundaries in Python code."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        # Mutate range(len(x)) -> range(len(x) + 1)
        if re.search(r"range\s*\(\s*len\s*\((.*?)\)\s*\)", line):
            new_line = re.sub(
                r"range\s*\(\s*len\s*\((.*?)\)\s*\)",
                r"range(len(\1) + 1)",
                line,
                count=1,
            )
            lines[idx] = new_line
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Off-by-one boundary error in range(len(...) + 1) causes IndexError out of bounds.",
                "Use range(len(...)) without the + 1 addition.",
            )

        # Mutate range(n) -> range(n + 1)
        m = re.search(r"range\s*\(\s*([a-zA-Z_]\w*|\d+)\s*\)", line)
        if m and m.group(1) != "0":
            var = m.group(1)
            new_line = re.sub(
                r"range\s*\(\s*" + re.escape(var) + r"\s*\)",
                f"range({var} + 1)",
                line,
                count=1,
            )
            lines[idx] = new_line
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Off-by-one error: range({var} + 1) iterates one step past valid boundary.",
                f"Use range({var}) to prevent out of bounds access.",
            )

        # Mutate <= len(...) -> < len(...) or < len(...) -> <= len(...)
        if "< len(" in line:
            lines[idx] = line.replace("< len(", "<= len(", 1)
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Off-by-one error: '<= len(...)' exceeds collection size by 1.",
                "Use '< len(...)' instead of '<= len(...)'.",
            )

    raise ValueError("No suitable loop boundary or range found for off_by_one mutation.")


def mutate_none_dereference_python(code: str) -> Tuple[str, str, str]:
    """Removes defensive None checks or replaces safe .get() with unsafe indexing."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        # Replace .get(key, default) -> [key]
        m = re.search(r"(\w+)\.get\s*\(\s*(['\"][^'\"]+['\"])\s*,\s*[^)]+\)", line)
        if m:
            obj, key = m.group(1), m.group(2)
            new_line = re.sub(
                r"(\w+)\.get\s*\(\s*(['\"][^'\"]+['\"])\s*,\s*[^)]+\)",
                f"{obj}[{key}]",
                line,
                count=1,
            )
            lines[idx] = new_line
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Unsafe dictionary access: removed safe .get() default, exposing {obj}[{key}] to KeyError.",
                f"Use {obj}.get({key}, default) to guard against missing keys.",
            )

        # Remove if ... is not None: guard
        m_guard = re.search(r"^(\s*)if\s+(\w+)\s+is\s+not\s+None\s*:", line)
        if m_guard:
            indent = m_guard.group(1)
            var_name = m_guard.group(2)
            # Replace guard with unconditional pass or flattened line
            lines[idx] = f"{indent}if True:  # Guard removed"
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Defensive guard removed: checking '{var_name} is not None' was bypassed, risking NoneType dereference.",
                f"Restore 'if {var_name} is not None:' defensive check.",
            )

    # General fallback: if code has .get(key)
    for idx, line in enumerate(lines):
        m = re.search(r"(\w+)\.get\s*\(\s*(['\"][^'\"]+['\"])\s*\)", line)
        if m:
            obj, key = m.group(1), m.group(2)
            lines[idx] = re.sub(
                r"(\w+)\.get\s*\(\s*(['\"][^'\"]+['\"])\s*\)",
                f"{obj}[{key}]",
                line,
                count=1,
            )
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Unsafe indexing: replaced safe .get() with direct index {obj}[{key}].",
                f"Use {obj}.get({key}) with fallback.",
            )

    raise ValueError("No suitable .get() or None guard found for none_dereference mutation.")


def mutate_resource_leak_python(code: str) -> Tuple[str, str, str]:
    """Replaces with open(...) context manager with unclosed file handle."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        m = re.search(r"^(\s*)with\s+open\s*\((.*?)\)\s+as\s+(\w+)\s*:", line)
        if m:
            indent = m.group(1)
            args = m.group(2)
            handle = m.group(3)
            lines[idx] = f"{indent}{handle} = open({args})"
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Resource leak: context manager 'with open(...)' was replaced by unclosed '{handle} = open(...)'.",
                f"Use 'with open(...) as {handle}:' to ensure automatic resource cleanup.",
            )

        # Match with session/client/connect
        m_conn = re.search(r"^(\s*)with\s+(\w+\.\w+)\s*\((.*?)\)\s+as\s+(\w+)\s*:", line)
        if m_conn:
            indent = m_conn.group(1)
            call = m_conn.group(2)
            args = m_conn.group(3)
            handle = m_conn.group(4)
            lines[idx] = f"{indent}{handle} = {call}({args})"
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                f"Resource leak: context manager for '{call}' removed; connection is never closed.",
                f"Use 'with {call}(...) as {handle}:' or close explicitly in finally block.",
            )

    raise ValueError("No 'with open(...)' or context manager found for resource_leak mutation.")


def mutate_unsafe_command_sink_python(code: str) -> Tuple[str, str, str]:
    """Converts safe parameterized subprocess calls or queries to raw string format + shell=True."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        # Subprocess safe run with sequence
        if "subprocess.run(" in line and "shell=True" not in line:
            m = re.search(r"subprocess\.run\s*\(\s*\[([^\]]+)\](.*)\)", line)
            if m:
                items = [it.strip() for it in m.group(1).split(",")]
                joined = " + ' ' + ".join(items)
                new_line = re.sub(
                    r"subprocess\.run\s*\(\s*\[([^\]]+)\](.*)\)",
                    f"subprocess.run({joined}, shell=True\\2)",
                    line,
                )
                lines[idx] = new_line
                return (
                    "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                    "Command injection vulnerability: subprocess executed with shell=True and dynamic arguments.",
                    "Pass arguments as a list without shell=True to avoid command injection.",
                )

        # SQL query execution with parameter tuple -> f-string interpolation
        m_sql = re.search(r"(\w+)\.execute\s*\(\s*(['\"][^'\"]+['\"])\s*,\s*\((.*?)\)\s*\)", line)
        if m_sql:
            cursor = m_sql.group(1)
            query = m_sql.group(2).strip("'\"")
            param = m_sql.group(3).strip().rstrip(",")
            interpolated = query.replace("?", f"{{{param}}}").replace("%s", f"{{{param}}}")
            new_line = re.sub(
                r"(\w+)\.execute\s*\(\s*['\"][^'\"]+['\"]\s*,\s*\(.*?\)\s*\)",
                f'{cursor}.execute(f"{interpolated}")',
                line,
            )
            lines[idx] = new_line
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "SQL Injection vulnerability: parameterized query converted to f-string interpolation.",
                "Use parameterized query (? or %s) with argument tuple instead of f-string.",
            )

    raise ValueError("No safe subprocess or query execution found for unsafe_command_sink mutation.")


def mutate_swallowed_exception_python(code: str) -> Tuple[str, str, str]:
    """Replaces typed exception handlers with bare except: pass."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        m = re.search(r"^(\s*)except\s+([A-Za-z0-9_,\s\(\)]+)\s*(?:as\s+\w+)?\s*:", line)
        if m:
            indent = m.group(1)
            # Find next non-empty line
            lines[idx] = f"{indent}except:"
            if idx + 1 < len(lines):
                next_indent = " " * (len(indent) + 4)
                lines[idx + 1] = f"{next_indent}pass  # Swallowed exception"
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Swallowed exception: explicit exception handler replaced with bare 'except: pass'.",
                "Catch specific exception types and log or re-raise unexpected failures.",
            )

    raise ValueError("No typed 'except ...:' handler found for swallowed_exception mutation.")


# =====================================================================
# TypeScript / JavaScript Mutation Implementations
# =====================================================================

def mutate_loose_equality_ts(code: str) -> Tuple[str, str, str]:
    """Replaces strict equality (=== / !==) with loose equality (== / !=)."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        if "===" in line:
            lines[idx] = line.replace("===", "==", 1)
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Loose equality operator '==' used instead of strict '===', risking type coercion bugs.",
                "Use strict equality '===' to avoid unexpected coercion.",
            )
        elif "!==" in line:
            lines[idx] = line.replace("!==", "!=", 1)
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Loose inequality operator '!=' used instead of strict '!==', risking type coercion bugs.",
                "Use strict inequality '!==' to avoid unexpected coercion.",
            )

    raise ValueError("No strict equality (=== / !==) found for loose_equality mutation.")


def mutate_missing_await_ts(code: str) -> Tuple[str, str, str]:
    """Removes 'await' keyword before an asynchronous promise call."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        if re.search(r"\bawait\s+", line):
            lines[idx] = re.sub(r"\bawait\s+", "", line, count=1)
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Missing 'await' keyword on asynchronous function call; returns pending Promise instead of value.",
                "Prepend 'await' to resolve the returned Promise.",
            )

    raise ValueError("No 'await' keyword found for missing_await mutation.")


def mutate_unhandled_promise_ts(code: str) -> Tuple[str, str, str]:
    """Removes .catch(...) error handler from a Promise chain."""
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        m = re.search(r"\.catch\s*\(\s*(?:err|\(\s*err\s*\)|error|\(\s*error\s*\))\s*=>.*?\)", line)
        if m:
            lines[idx] = re.sub(
                r"\.catch\s*\(\s*(?:err|\(\s*err\s*\)|error|\(\s*error\s*\))\s*=>.*?\)",
                "",
                line,
                count=1,
            )
            return (
                "\n".join(lines) + ("\n" if code.endswith("\n") else ""),
                "Unhandled Promise rejection: removed '.catch()' handler from Promise chain.",
                "Attach a '.catch()' error handler to catch and handle Promise rejections.",
            )

    raise ValueError("No '.catch(...)' handler found for unhandled_promise mutation.")


# =====================================================================
# Seed Code Templates for Bulk Synthesis
# =====================================================================

SEED_TEMPLATES_PYTHON = {
    "invert_comparison": [
        "def check_permission(user, role):\n    if user.role == role:\n        return True\n    return False\n",
        "def is_positive(val):\n    if val > 0:\n        return True\n    return False\n",
        "def is_valid_age(age):\n    if age >= 18 and age <= 120:\n        return True\n    return False\n",
        "def contains_item(item, items):\n    if item in items:\n        return True\n    return False\n",
        "def is_empty(seq):\n    if len(seq) == 0:\n        return True\n    return False\n",
    ],
    "off_by_one": [
        "def print_elements(items):\n    for i in range(len(items)):\n        print(items[i])\n",
        "def process_batches(total_count):\n    for batch in range(total_count):\n        run_batch(batch)\n",
        "def check_bounds(idx, data):\n    if idx < len(data):\n        return data[idx]\n    return None\n",
        "def get_slice(arr, limit):\n    return [arr[i] for i in range(limit)]\n",
    ],
    "none_dereference": [
        "def get_config_value(config):\n    return config.get('timeout', 30)\n",
        "def fetch_user_email(profile):\n    return profile.get('email', 'guest@example.com')\n",
        "def lookup_port(settings):\n    return settings.get('port', 8080)\n",
        "def calculate_total(order):\n    tax = order.get('tax_rate', 0.05)\n    return order['subtotal'] * (1 + tax)\n",
    ],
    "resource_leak": [
        "def read_payload(path):\n    with open(path, 'r', encoding='utf-8') as f:\n        return f.read()\n",
        "def write_metrics(path, data):\n    with open(path, 'w', encoding='utf-8') as f:\n        f.write(data)\n",
        "def dump_json(file_path, obj):\n    with open(file_path, 'w') as f:\n        import json\n        json.dump(obj, f)\n",
    ],
    "unsafe_command_sink": [
        "import subprocess\ndef ping_host(host):\n    return subprocess.run(['ping', '-c', '1', host], check=True)\n",
        "import subprocess\ndef run_tool(cmd, arg):\n    return subprocess.run([cmd, arg], capture_output=True)\n",
        "def query_user_by_id(cursor, user_id):\n    return cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n",
        "def fetch_record(cursor, record_id):\n    cursor.execute('SELECT details FROM records WHERE id = ?', (record_id,))\n    return cursor.fetchone()\n",
    ],
    "swallowed_exception": [
        "def parse_payload(raw_json):\n    import json\n    try:\n        return json.loads(raw_json)\n    except (ValueError, TypeError) as exc:\n        raise ValueError('Invalid JSON payload') from exc\n",
        "def safe_int_convert(val):\n    try:\n        return int(val)\n    except (ValueError, TypeError):\n        return 0\n",
        "def fetch_remote_data(client, url):\n    try:\n        return client.get(url)\n    except ConnectionError as err:\n        logger.error(err)\n        raise\n",
    ],
}

SEED_TEMPLATES_TYPESCRIPT = {
    "loose_equality": [
        "export function verifyToken(expected: string, actual: string): boolean {\n    return actual === expected;\n}\n",
        "export function isAdministrator(role: string): boolean {\n    return role === 'admin';\n}\n",
        "export function validateStatus(code: number): boolean {\n    return code !== 500;\n}\n",
    ],
    "missing_await": [
        "export async function fetchUserData(userId: string): Promise<User> {\n    const response = await api.getUser(userId);\n    return response.data;\n}\n",
        "export async function saveProfile(profile: Profile): Promise<void> {\n    await db.save(profile);\n    console.log('Saved');\n}\n",
        "export async function computeChecksum(file: string): Promise<string> {\n    const hash = await crypto.calculate(file);\n    return hash;\n}\n",
    ],
    "unhandled_promise": [
        "export function loadConfig(): void {\n    fetch('/config')\n        .then(res => res.json())\n        .catch(err => console.error('Failed to load config', err));\n}\n",
        "export function syncMetrics(data: Metric[]): void {\n    api.post('/metrics', data)\n        .then(() => notifySuccess())\n        .catch(error => handleFailure(error));\n}\n",
    ],
}


# =====================================================================
# Main BugInjector Class
# =====================================================================

class BugInjector:
    """
    Deterministic bug injection engine for Aion-Bench (BENCH-02).
    Applies AST / structural mutation operators and produces BenchmarkCase records
    with exact ground-truth line anchors.
    """

    OPERATORS_PYTHON = {
        "invert_comparison": (mutate_invert_comparison_python, FindingCategory.BUG, FindingSeverity.CRITICAL, "MUT-INVERT-COMP"),
        "off_by_one": (mutate_off_by_one_python, FindingCategory.BUG, FindingSeverity.MAJOR, "MUT-OFF-BY-ONE"),
        "none_dereference": (mutate_none_dereference_python, FindingCategory.BUG, FindingSeverity.CRITICAL, "MUT-NONE-DEREF"),
        "resource_leak": (mutate_resource_leak_python, FindingCategory.PERFORMANCE, FindingSeverity.MAJOR, "MUT-RESOURCE-LEAK"),
        "unsafe_command_sink": (mutate_unsafe_command_sink_python, FindingCategory.SECURITY, FindingSeverity.CRITICAL, "MUT-UNSAFE-SINK"),
        "swallowed_exception": (mutate_swallowed_exception_python, FindingCategory.BUG, FindingSeverity.MAJOR, "MUT-SWALLOWED-EXC"),
    }

    OPERATORS_TYPESCRIPT = {
        "loose_equality": (mutate_loose_equality_ts, FindingCategory.BUG, FindingSeverity.MINOR, "MUT-JS-LOOSE-EQ"),
        "missing_await": (mutate_missing_await_ts, FindingCategory.BUG, FindingSeverity.CRITICAL, "MUT-JS-MISSING-AWAIT"),
        "unhandled_promise": (mutate_unhandled_promise_ts, FindingCategory.BUG, FindingSeverity.MAJOR, "MUT-JS-UNHANDLED-PROMISE"),
        "invert_comparison": (mutate_invert_comparison_python, FindingCategory.BUG, FindingSeverity.CRITICAL, "MUT-INVERT-COMP"),
    }

    def get_available_operators(self, language: str = "python") -> List[str]:
        """Return list of available operator names for the given language."""
        lang = language.lower()
        if lang == "python":
            return list(self.OPERATORS_PYTHON.keys())
        elif lang in ("typescript", "javascript"):
            return list(self.OPERATORS_TYPESCRIPT.keys())
        return list(self.OPERATORS_PYTHON.keys())

    def inject_bug(
        self,
        code: str,
        operator: str,
        language: str = "python",
        file_path: Optional[str] = None,
        case_id: Optional[str] = None,
        repository: str = "aion/synthetic-bench",
    ) -> BenchmarkCase:
        """
        Inject a targeted bug into the provided code using the specified mutation operator.

        Args:
            code: Original valid source code.
            operator: Mutation operator name (e.g. 'invert_comparison', 'off_by_one').
            language: Programming language ('python', 'typescript', 'javascript').
            file_path: Relative file path for diff and case.
            case_id: Unique case identifier.
            repository: Repository identifier.

        Returns:
            BenchmarkCase with is_clean_diff=False, unified diff, and exact GroundTruthFinding.
        """
        lang = language.lower()
        ext = "ts" if lang == "typescript" else ("js" if lang == "javascript" else "py")
        file_path = file_path or f"src/module.{ext}"
        case_id = case_id or f"inj-{operator}-{uuid.uuid4().hex[:8]}"

        # Select operator table
        if lang in ("typescript", "javascript"):
            op_table = self.OPERATORS_TYPESCRIPT
        else:
            op_table = self.OPERATORS_PYTHON

        if operator not in op_table:
            raise ValueError(f"Unknown mutation operator '{operator}' for language '{language}'.")

        mutator_fn, category, severity, rule_id = op_table[operator]

        mutated_code, description, fix_suggestion = mutator_fn(code)

        line_start, line_end = compute_modified_line_range(code, mutated_code)
        diff_str = generate_unified_diff(code, mutated_code, file_path)

        finding = GroundTruthFinding(
            finding_id=f"gt-{case_id}-1",
            line_start=line_start,
            line_end=line_end,
            category=category,
            severity=severity,
            description=description,
            fix_suggestion=fix_suggestion,
            rule_id=rule_id,
            file_path=file_path,
        )

        return BenchmarkCase(
            case_id=case_id,
            repository=repository,
            language=language,
            file_path=file_path,
            original_code=code,
            modified_code=mutated_code,
            diff=diff_str,
            split="dev",
            is_clean_diff=False,
            ground_truth=[finding],
            metadata={
                "mutation_operator": operator,
                "synthesizer": "BugInjector",
            },
        )

    def generate_seed_cases(self, language: str = "python") -> List[BenchmarkCase]:
        """Generate benchmark cases from all available built-in seed templates."""
        lang = language.lower()
        cases: List[BenchmarkCase] = []

        if lang in ("typescript", "javascript"):
            seeds = SEED_TEMPLATES_TYPESCRIPT
            ext = "ts" if lang == "typescript" else "js"
        else:
            seeds = SEED_TEMPLATES_PYTHON
            ext = "py"

        for op_name, templates in seeds.items():
            for idx, code in enumerate(templates, start=1):
                try:
                    case = self.inject_bug(
                        code=code,
                        operator=op_name,
                        language=language,
                        file_path=f"src/{op_name}_{idx}.{ext}",
                        case_id=f"inj-{lang}-{op_name}-{idx}",
                    )
                    cases.append(case)
                except Exception:
                    continue

        return cases
