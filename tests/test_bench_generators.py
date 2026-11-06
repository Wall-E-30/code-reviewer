"""
tests/test_bench_generators.py

Unit and integration tests for Aion-Bench generators (BENCH-02, BENCH-03):
- BugInjector mutation operators (Python and TypeScript)
- CleanDiffGenerator negative controls (reformatting, typing, docstrings, rename, tests)
- ReviewMiner chatter filtering, subsequent commit checks, and category mapping
- Corpus synthesizer producing >= 200 schema-valid benchmark cases
"""

from pathlib import Path
import pytest

from bench.generator.clean import CleanDiffGenerator
from bench.generator.injector import (
    BugInjector,
    compute_modified_line_range,
    generate_unified_diff,
)
from bench.generator.synthesize import main as synth_main, synthesize_benchmark_corpus
from bench.mined.miner import ReviewMiner
from bench.schema import (
    BenchmarkCase,
    FindingCategory,
    FindingSeverity,
    load_cases_from_file,
)


# =====================================================================
# 1. BugInjector Tests
# =====================================================================

class TestBugInjector:

    @pytest.fixture
    def injector(self):
        return BugInjector()

    def test_invert_comparison_python(self, injector):
        code = "def check(x):\n    if x > 0:\n        return True\n    return False\n"
        case = injector.inject_bug(code, "invert_comparison", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.BUG
        assert gt.severity == FindingSeverity.CRITICAL
        assert "Inverted comparison" in gt.description
        assert "<=" in case.modified_code
        assert gt.line_start == 2
        assert gt.line_end == 2

    def test_off_by_one_python(self, injector):
        code = "def iterate(items):\n    for i in range(len(items)):\n        print(items[i])\n"
        case = injector.inject_bug(code, "off_by_one", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.BUG
        assert "Off-by-one" in gt.description
        assert "range(len(items) + 1)" in case.modified_code

    def test_none_dereference_python(self, injector):
        code = "def get_value(d):\n    return d.get('key', 'default')\n"
        case = injector.inject_bug(code, "none_dereference", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.BUG
        assert "d['key']" in case.modified_code

    def test_resource_leak_python(self, injector):
        code = "def read_file(path):\n    with open(path, 'r') as f:\n        return f.read()\n"
        case = injector.inject_bug(code, "resource_leak", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.PERFORMANCE
        assert "Resource leak" in gt.description
        assert "f = open(path, 'r')" in case.modified_code

    def test_unsafe_command_sink_python(self, injector):
        code = "import subprocess\ndef ping(host):\n    return subprocess.run(['ping', host])\n"
        case = injector.inject_bug(code, "unsafe_command_sink", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.SECURITY
        assert "Command injection" in gt.description
        assert "shell=True" in case.modified_code

    def test_swallowed_exception_python(self, injector):
        code = "def parse(x):\n    try:\n        return int(x)\n    except (ValueError, TypeError) as e:\n        raise\n"
        case = injector.inject_bug(code, "swallowed_exception", language="python")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        gt = case.ground_truth[0]
        assert gt.category == FindingCategory.BUG
        assert "Swallowed exception" in gt.description
        assert "except:" in case.modified_code

    def test_typescript_loose_equality(self, injector):
        code = "export function isSame(a: string, b: string): boolean {\n    return a === b;\n}\n"
        case = injector.inject_bug(code, "loose_equality", language="typescript")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        assert "===" not in case.modified_code
        assert "==" in case.modified_code

    def test_typescript_missing_await(self, injector):
        code = "export async function run(): Promise<void> {\n    await service.call();\n}\n"
        case = injector.inject_bug(code, "missing_await", language="typescript")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        assert "await service.call()" not in case.modified_code
        assert "service.call()" in case.modified_code

    def test_typescript_unhandled_promise(self, injector):
        code = "export function load(): void {\n    fetch('/api').then(r => r.json()).catch(err => console.error(err));\n}\n"
        case = injector.inject_bug(code, "unhandled_promise", language="typescript")

        assert case.is_clean_diff is False
        assert len(case.ground_truth) == 1
        assert ".catch(" not in case.modified_code

    def test_unsupported_operator_raises(self, injector):
        with pytest.raises(ValueError, match="Unknown mutation operator"):
            injector.inject_bug("x = 1", "nonexistent_operator", language="python")

    def test_generate_seed_cases(self, injector):
        py_seeds = injector.generate_seed_cases("python")
        ts_seeds = injector.generate_seed_cases("typescript")
        assert len(py_seeds) >= 15
        assert len(ts_seeds) >= 6
        for c in py_seeds + ts_seeds:
            assert c.is_clean_diff is False
            assert len(c.ground_truth) >= 1


# =====================================================================
# 2. CleanDiffGenerator Tests
# =====================================================================

class TestCleanDiffGenerator:

    @pytest.fixture
    def clean_gen(self):
        return CleanDiffGenerator()

    def test_reformat_whitespace(self, clean_gen):
        code = "def calc(a, b):\n    x=a+b\n    return x\n"
        case = clean_gen.generate_clean_diff(code, "reformat_whitespace", language="python")

        assert case.is_clean_diff is True
        assert len(case.ground_truth) == 0
        assert "x = a+b" in case.modified_code or " = " in case.modified_code
        assert case.diff != ""

    def test_add_docstrings(self, clean_gen):
        code = "def process_data(items):\n    return [x for x in items if x]\n"
        case = clean_gen.generate_clean_diff(code, "add_docstrings", language="python")

        assert case.is_clean_diff is True
        assert len(case.ground_truth) == 0
        assert '"""' in case.modified_code
        assert case.diff != ""

    def test_add_type_hints(self, clean_gen):
        code = "def calculate_sum(a, b):\n    return a + b\n"
        case = clean_gen.generate_clean_diff(code, "add_type_hints", language="python")

        assert case.is_clean_diff is True
        assert len(case.ground_truth) == 0
        assert "a: Any, b: Any" in case.modified_code
        assert case.diff != ""

    def test_safe_rename(self, clean_gen):
        code = "def compute_items(items):\n    res = []\n    for x in items:\n        res.append(x)\n    return res\n"
        case = clean_gen.generate_clean_diff(code, "safe_rename", language="python")

        assert case.is_clean_diff is True
        assert len(case.ground_truth) == 0
        assert "result" in case.modified_code
        assert case.diff != ""

    def test_add_unit_tests(self, clean_gen):
        code = "def is_valid(x):\n    return x > 0\n"
        case = clean_gen.generate_clean_diff(code, "add_unit_tests", language="python")

        assert case.is_clean_diff is True
        assert len(case.ground_truth) == 0
        assert "test_module_behavior" in case.modified_code
        assert case.diff != ""

    def test_clean_seed_cases(self, clean_gen):
        py_seeds = clean_gen.generate_seed_cases("python")
        ts_seeds = clean_gen.generate_seed_cases("typescript")
        assert len(py_seeds) >= 10
        assert len(ts_seeds) >= 5
        for c in py_seeds + ts_seeds:
            assert c.is_clean_diff is True
            assert len(c.ground_truth) == 0
            assert c.diff != ""


# =====================================================================
# 3. ReviewMiner Tests
# =====================================================================

class TestReviewMiner:

    @pytest.fixture
    def miner(self):
        return ReviewMiner()

    def test_chatter_filtering(self, miner):
        # Social chatter phrases must be filtered out
        assert not miner.is_actionable_comment("LGTM!")
        assert not miner.is_actionable_comment("looks good to me")
        assert not miner.is_actionable_comment("thanks")
        assert not miner.is_actionable_comment("thank you very much!")
        assert not miner.is_actionable_comment("approved")
        assert not miner.is_actionable_comment("+1")
        assert not miner.is_actionable_comment("done.")
        assert not miner.is_actionable_comment("fixed")
        assert not miner.is_actionable_comment("great catch!")

        # Substantive engineering comments must pass
        assert miner.is_actionable_comment("This will throw a NullPointerException when user is null.")
        assert miner.is_actionable_comment("Missing await keyword on database query promise.")
        assert miner.is_actionable_comment("SQL injection vulnerability: format string used in cursor.execute.")
        assert miner.is_actionable_comment("Potential memory leak because figure is not closed in finally block.")

    def test_subsequent_commit_enforcement(self, miner):
        record_without_commit = {
            "case_id": "test-no-commit",
            "comment": "You should use a dictionary here instead of linear scan.",
            "has_subsequent_commit": False,
            "original_code": "x = 1\n",
            "modified_code": "x = 2\n",
            "language": "python",
        }
        assert miner.mine_raw_record(record_without_commit) is None

        record_with_commit = {
            "case_id": "test-with-commit",
            "comment": "You should use a dictionary here instead of linear scan.",
            "has_subsequent_commit": True,
            "original_code": "x = 1\n",
            "modified_code": "x = 2\n",
            "language": "python",
            "line_number": 1,
        }
        case = miner.mine_raw_record(record_with_commit)
        assert case is not None
        assert case.case_id == "test-with-commit"
        assert len(case.ground_truth) == 1

    def test_category_classification(self, miner):
        cat_sec, sev_sec, _ = miner.classify_comment_category("SQL injection vulnerability in query construction.")
        assert cat_sec == FindingCategory.SECURITY
        assert sev_sec == FindingSeverity.CRITICAL

        cat_perf, sev_perf, _ = miner.classify_comment_category("This nested loop causes quadratic O(n^2) performance.")
        assert cat_perf == FindingCategory.PERFORMANCE
        assert sev_perf == FindingSeverity.MAJOR

        cat_style, _, _ = miner.classify_comment_category("Please adhere to PEP 8 naming convention.")
        assert cat_style == FindingCategory.STYLE

        cat_bug, _, _ = miner.classify_comment_category("This logic causes an unexpected null crash.")
        assert cat_bug == FindingCategory.BUG

    def test_bundled_cases(self, miner):
        bundled = miner.get_bundled_mined_cases()
        assert len(bundled) == 50

        py_cases = miner.get_bundled_mined_cases(language="python")
        ts_cases = miner.get_bundled_mined_cases(language="typescript")

        assert len(py_cases) >= 20
        assert len(ts_cases) >= 20
        assert len(py_cases) + len(ts_cases) == 50

        for c in bundled:
            assert c.is_clean_diff is False
            assert len(c.ground_truth) == 1
            assert c.ground_truth[0].line_start >= 1


# =====================================================================
# 4. Corpus Synthesizer End-to-End Tests
# =====================================================================

class TestCorpusSynthesizer:

    def test_synthesize_target_200_minimum(self):
        cases = synthesize_benchmark_corpus(target_count=200, seed=123)
        assert len(cases) >= 200

        # Check clean diffs (measured for FPR)
        clean_cases = [c for c in cases if c.is_clean_diff]
        buggy_cases = [c for c in cases if not c.is_clean_diff]

        assert len(clean_cases) >= 50
        assert len(buggy_cases) >= 120

        # Check language diversity
        py_cases = [c for c in cases if c.language == "python"]
        ts_cases = [c for c in cases if c.language in ("typescript", "javascript")]

        assert len(py_cases) >= 80
        assert len(ts_cases) >= 80

        # Every case must be validated against Pydantic schema
        for c in cases:
            BenchmarkCase.model_validate(c)

    def test_synthesize_cli_execution(self, tmp_path):
        output_file = tmp_path / "test_synth_cases.json"
        exit_code = synth_main([
            "--target", "200",
            "--output", str(output_file),
            "--seed", "99",
        ])
        assert exit_code == 0
        assert output_file.exists()

        loaded = load_cases_from_file(output_file)
        assert len(loaded) >= 200
