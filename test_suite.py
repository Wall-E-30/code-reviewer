#!/usr/bin/env python3
"""
Comprehensive test suite for Aion Code Reviewer.
Tests the environment, scoring, and optimization logic.
"""

import sys
import asyncio
import ast
import json
from inference import (
    evaluate_and_optimize, 
    run_full_optimization,
    deep_syntax_repair,
    normalize_indentation,
    robust_repair_code,
    clean_json_string
)
from env import CodeReviewEnv
from models import Action, Observation


def test_deep_syntax_repair():
    """Test syntax repair for common errors."""
    code = 'print(Hello World)'
    result = deep_syntax_repair(code)
    assert 'print(' in result
    assert 'Hello World' in result or 'Hello' in result
    print("PASS: test_deep_syntax_repair")


def test_normalize_indentation():
    """Test indentation normalization."""
    code = "def foo():\nprint('hello')\n  print('world')"
    result = normalize_indentation(code)
    assert 'def foo():' in result
    
    # Test nested function indentation preservation
    nested_code = "def outer():\n    def inner():\n        pass\n    inner()"
    nested_result = normalize_indentation(nested_code)
    assert "    def inner():" in nested_result
    assert "        pass" in nested_result
    
    # Test nested import preservation
    nested_import = "def func():\n    import math\n    return math.sqrt(4)"
    import_result = normalize_indentation(nested_import)
    assert "    import math" in import_result
    
    # Test top-level statement preservation (current_indent == 0)
    top_level_code = "def my_func():\n    pass\nx = 10\nprint(x)"
    top_level_result = normalize_indentation(top_level_code)
    assert "x = 10" in top_level_result.splitlines()
    assert "print(x)" in top_level_result.splitlines()
    
    print("PASS: test_normalize_indentation")


def test_robust_repair_code():
    """Test robust code repair."""
    result = robust_repair_code("")
    assert 'def' in result
    assert 'pass' in result
    
    code = "def test():\n    pass"
    result = robust_repair_code(code)
    assert '__name__' in result
    print("PASS: test_robust_repair_code")


def test_clean_json_string():
    """Test JSON string cleaning."""
    # Clean JSON
    json_str = '{"action_type": "apply_fix", "content": "test"}'
    result = clean_json_string(json_str)
    parsed = json.loads(result)
    assert parsed['action_type'] == 'apply_fix'
    
    # JSON in markdown
    md_str = '```json\n{"key": "value"}\n```'
    result = clean_json_string(md_str)
    parsed = json.loads(result)
    assert parsed['key'] == 'value'
    print("PASS: test_clean_json_string")


def test_env_style_cleanup():
    """Test style-cleanup task scoring."""
    env = CodeReviewEnv()
    obs = env.reset(task_id='style-cleanup')
    
    # Test original code has low score
    original_score = env._calculate_reward()
    assert 0.01 <= original_score < 0.99
    
    # Apply fix: remove sys import, fix indentation
    fixed_code = '''def hello_world():
    print("Hello")
    print("Indentation is wrong here")

if __name__ == "__main__":
    hello_world()'''
    
    action = Action(action_type='apply_fix', content=fixed_code)
    obs, reward, done, info = env.step(action)
    
    # Should have high score
    assert reward >= 0.90
    assert reward < 1.0
    print("PASS: test_env_style_cleanup")


def test_env_efficiency_boost():
    """Test efficiency-boost task scoring."""
    env = CodeReviewEnv()
    obs = env.reset(task_id='efficiency-boost')
    
    # Test original nested loop code has medium score
    original_score = env._calculate_reward()
    assert original_score > 0.01
    
    # Apply fix: use set for O(n) lookup
    fixed_code = '''def find_duplicates(list_a, list_b):
    # Optimized: O(n) set lookup
    seen = set(list_a)
    return [x for x in list_b if x in seen]

if __name__ == "__main__":
    find_duplicates([1,2], [2,3])'''
    
    action = Action(action_type='apply_fix', content=fixed_code)
    obs, reward, done, info = env.step(action)
    
    # Should have high score
    assert reward >= 0.90
    assert reward < 1.0
    print("PASS: test_env_efficiency_boost")


def test_env_efficiency_boost_comprehensions():
    """Test that set comprehensions and annotated assignments are correctly identified by the efficiency grader."""
    env = CodeReviewEnv()
    env.reset(task_id='efficiency-boost')
    
    # 1. Test set comprehension assignment: seen = {x for x in list_a}
    code_comp = '''def find_duplicates(list_a, list_b):
    seen = {x for x in list_a}
    duplicates = []
    for x in list_b:
        if x in seen:
            duplicates.append(x)
    return duplicates

if __name__ == "__main__":
    find_duplicates([1,2], [2,3])'''
    env.load_custom_code(code_comp, 'efficiency-boost')
    assert env._calculate_reward() == 0.99, "Failed to score set comprehension correctly"

    # 2. Test annotated set assignment: seen: set = set(list_a)
    code_ann = '''def find_duplicates(list_a, list_b):
    seen: set = set(list_a)
    duplicates = []
    for x in list_b:
        if x in seen:
            duplicates.append(x)
    return duplicates

if __name__ == "__main__":
    find_duplicates([1,2], [2,3])'''
    env.load_custom_code(code_ann, 'efficiency-boost')
    assert env._calculate_reward() == 0.99, "Failed to score annotated set assignment correctly"

    # 3. Test nested comprehension loops (which are inefficient and should be penalized)
    code_nested_comp = '''def find_duplicates(list_a, list_b):
    duplicates = [x for x in list_b for y in list_a if x == y]
    return duplicates

if __name__ == "__main__":
    find_duplicates([1,2], [2,3])'''
    env.load_custom_code(code_nested_comp, 'efficiency-boost')
    assert env._calculate_reward() == 0.39, "Failed to penalize nested list comprehension"

    print("PASS: test_env_efficiency_boost_comprehensions")


def test_env_security_audit():
    """Test security-audit task scoring."""
    env = CodeReviewEnv()
    obs = env.reset(task_id='security-audit')
    
    # Test original SQL injection code has low score
    original_score = env._calculate_reward()
    assert original_score < 0.5
    
    # Apply fix: use parameterized query
    fixed_code = '''import sqlite3
def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return cursor.fetchone()

if __name__ == "__main__":
    get_user_data('admin')'''
    
    action = Action(action_type='apply_fix', content=fixed_code)
    obs, reward, done, info = env.step(action)
    print('DEBUG: reward =', reward)
    print('DEBUG: reward >= 0.85 =', reward >= 0.85)
    print('DEBUG: reward < 1.0 =', reward < 1.0)
    
    # Should have high score
    assert reward >= 0.85
    assert reward < 1.0
    print("PASS: test_env_security_audit")


def test_security_audit_direct_and_alias_detection():
    """Test that direct imports and aliases for security audit sinks are correctly detected as vulnerable."""
    env = CodeReviewEnv()
    env.reset(task_id='security-audit')
    
    # 1. Test "from os import system" vulnerable code
    vulnerable_os_direct = '''from os import system
def run_command(cmd):
    system(cmd)
'''
    env.load_custom_code(vulnerable_os_direct, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable direct import 'from os import system'"

    # 2. Test "import os as my_os" vulnerable code
    vulnerable_os_alias = '''import os as my_os
def run_command(cmd):
    my_os.system(cmd)
'''
    env.load_custom_code(vulnerable_os_alias, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable os alias 'my_os.system'"

    # 3. Test "import subprocess as sub" with shell=True vulnerable code
    vulnerable_sub_alias = '''import subprocess as sub
def run_command(cmd):
    sub.run(cmd, shell=True)
'''
    env.load_custom_code(vulnerable_sub_alias, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable subprocess alias with shell=True"

    # 4. Test "from subprocess import run" with shell=True vulnerable code
    vulnerable_sub_direct = '''from subprocess import run
def run_command(cmd):
    run(cmd, shell=True)
'''
    env.load_custom_code(vulnerable_sub_direct, 'security-audit')
    assert env._calculate_reward() == 0.10, "Failed to detect vulnerable subprocess direct import with shell=True"

    print("PASS: test_security_audit_direct_and_alias_detection")


def test_env_observation_model():
    """Test Pydantic Observation model."""
    env = CodeReviewEnv()
    obs = env.reset(task_id='style-cleanup')
    
    # Verify observation has all required fields
    assert hasattr(obs, 'file_name')
    assert hasattr(obs, 'code_content')
    assert hasattr(obs, 'diff')
    assert hasattr(obs, 'linter_report')
    assert hasattr(obs, 'current_task')
    assert isinstance(obs.file_name, str)
    assert isinstance(obs.code_content, str)
    assert isinstance(obs.diff, str)
    assert isinstance(obs.linter_report, list)
    assert isinstance(obs.current_task, str)
    print("PASS: test_env_observation_model")


def test_env_reward_bounds():
    """Test that rewards are always in (0, 1) range."""
    env = CodeReviewEnv()
    
    for task_id in ['style-cleanup', 'efficiency-boost', 'security-audit']:
        env.reset(task_id=task_id)
        
        # Test with valid code
        valid_codes = [
            ("def foo(): pass", task_id),
            ("def bar(): return 1", task_id),
        ]
        
        for code, task in valid_codes:
            env.load_custom_code(code, task)
            reward = env._calculate_reward()
            assert 0.01 <= reward <= 0.99, f"Reward {reward} out of bounds for task {task}"
        
        # Test with invalid syntax
        env.load_custom_code("def invalid(", task_id)
        reward = env._calculate_reward()
        assert reward == 0.01, f"Invalid syntax should score 0.01, got {reward}"
    
    print("PASS: test_env_reward_bounds")


def test_evaluate_and_optimize():
    """Test the evaluate_and_optimize function (mock)."""
    test_code = "import sys\nprint('test')"
    
    # This will use the mock client since no HF_TOKEN is set
    init_score, fixed_code, final_score, perf, mem, rec = asyncio.run(
        evaluate_and_optimize(test_code, "style-cleanup")
    )
    
    assert 0.0 <= init_score <= 1.0
    assert 0.0 <= final_score <= 1.0
    assert isinstance(fixed_code, str)
    assert len(fixed_code) > 0

    # Test multi-import selective cleaning
    from inference import MockOpenAI
    mock_client = MockOpenAI()
    res = mock_client.create(messages=[{"content": "LANGUAGE: python\nTASK: style-cleanup\nUSER CODE:\nimport sys, math\nx = math.sqrt(4)\nprint(x)\nReturn the COMPLETE"}])
    res_data = json.loads(res.choices[0].message.content)
    fixed_res = res_data["content"]
    assert "import math" in fixed_res
    assert "import sys" not in fixed_res

    print("PASS: test_evaluate_and_optimize")


def test_run_full_optimization():
    """Test the full optimization pipeline."""
    import inference
    orig_has_rl = inference.HAS_RL_MODEL
    inference.HAS_RL_MODEL = False
    
    test_code = "import sys\ndef find_dup(a,b):\n  for x in a:\n    for y in b:\n      if x==y: return x"
    
    try:
        init_score, fixed_code, final_score = asyncio.run(
            run_full_optimization(test_code)
        )
        
        assert 0.0 <= init_score <= 1.0
        assert 0.0 <= final_score <= 1.0
        assert isinstance(fixed_code, str)
        assert 'seen' in fixed_code
        
        # Test error resilience (failure recovery)
        err_init_score, err_fixed_code, err_final_score = asyncio.run(
            run_full_optimization("")
        )
        assert not err_fixed_code.startswith("Error:")
        assert "def " in err_fixed_code
    finally:
        inference.HAS_RL_MODEL = orig_has_rl
    
    print("PASS: test_run_full_optimization")


def test_env_backtracking_and_string_bypass():
    """Test backtracking=False option and string-bypass prevention."""
    # 1. Backtracking = False test
    env = CodeReviewEnv(backtrack=False)
    env.reset(task_id="style-cleanup")
    
    # Introduce a syntax error
    action = Action(action_type="apply_fix", content="def invalid_syntax(invalid python code here:")
    obs, reward, done, info = env.step(action)
    
    # Ensure syntax error code is NOT reverted when backtrack=False
    assert env.code == "def invalid_syntax(invalid python code here:"
    assert any("Syntax Error" in r for r in obs.linter_report)
    
    # 2. String literal bypass test
    env_js = CodeReviewEnv()
    env_js.language = "javascript"
    env_js.reset(task_id="efficiency-boost")
    
    # Try to bypass JS efficiency reward check by putting Set/Map inside comments/strings
    bypass_code = 'const my_string = "Set Map .has()";'
    env_js.load_custom_code(bypass_code, "efficiency-boost")
    # Verify reward is still low (0.01) because the comment/string literal was stripped before scoring
    reward = env_js._calculate_reward()
    assert reward == 0.01


def test_robust_parser_and_extra_languages():
    """Test robust LLM response parsing and detection of extra languages (PHP, HTML, CSS, SQL, Bash)."""
    from inference import extract_action_robustly, detect_language
    
    # 1. Test robust parser with various messy model outputs
    # JSON output with raw unescaped double quotes inside content
    raw_json_bad = '{"action_type": "apply_fix", "content": "def hello():\n    print(\"nested raw quotes\")"}'
    action = extract_action_robustly(raw_json_bad)
    assert "def hello()" in action.content
    
    # Markdown block format directly returning the code
    markdown_bad = 'Sure, here is the optimized code:\n```python\ndef hello_world():\n    pass\n```\nHope this helps!'
    action = extract_action_robustly(markdown_bad)
    assert action.content == "def hello_world():\n    pass"
    
    # Standard text-only fallback (no JSON structure at all)
    text_bad = 'def plain_func():\n    return 42'
    action = extract_action_robustly(text_bad)
    assert action.content == 'def plain_func():\n    return 42'
    
    # Test leak of PAST TRIAL HISTORY in raw output
    leaked_output = '{"action_type": "apply_fix", "content": "int main() { return 0; }\\nPAST TRIAL HISTORY (Learn from your failures...)"}'
    action_leaked = extract_action_robustly(leaked_output)
    assert action_leaked.content == "int main() { return 0; }"

    # Test syntax fixer on C function call without semicolon and missing include
    from inference import fix_syntax_errors
    c_raw = "int main(){\nint a=5;\nprintf(a)\n}"
    c_fixed = fix_syntax_errors(c_raw, "c")
    assert "#include <stdio.h>" in c_fixed
    assert "printf(a);" in c_fixed

    # 2. Test language detection extensions
    assert detect_language('<?php echo "Hello World"; ?>') == "php"
    assert detect_language('<!DOCTYPE html><html><body><div>Test</div></body></html>') == "html"
    assert detect_language('body { background-color: #ffffff; margin: 0; }') == "css"
    assert detect_language('SELECT * FROM users WHERE id = 1;') == "sql"
    assert detect_language('#!/bin/bash\necho "Scripting"') == "bash"
    assert detect_language('system.io.print(heeloo)') in ('csharp', 'java')
    assert detect_language('System.out.println("test");') == "java"
    assert detect_language('int x = 5;') == "java"


def test_custom_code_differential_testing():
    """Test that custom Python submissions are verified via differential testing."""
    env = CodeReviewEnv()
    
    custom_code = (
        "def sum_pairs(lst):\n"
        "    res = []\n"
        "    for x in lst:\n"
        "        for y in lst:\n"
        "            res.append(x + y)\n"
        "    return res\n"
    )
    
    env.load_custom_code(custom_code, "efficiency-boost", language="python")
    
    assert len(env.test_cases) > 0
    
    hacked_code = (
        "def sum_pairs(lst):\n"
        "    return []\n"
    )
    action_hack = Action(action_type="apply_fix", content=hacked_code)
    obs, reward, done, info = env.step(action_hack)
    assert reward == 0.01
    
    correct_code = (
        "def sum_pairs(lst):\n"
        "    res = []\n"
        "    for x in lst:\n"
        "        for y in lst:\n"
        "            res.append(x + y)\n"
        "    return res\n"
    )
    env.reset()
    env.load_custom_code(custom_code, "efficiency-boost", language="python")
    action_correct = Action(action_type="apply_fix", content=correct_code)
    obs2, reward2, done2, info2 = env.step(action_correct)
    assert reward2 > 0.01
    
    print("PASS: test_custom_code_differential_testing")


def test_load_custom_code_rce_blocking():
    """Test that custom code containing dangerous constructs is blocked from executing or generating test cases."""
    env = CodeReviewEnv()
    
    # Unsafe code 1: import os system call
    unsafe_code_import = (
        "import os\n"
        "def bad_func(x):\n"
        "    os.system('whoami')\n"
        "    return x\n"
    )
    obs = env.load_custom_code(unsafe_code_import, "efficiency-boost")
    assert len(env.test_cases) == 0, "Test cases should be empty for unsafe import"
    assert any("Security Warning" in msg for msg in obs.linter_report), "Observation should report a security warning"
    assert env._verify_correctness(unsafe_code_import), "Unsafe but syntactically valid code should safely bypass execution verification"

    # Unsafe code 2: eval()
    unsafe_code_eval = (
        "def bad_func(x):\n"
        "    eval('print(123)')\n"
        "    return x\n"
    )
    obs2 = env.load_custom_code(unsafe_code_eval, "efficiency-boost")
    assert len(env.test_cases) == 0
    assert any("Security Warning" in msg for msg in obs2.linter_report)
    assert env._verify_correctness(unsafe_code_eval)

    # Unsafe code 3: __subclasses__ traversal
    unsafe_code_magic = (
        "def bad_func(x):\n"
        "    [].__class__.__base__.__subclasses__()\n"
        "    return x\n"
    )
    obs3 = env.load_custom_code(unsafe_code_magic, "efficiency-boost")
    assert len(env.test_cases) == 0
    assert any("Security Warning" in msg for msg in obs3.linter_report)

    # Safe code: should pass and generate test cases
    safe_code = (
        "def good_func(x):\n"
        "    return x + 1\n"
    )
    obs_safe = env.load_custom_code(safe_code, "efficiency-boost")
    assert len(env.test_cases) > 0, "Safe code should generate test cases"
    assert env.best_reward > 0.01, "Safe code should have a valid reward score"
    print("PASS: test_load_custom_code_rce_blocking")


def test_new_ast_linter_checks():
    """Test new AST linter detections and strengthened sandbox RCE checks."""
    env = CodeReviewEnv()
    
    # 1. Test unused variables, bare excepts, mutable defaults, nested conditionals
    style_code = (
        "def test_func(a, b=[]):\n"
        "    x = 10\n"
        "    try:\n"
        "        if a > 0:\n"
        "            if a > 1:\n"
        "                if a > 2:\n"
        "                    print(a)\n"
        "    except:\n"
        "        pass\n"
    )
    obs = env.load_custom_code(style_code, "style-cleanup")
    report = obs.linter_report
    assert any("Unused variable 'x'" in msg for msg in report)
    assert any("Bare except block detected" in msg for msg in report)
    assert any("Mutable default argument" in msg for msg in report)
    assert any("Excessive nested conditional blocks" in msg for msg in report)

    # 2. Test deprecated modules under security-audit
    sec_code = (
        "import md5\n"
        "import pickle\n"
    )
    obs2 = env.load_custom_code(sec_code, "security-audit")
    report2 = obs2.linter_report
    assert any("Use of deprecated or insecure module 'md5'" in msg for msg in report2)
    assert any("Use of deprecated or insecure module 'pickle'" in msg for msg in report2)

    # 3. Test strengthened sandbox blocking for requests/urllib and __builtins__
    unsafe_code_req = (
        "import requests\n"
    )
    obs3 = env.load_custom_code(unsafe_code_req, "security-audit")
    assert len(env.test_cases) == 0
    assert any("Security Warning" in msg for msg in obs3.linter_report)

    unsafe_code_builtins = (
        "getattr(x, '__builtins__')\n"
    )
    obs4 = env.load_custom_code(unsafe_code_builtins, "security-audit")
    assert len(env.test_cases) == 0
    assert any("Security Warning" in msg for msg in obs4.linter_report)

    print("PASS: test_new_ast_linter_checks")


def main():
    """Run all tests."""
    print("="*60)
    print("Running Aion Code Reviewer Test Suite")
    print("="*60)
    
    tests = [
        test_load_custom_code_rce_blocking,
        test_custom_code_differential_testing,
        test_deep_syntax_repair,
        test_normalize_indentation,
        test_robust_repair_code,
        test_clean_json_string,
        test_env_observation_model,
        test_env_reward_bounds,
        test_env_style_cleanup,
        test_env_efficiency_boost,
        test_env_efficiency_boost_comprehensions,
        test_env_security_audit,
        test_security_audit_direct_and_alias_detection,
        test_evaluate_and_optimize,
        test_run_full_optimization,
        test_env_backtracking_and_string_bypass,
        test_robust_parser_and_extra_languages,
        test_new_ast_linter_checks,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print("PASS: %s" % test.__name__)
            passed += 1
        except AssertionError as e:
            print("FAIL: %s: %s" % (test.__name__, str(e)))
            failed += 1
        except Exception as e:
            print("ERROR: %s: %s" % (test.__name__, str(e)))
            import traceback
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print("ERROR: %s: %s" % (test.__name__, str(e)))
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*60)
    print("Results: %d passed, %d failed" % (passed, failed))
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
