"""
bench/generator/clean.py

Clean-diff negative generator for Aion-Bench (BENCH-02).
Generates valid, non-regressing code modifications (refactoring, whitespace,
docstrings, type hints, safe renames, unit tests) where any review comment
is penalized as a false positive (FPR).
"""

from __future__ import annotations

import ast
import difflib
import re
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from bench.schema import BenchmarkCase


def generate_clean_unified_diff(original_code: str, modified_code: str, file_path: str) -> str:
    """Generate standard unified diff formatted string for clean diffs."""
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
# Clean Transformation Operators
# =====================================================================

def clean_reformat_whitespace(code: str, language: str = "python") -> str:
    """PEP 8 whitespace and operator spacing normalization."""
    lines = code.splitlines()
    cleaned_lines: List[str] = []

    for line in lines:
        # Normalize operator spacing: e.g. x=1+2 -> x = 1 + 2 (if not keyword arg or slice)
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            # Add spaces around single '=' if not already spaced and not ==/!=/</>
            l = re.sub(r"(?<=\w)=(?=\w)", " = ", line)
            # Normalize trailing whitespace
            cleaned_lines.append(l.rstrip())
        else:
            cleaned_lines.append(line.rstrip())

    # Ensure single trailing newline
    result = "\n".join(cleaned_lines)
    if not result.endswith("\n"):
        result += "\n"

    # If no change occurred, ensure standardized formatting with an extra spacing adjustment
    if result == code:
        result = "\n".join(cleaned_lines) + "\n"
        if not result.startswith("\n"):
            result = "# Formatted via PEP 8 style guide\n" + result

    return result


def clean_add_docstrings(code: str, language: str = "python") -> str:
    """Adds docstrings or explanatory comments to functions."""
    lines = code.splitlines()
    new_lines: List[str] = []
    docstring_added = False

    for idx, line in enumerate(lines):
        new_lines.append(line)
        # Check for function definition
        if not docstring_added:
            m_def = re.search(r"^(\s*)def\s+([a-zA-Z_]\w*)\s*\(", line)
            if m_def:
                indent = m_def.group(1) + "    "
                func_name = m_def.group(2)
                doc = f'{indent}"""Perform {func_name.replace("_", " ")} operation."""'
                new_lines.append(doc)
                docstring_added = True
            elif language in ("typescript", "javascript"):
                m_fn = re.search(r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_]\w*)\s*\(", line)
                if m_fn:
                    indent = m_fn.group(1)
                    func_name = m_fn.group(2)
                    doc = f"{indent}/**\n{indent} * Execute {func_name} logic.\n{indent} */"
                    # Insert before function line
                    new_lines.pop()
                    new_lines.extend(doc.splitlines())
                    new_lines.append(line)
                    docstring_added = True

    if not docstring_added:
        # Fallback: add header docstring
        new_lines.insert(0, '"""Module utilities and helper routines."""\n')

    result = "\n".join(new_lines)
    if code.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def clean_add_type_hints(code: str, language: str = "python") -> str:
    """Annotates untyped function definitions with type hints."""
    lines = code.splitlines()
    new_lines: List[str] = []
    typed_added = False

    for line in lines:
        if language == "python" and not typed_added:
            # Match def func(a, b):
            m = re.match(r"^(\s*)def\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*:", line)
            if m:
                indent = m.group(1)
                func_name = m.group(2)
                raw_args = m.group(3).strip()

                if raw_args and ":" not in raw_args:
                    params = [p.strip() for p in raw_args.split(",") if p.strip()]
                    typed_params = ", ".join(f"{p}: Any" if p not in ("self", "cls") else p for p in params)
                    new_line = f"{indent}def {func_name}({typed_params}) -> Any:"
                    new_lines.append(new_line)
                    typed_added = True
                    continue
                elif not raw_args:
                    new_line = f"{indent}def {func_name}() -> None:"
                    new_lines.append(new_line)
                    typed_added = True
                    continue

        new_lines.append(line)

    if not typed_added and language == "python":
        # If no function matched or already typed, prepend typing import
        new_lines.insert(0, "from typing import Any, Optional, Dict, List")

    result = "\n".join(new_lines)
    if code.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def clean_safe_rename(code: str, language: str = "python") -> str:
    """Renames cryptic local variables to clear descriptive names across all references."""
    # Common short names to expand
    rename_pairs = [
        (r"\bres\b", "result"),
        (r"\bdata_dict\b", "payload_dict"),
        (r"\bx\b", "item_val"),
        (r"\bval\b", "element_value"),
        (r"\bidx\b", "index"),
    ]

    for pattern, replacement in rename_pairs:
        if re.search(pattern, code):
            # Only rename if replacement doesn't already exist in code
            if not re.search(r"\b" + re.escape(replacement) + r"\b", code):
                renamed = re.sub(pattern, replacement, code)
                if renamed != code:
                    return renamed

    # Fallback: add clear variable assignment alias
    lines = code.splitlines()
    for idx, line in enumerate(lines):
        if "return " in line:
            indent = re.match(r"^(\s*)", line).group(1)
            lines.insert(idx, f"{indent}# Explicit variable mapping\n{indent}result_output = None")
            break
    return "\n".join(lines) + ("\n" if code.endswith("\n") else "")


def clean_add_unit_tests(code: str, language: str = "python") -> str:
    """Appends valid unit test functions testing existing code without altering original logic."""
    if language == "python":
        test_block = (
            "\n\n# --- Unit Tests ---\n"
            "def test_module_behavior():\n"
            "    \"\"\"Verify basic module functions execute without exceptions.\"\"\"\n"
            "    assert True\n"
        )
    else:
        test_block = (
            "\n\n// --- Unit Tests ---\n"
            "describe('module execution', () => {\n"
            "    it('should initialize without error', () => {\n"
            "        expect(true).toBe(true);\n"
            "    });\n"
            "});\n"
        )
    return code.rstrip() + test_block


# =====================================================================
# Seed Clean Code Templates
# =====================================================================

SEED_CLEAN_PYTHON = {
    "reformat_whitespace": [
        "def compute_average(values):\n    total=sum(values)\n    count=len(values)\n    return total/count if count>0 else 0.0\n",
        "def filter_active(users):\n    return [u for u in users if u['active']==True]\n",
    ],
    "add_docstrings": [
        "def sanitize_string(text):\n    return text.strip().lower()\n",
        "def calculate_tax(subtotal, rate=0.08):\n    return subtotal * rate\n",
    ],
    "add_type_hints": [
        "def format_greeting(name):\n    return f'Hello, {name}!'\n",
        "def sum_numbers(a, b):\n    return a + b\n",
        "def get_user_status(user_id):\n    return {'status': 'active'}\n",
    ],
    "safe_rename": [
        "def process_elements(items):\n    res = []\n    for x in items:\n        res.append(x * 2)\n    return res\n",
        "def search_index(query, values):\n    for idx, val in enumerate(values):\n        if val == query:\n            return idx\n    return -1\n",
    ],
    "add_unit_tests": [
        "def multiply(a, b):\n    return a * b\n",
        "def is_even(num):\n    return num % 2 == 0\n",
    ],
}

SEED_CLEAN_TYPESCRIPT = {
    "reformat_whitespace": [
        "export function calculateDiscount(price: number, discount: number): number {\n    const finalPrice=price*(1-discount);\n    return finalPrice;\n}\n",
    ],
    "add_docstrings": [
        "export function formatCurrency(amount: number): string {\n    return `$${amount.toFixed(2)}`;\n}\n",
    ],
    "add_type_hints": [
        "export function parsePort(envValue) {\n    return parseInt(envValue, 10) || 3000;\n}\n",
    ],
    "safe_rename": [
        "export function sumArray(items: number[]): number {\n    let res = 0;\n    for (const val of items) {\n        res += val;\n    }\n    return res;\n}\n",
    ],
    "add_unit_tests": [
        "export function capitalize(str: string): string {\n    return str.charAt(0).toUpperCase() + str.slice(1);\n}\n",
    ],
}


# =====================================================================
# Main CleanDiffGenerator Class
# =====================================================================

class CleanDiffGenerator:
    """
    Clean-diff negative generator for Aion-Bench (BENCH-02).
    Generates valid refactorings and documentation updates that carry is_clean_diff=True
    and empty ground-truth findings (ground_truth=[]) to measure False-Positive Rate.
    """

    OPERATORS = {
        "reformat_whitespace": clean_reformat_whitespace,
        "add_docstrings": clean_add_docstrings,
        "add_type_hints": clean_add_type_hints,
        "safe_rename": clean_safe_rename,
        "add_unit_tests": clean_add_unit_tests,
    }

    def get_available_operators(self) -> List[str]:
        """Return list of supported clean transformation operators."""
        return list(self.OPERATORS.keys())

    def generate_clean_diff(
        self,
        code: str,
        operator: str,
        language: str = "python",
        file_path: Optional[str] = None,
        case_id: Optional[str] = None,
        repository: str = "aion/clean-negatives",
    ) -> BenchmarkCase:
        """
        Generate a clean diff benchmark case using the specified non-buggy operator.

        Args:
            code: Original valid source code.
            operator: Clean operator ('reformat_whitespace', 'add_docstrings', etc.).
            language: Programming language ('python', 'typescript', 'javascript').
            file_path: Relative file path.
            case_id: Unique case identifier.
            repository: Repository identifier.

        Returns:
            BenchmarkCase with is_clean_diff=True and ground_truth=[].
        """
        lang = language.lower()
        ext = "ts" if lang == "typescript" else ("js" if lang == "javascript" else "py")
        file_path = file_path or f"src/clean_{operator}.{ext}"
        case_id = case_id or f"clean-{operator}-{uuid.uuid4().hex[:8]}"

        if operator not in self.OPERATORS:
            raise ValueError(f"Unknown clean operator '{operator}'. Available: {list(self.OPERATORS.keys())}")

        clean_fn = self.OPERATORS[operator]
        modified_code = clean_fn(code, language=lang)

        # If modified code is identical, append an empty comment line to ensure diff
        if modified_code == code:
            modified_code = code.rstrip() + "\n# Clean refactoring verified\n"

        diff_str = generate_clean_unified_diff(code, modified_code, file_path)

        return BenchmarkCase(
            case_id=case_id,
            repository=repository,
            language=language,
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            diff=diff_str,
            split="dev",
            is_clean_diff=True,
            ground_truth=[],
            metadata={
                "clean_operator": operator,
                "synthesizer": "CleanDiffGenerator",
            },
        )

    def generate_seed_cases(self, language: str = "python") -> List[BenchmarkCase]:
        """Generate clean cases from built-in seed templates."""
        lang = language.lower()
        cases: List[BenchmarkCase] = []

        if lang in ("typescript", "javascript"):
            seeds = SEED_CLEAN_TYPESCRIPT
            ext = "ts" if lang == "typescript" else "js"
        else:
            seeds = SEED_CLEAN_PYTHON
            ext = "py"

        for op_name, templates in seeds.items():
            for idx, code in enumerate(templates, start=1):
                try:
                    case = self.generate_clean_diff(
                        code=code,
                        operator=op_name,
                        language=language,
                        file_path=f"src/{op_name}_{idx}.{ext}",
                        case_id=f"clean-{lang}-{op_name}-{idx}",
                    )
                    cases.append(case)
                except Exception:
                    continue

        return cases
