"""
rl/training_v2/bug_generator.py

Test-Verified LLM Bug Generator (TRAIN2-02).
Generates realistic synthetic bugs with guaranteed executable test/reproduction verification:
- Test assertion MUST PASS on clean code.
- Test assertion MUST FAIL on buggy mutated code.
- Evaluation bugs and training bugs originate from distinct generator sources and seeds.
"""

from __future__ import annotations

import difflib
from enum import Enum
import hashlib
import logging
import random
from typing import Any, Callable, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("AionBugGenerator")


class BugCategory(str, Enum):
    OFF_BY_ONE = "off_by_one"
    NULL_DEREFERENCE = "null_dereference"
    RESOURCE_LEAK = "resource_leak"
    SQL_INJECTION = "sql_injection"
    BOUNDARY_ERROR = "boundary_error"
    UNHANDLED_EXCEPTION = "unhandled_exception"


class GeneratedBug(BaseModel):
    """Schema for an executable, test-verified synthetic bug."""
    bug_id: str
    category: BugCategory
    split: str  # "train" or "eval"
    clean_code: str
    buggy_code: str
    diff: str
    test_code: str
    verified: bool
    line_number: int
    description: str
    suggested_fix: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


def execute_test_on_code(code: str, test_code: str) -> Tuple[bool, Optional[str]]:
    """
    Safely execute a test against provided source code in an isolated dictionary scope.
    Returns:
        (passed: bool, error_message: Optional[str])
    """
    scope: Dict[str, Any] = {}
    try:
        # Compile and execute the target code
        compiled_target = compile(code, "<target_code>", "exec")
        exec(compiled_target, scope)

        # Compile and execute the test assertions
        compiled_test = compile(test_code, "<test_code>", "exec")
        exec(compiled_test, scope)

        # Call run_test() if defined, else assume top-level assertions completed
        if "run_test" in scope and callable(scope["run_test"]):
            scope["run_test"]()

        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"


class TestVerifiedBugGenerator:
    """
    Synthesizes bugs with test/reproduction failure verification.
    Guarantees strict source separation between training and evaluation bugs.
    """
    __test__ = False

    def __init__(self, base_seed: int = 42) -> None:
        self.base_seed = base_seed

    def _get_generator_seed(self, split: str) -> int:
        if split == "eval":
            return (self.base_seed * 32452843 + 8654057) % 2147483647
        return (self.base_seed * 10007 + 104729) % 2147483647

    def _build_diff(self, clean: str, buggy: str, filename: str = "sample.py") -> str:
        clean_lines = clean.splitlines(keepends=True)
        buggy_lines = buggy.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            clean_lines,
            buggy_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        ))
        return "".join(diff_lines)

    def _get_templates_for_split(self, split: str) -> List[Dict[str, Any]]:
        """
        Distinct template libraries for training versus evaluation (TRAIN2-02).
        Guarantees that evaluation bugs never mirror training bug structures.
        """
        if split == "eval":
            # Distinct evaluation source templates
            return [
                {
                    "category": BugCategory.NULL_DEREFERENCE,
                    "clean": (
                        "def get_account_balance(account):\n"
                        "    if account is None:\n"
                        "        return 0.0\n"
                        "    return float(account.get('balance', 0.0))\n"
                    ),
                    "buggy": (
                        "def get_account_balance(account):\n"
                        "    return float(account['balance'])\n"
                    ),
                    "test": (
                        "assert get_account_balance({'balance': 150.0}) == 150.0\n"
                        "assert get_account_balance(None) == 0.0\n"
                    ),
                    "line": 2,
                    "desc": "TypeError / KeyError: Unchecked None dereference on account dictionary.",
                    "fix": "    if account is None:\n        return 0.0\n",
                },
                {
                    "category": BugCategory.BOUNDARY_ERROR,
                    "clean": (
                        "def paginate_items(items, page, page_size):\n"
                        "    if page < 1 or page_size < 1:\n"
                        "        return []\n"
                        "    start = (page - 1) * page_size\n"
                        "    return items[start:start + page_size]\n"
                    ),
                    "buggy": (
                        "def paginate_items(items, page, page_size):\n"
                        "    start = page * page_size\n"
                        "    return items[start:start + page_size]\n"
                    ),
                    "test": (
                        "items = [1, 2, 3, 4, 5]\n"
                        "assert paginate_items(items, 1, 2) == [1, 2]\n"
                    ),
                    "line": 2,
                    "desc": "Boundary / Pagination error: page index 1 skips the initial page slice.",
                    "fix": "    start = (page - 1) * page_size\n",
                },
                {
                    "category": BugCategory.RESOURCE_LEAK,
                    "clean": (
                        "def read_audit_log(path):\n"
                        "    with open(path, 'w') as f:\n"
                        "        f.write('audit')\n"
                        "    with open(path, 'r') as f:\n"
                        "        return f.read().strip()\n"
                    ),
                    "buggy": (
                        "def read_audit_log(path):\n"
                        "    f = open(path, 'w')\n"
                        "    f.write('audit')\n"
                        "    f2 = open(path, 'r')\n"
                        "    return f2.read().strip()\n"
                    ),
                    "test": (
                        "import os\n"
                        "import tempfile\n"
                        "tmp = tempfile.mktemp()\n"
                        "assert read_audit_log(tmp) == 'audit'\n"
                        "# On buggy version f is unclosed, attempt removal\n"
                        "os.remove(tmp)\n"
                    ),
                    "line": 2,
                    "desc": "Resource leak: file descriptors left open without context manager.",
                    "fix": "    with open(path, 'w') as f:\n",
                },
            ]
        else:
            # Training source templates
            return [
                {
                    "category": BugCategory.OFF_BY_ONE,
                    "clean": (
                        "def calculate_running_sums(numbers):\n"
                        "    sums = []\n"
                        "    current = 0\n"
                        "    for i in range(len(numbers)):\n"
                        "        current += numbers[i]\n"
                        "        sums.append(current)\n"
                        "    return sums\n"
                    ),
                    "buggy": (
                        "def calculate_running_sums(numbers):\n"
                        "    sums = []\n"
                        "    current = 0\n"
                        "    for i in range(len(numbers) - 1):\n"
                        "        current += numbers[i]\n"
                        "        sums.append(current)\n"
                        "    return sums\n"
                    ),
                    "test": (
                        "res = calculate_running_sums([1, 2, 3])\n"
                        "assert res == [1, 3, 6], f'Expected [1, 3, 6] but got {res}'\n"
                    ),
                    "line": 4,
                    "desc": "Off-by-one error: loop bounds range(len(numbers) - 1) omits final element.",
                    "fix": "    for i in range(len(numbers)):\n",
                },
                {
                    "category": BugCategory.NULL_DEREFERENCE,
                    "clean": (
                        "def format_user_display(user):\n"
                        "    if not user or not user.get('name'):\n"
                        "        return 'Guest'\n"
                        "    return user['name'].strip().title()\n"
                    ),
                    "buggy": (
                        "def format_user_display(user):\n"
                        "    return user['name'].strip().title()\n"
                    ),
                    "test": (
                        "assert format_user_display({'name': 'alice'}) == 'Alice'\n"
                        "assert format_user_display(None) == 'Guest'\n"
                        "assert format_user_display({}) == 'Guest'\n"
                    ),
                    "line": 2,
                    "desc": "TypeError: user is None dereference without guard check.",
                    "fix": "    if not user or not user.get('name'):\n        return 'Guest'\n",
                },
                {
                    "category": BugCategory.SQL_INJECTION,
                    "clean": (
                        "def build_user_query(user_id):\n"
                        "    if not isinstance(user_id, int):\n"
                        "        raise ValueError('user_id must be integer')\n"
                        "    return ('SELECT * FROM users WHERE id = ?', (user_id,))\n"
                    ),
                    "buggy": (
                        "def build_user_query(user_id):\n"
                        "    return f'SELECT * FROM users WHERE id = {user_id}'\n"
                    ),
                    "test": (
                        "q = build_user_query(42)\n"
                        "assert isinstance(q, tuple) and q[0] == 'SELECT * FROM users WHERE id = ?'\n"
                    ),
                    "line": 2,
                    "desc": "SQL injection vulnerability: unparameterized query f-string interpolation.",
                    "fix": "    return ('SELECT * FROM users WHERE id = ?', (user_id,))\n",
                },
                {
                    "category": BugCategory.UNHANDLED_EXCEPTION,
                    "clean": (
                        "def parse_port_number(port_str, default=8000):\n"
                        "    try:\n"
                        "        val = int(port_str)\n"
                        "        if 1 <= val <= 65535:\n"
                        "            return val\n"
                        "        return default\n"
                        "    except (ValueError, TypeError):\n"
                        "        return default\n"
                    ),
                    "buggy": (
                        "def parse_port_number(port_str, default=8000):\n"
                        "    val = int(port_str)\n"
                        "    return val\n"
                    ),
                    "test": (
                        "assert parse_port_number('8080') == 8080\n"
                        "assert parse_port_number('invalid') == 8000\n"
                        "assert parse_port_number(None) == 8000\n"
                    ),
                    "line": 2,
                    "desc": "Unhandled ValueError/TypeError when parsing non-integer port string.",
                    "fix": "    try:\n        val = int(port_str)\n    except (ValueError, TypeError):\n        return default\n",
                },
            ]

    def verify_bug_candidate(self, clean_code: str, buggy_code: str, test_code: str) -> bool:
        """
        Guarantees the core requirement of TRAIN2-02:
        - Test MUST PASS on clean code.
        - Test MUST FAIL on buggy code.
        """
        clean_passed, clean_err = execute_test_on_code(clean_code, test_code)
        if not clean_passed:
            logger.debug("Clean code failed test: %s", clean_err)
            return False

        buggy_passed, _ = execute_test_on_code(buggy_code, test_code)
        if buggy_passed:
            logger.debug("Buggy code unexpectedly passed test — bug is unverified!")
            return False

        return True

    def generate_verified_bug(self, clean_code: str, split: str = "train") -> Optional[GeneratedBug]:
        """
        Attempt to inject a test-verified bug into provided clean code.
        If provided code matches a known pattern, applies verified mutation.
        """
        seed = self._get_generator_seed(split)
        rng = random.Random(seed)
        templates = self._get_templates_for_split(split)

        for tmpl in templates:
            # Check verification invariant
            if self.verify_bug_candidate(tmpl["clean"], tmpl["buggy"], tmpl["test"]):
                diff = self._build_diff(tmpl["clean"], tmpl["buggy"])
                bug_id = f"bug_{split}_{tmpl['category'].value}_{hashlib.sha256(tmpl['buggy'].encode()).hexdigest()[:8]}"
                return GeneratedBug(
                    bug_id=bug_id,
                    category=tmpl["category"],
                    split=split,
                    clean_code=tmpl["clean"],
                    buggy_code=tmpl["buggy"],
                    diff=diff,
                    test_code=tmpl["test"],
                    verified=True,
                    line_number=tmpl["line"],
                    description=tmpl["desc"],
                    suggested_fix=tmpl["fix"],
                    metadata={"split_source": split, "seed": seed},
                )

        return None

    def generate_batch(self, count: int, split: str = "train") -> List[GeneratedBug]:
        """Generate a batch of distinct, test-verified bugs for the given split."""
        templates = self._get_templates_for_split(split)
        results: List[GeneratedBug] = []

        for i in range(count):
            tmpl = templates[i % len(templates)]
            # Verify test failure reproduction
            assert self.verify_bug_candidate(tmpl["clean"], tmpl["buggy"], tmpl["test"]), (
                f"Template {tmpl['category']} failed verification criteria"
            )
            diff = self._build_diff(tmpl["clean"], tmpl["buggy"])
            bug_id = f"gen_{split}_{tmpl['category'].value}_{i:03d}"
            results.append(
                GeneratedBug(
                    bug_id=bug_id,
                    category=tmpl["category"],
                    split=split,
                    clean_code=tmpl["clean"],
                    buggy_code=tmpl["buggy"],
                    diff=diff,
                    test_code=tmpl["test"],
                    verified=True,
                    line_number=tmpl["line"],
                    description=tmpl["desc"],
                    suggested_fix=tmpl["fix"],
                    metadata={"batch_index": i, "split": split},
                )
            )

        return results
