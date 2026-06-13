import ast
import re
import difflib
import sys
import subprocess
import tempfile
import os
import base64
import json
from typing import List, Tuple, Dict, Any

from models import Observation

# --- Baseline Tasks Definitions ---
TASKS = {
    "style-cleanup": {
        "file_name": "style.py",
        "code": (
            "import os\n"
            "import sys # Unused import\n"
            "def hello_world():\n"
            "  print(\"Hello\")\n"
            "  print(\"Indentation is wrong here\")\n\n"
            "if __name__ == \"__main__\":\n"
            "    hello_world()"
        ),
        "linter": ["Unused import 'sys' detected.", "Indentation error: expected 4 spaces, got 2."]
    },
    "efficiency-boost": {
        "file_name": "logic.py",
        "code": (
            "def find_duplicates(list_a, list_b):\n"
            "    # Very slow O(N^2) approach\n"
            "    duplicates = []\n"
            "    for item_a in list_a:\n"
            "        for item_b in list_b:\n"
            "            if item_a == item_b:\n"
            "                duplicates.append(item_a)\n"
            "    return duplicates\n\n"
            "if __name__ == \"__main__\":\n"
            "    find_duplicates([1,2], [2,3])"
        ),
        "linter": ["Nested loops detected (O(n^2)). Refactor to use a dictionary or set for O(n) lookups."]
    },
    "security-audit": {
        "file_name": "security.py",
        "code": (
            "import sqlite3\n"
            "def get_user_data(user_id):\n"
            "    conn = sqlite3.connect('users.db')\n"
            "    cursor = conn.cursor()\n"
            "    query = f\"SELECT * FROM users WHERE id = '{user_id}'\"\n"
            "    cursor.execute(query)\n"
            "    return cursor.fetchone()\n\n"
            "if __name__ == \"__main__\":\n"
            "    get_user_data('admin')"
        ),
        "linter": ["SQL Injection vulnerability. Remove f-string and use parameterized queries (?, %s, or :param)."]
    }
}

class CodeReviewEnv:
    """
    Code Reviewer RL Environment conforming to Gymnasium-like interfaces.
    Coordinates code modifications, safety sandboxing, differential testing,
    AST-based grading, and regression recovery.
    """
    def __init__(self, backtrack: bool = True):
        self.current_task_id = "style-cleanup"
        self.code = TASKS[self.current_task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        self.max_steps = 5
        self.max_score_seen = 0.01
        self.best_code = self.code
        self.best_reward = 0.01
        self.language = "python"
        self.backtrack = backtrack
        self.test_cases = []

    def reset(self, task_id: str = "style-cleanup") -> Observation:
        if task_id not in TASKS:
            task_id = "style-cleanup"
        self.current_task_id = task_id
        self.code = TASKS[task_id]["code"]
        self.original_code = self.code
        self.step_count = 0
        self.max_score_seen = 0.01
        self.best_code = self.code
        self.best_reward = 0.01
        self.language = "python"
        self.test_cases = []
        return self._get_observation()

    def state(self) -> dict:
        return {
            "task_id": self.current_task_id,
            "code_content": self.code,
            "steps_taken": self.step_count,
            "total_score": self.max_score_seen
        }

    def step(self, action) -> Tuple[Observation, float, bool, dict]:
        self.step_count += 1
        proposed_code = self.code
        
        if action.action_type == "apply_fix" and action.content:
            if action.line_number is not None:
                lines = self.code.splitlines()
                idx = action.line_number - 1
                if 0 <= idx < len(lines):
                    lines[idx] = action.content
                    proposed_code = "\n".join(lines)
                else:
                    proposed_code = action.content
            else:
                proposed_code = action.content

        # Validate syntax compiles before running further evaluation
        has_syntax_error = False
        syntax_err_msg = ""
        if self.language == "python":
            try:
                ast.parse(proposed_code)
            except SyntaxError as e:
                has_syntax_error = True
                syntax_err_msg = str(e)

        if has_syntax_error:
            # Revert to best known state or keep the broken code depending on backtrack setting
            reward = 0.01
            if self.backtrack:
                self.code = self.best_code
                regression_warning = f"[Regression Warning] Action failed due to Syntax Error: {syntax_err_msg}. Reverted to the previous best-known state."
            else:
                self.code = proposed_code
                regression_warning = f"[Syntax Error] {syntax_err_msg}."
        else:
            self.code = proposed_code
            reward = self._calculate_reward()

            if reward < self.best_reward:
                if self.backtrack:
                    self.code = self.best_code
                    regression_warning = f"[Regression Warning] Proposed change reduced quality score from {self.best_reward:.2f} to {reward:.2f}. Reverted to the previous best-known state."
                else:
                    regression_warning = f"[Regression Warning] Proposed change reduced quality score from {self.best_reward:.2f} to {reward:.2f}."
            else:
                self.best_code = proposed_code
                self.best_reward = reward
                self.max_score_seen = max(self.max_score_seen, reward)
                regression_warning = ""

        # Done if max steps reached or maximum grade obtained
        done = self.step_count >= self.max_steps or self.best_reward >= 0.98

        obs = self._get_observation()
        if regression_warning:
            obs.linter_report.append(regression_warning)

        return obs, reward, done, {"total_score": self.max_score_seen}

    def _is_code_safe_to_execute(self, code: str) -> bool:
        if not code:
            return True
        try:
            tree = ast.parse(code)
        except Exception:
            return True  # If it fails to parse, it won't execute anyway

        dangerous_modules = {
            'subprocess', 'socket', 'pty', 'ctypes', 'importlib', 'builtins',
            'requests', 'urllib', 'http', 'ftplib', 'telnetlib'
        }
        dangerous_functions = {
            'eval', 'exec', 'open', 'compile', 'getattr', 'setattr', 'delattr'
        }
        dangerous_calls = {
            'system', 'popen', 'run', 'call', 'Popen', 'spawn', 'fork'
        }

        for node in ast.walk(tree):
            # Imports checking
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in dangerous_modules:
                        return False
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in dangerous_modules:
                    return False
                for alias in node.names:
                    if alias.name in dangerous_modules or alias.name in dangerous_calls or alias.name in dangerous_functions:
                        return False
            
            # Function calls checking
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_functions or node.func.id in dangerous_calls:
                        return False
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in dangerous_functions or node.func.attr in dangerous_calls:
                        return False
                    if node.func.attr in ['__subclasses__', '__globals__', '__code__', '__func__', '__self__', '__dict__', '__builtins__']:
                        return False
                        
            # Attribute checking
            elif isinstance(node, ast.Attribute):
                if node.attr in ['__subclasses__', '__globals__', '__code__', '__func__', '__self__', '__dict__', '__builtins__']:
                    return False

        return True

    def load_custom_code(self, code: str, task_type: str, language: str = "python") -> Observation:
        self.code = code
        self.original_code = code
        self.current_task_id = task_type
        self.language = language
        self.step_count = 0
        self.best_code = code
        self.test_cases = []

        if language == "python" and self._is_code_safe_to_execute(code):
            # Build and run the test case generator inside a subprocess
            encoded_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')
            generator_script = f"""
import base64
import sys
import json
import ast
import io
from contextlib import redirect_stdout

code_str = base64.b64decode({repr(encoded_code)}).decode('utf-8')
globals_dict = {{}}

try:
    exec(code_str, globals_dict)
except Exception:
    print(json.dumps([]))
    sys.exit(0)

try:
    tree = ast.parse(code_str)
except Exception:
    print(json.dumps([]))
    sys.exit(0)

funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
test_cases = []

for f in funcs:
    func_name = f.name
    if func_name.startswith("__"):
        continue
    orig_func = globals_dict.get(func_name)
    if not orig_func or not callable(orig_func):
        continue
    
    args_count = len(f.args.args)
    arg_scenarios = []
    if args_count == 1:
        arg_scenarios = [
            ([1, 2, 3, 2, 1],),
            ([],),
            ("hello",),
            (10,)
        ]
    elif args_count == 2:
        arg_scenarios = [
            ([1, 2, 3], [2, 3, 4]),
            ([1, 1], [1, 2]),
            ([], []),
            ("abc", "bcd"),
            (5, 10)
        ]
    elif args_count == 3:
        arg_scenarios = [
            (1, 2, 3),
            ([], [], []),
            ("a", "b", "c")
        ]
    else:
        arg_scenarios = [()]

    for args in arg_scenarios:
        try:
            f_out = io.StringIO()
            with redirect_stdout(f_out):
                ret = orig_func(*args)
            stdout_val = f_out.getvalue()
            test_cases.append({{
                "func_name": func_name,
                "args": args,
                "expected_return": ret,
                "expected_stdout": stdout_val
            }})
        except Exception:
            pass

print(json.dumps(test_cases))
"""
            try:
                with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
                    f.write(generator_script)
                    f_path = f.name
                
                res = subprocess.run([sys.executable, f_path], capture_output=True, text=True, timeout=5.0)
                try:
                    os.unlink(f_path)
                except Exception:
                    pass

                if res.returncode == 0:
                    try:
                        self.test_cases = json.loads(res.stdout.strip())
                    except Exception:
                        self.test_cases = []
            except Exception:
                self.test_cases = []

        self.best_reward = self._calculate_reward()
        self.max_score_seen = self.best_reward
        return self._get_observation()

    def _strip_comments(self, code: str, lang: str) -> str:
        if not code:
            return ""
        if lang in ('python', 'ruby'):
            code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        else:
            code_no_block = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            code = re.sub(r'//.*$', '', code_no_block, flags=re.MULTILINE)

        # Standardize strings to avoid string content bypasses
        code = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', code)
        code = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "''", code)
        code = re.sub(r"`[^`\\]*(?:\\.[^`\\]*)*`", "``", code)
        return code

    def _check_nested_loops_generic(self, clean_code: str, lang: str) -> bool:
        loop_patterns = {
            'javascript': r'\bfor\b|\bwhile\b|\.forEach\b|\.map\b',
            'typescript': r'\bfor\b|\bwhile\b|\.forEach\b|\.map\b',
            'java': r'\bfor\b|\bwhile\b',
            'cpp': r'\bfor\b|\bwhile\b',
            'c': r'\bfor\b|\bwhile\b',
            'go': r'\bfor\b|\brange\b',
            'rust': r'\bfor\b|\bloop\b|\bwhile\b|\.iter\(\)',
            'ruby': r'\b(each|times|upto|downto|loop|while|for)\b',
            'kotlin': r'\bfor\b|\bwhile\b|\.forEach\b',
            'swift': r'\bfor\b|\bwhile\b|\.forEach\b',
            'csharp': r'\bfor\b|\bwhile\b|\bforeach\b',
        }
        pattern = loop_patterns.get(lang, r'\bfor\b|\bwhile\b')
        
        if lang in ('javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust', 'kotlin', 'swift', 'csharp'):
            lines = clean_code.splitlines()
            loop_depth = 0
            for line in lines:
                matches = re.findall(pattern, line)
                if matches:
                    loop_depth += len(matches)
                    if loop_depth >= 2:
                        return True
                closures = line.count('}')
                if closures > 0:
                    loop_depth = max(0, loop_depth - closures)
        else:
            lines = clean_code.splitlines()
            loop_depth = 0
            for line in lines:
                if re.search(pattern, line):
                    loop_depth += 1
                    if loop_depth >= 2:
                        return True
                if 'end' in line:
                    loop_depth = max(0, loop_depth - 1)
        return False

    def _generate_dynamic_linter_generic(self) -> List[str]:
        linter = []
        code = self.code
        lang = getattr(self, 'language', 'python')
        clean_code = self._strip_comments(code, lang)

        if self.current_task_id == "style-cleanup":
            lines = clean_code.splitlines()
            for line in lines:
                stripped = line.lstrip()
                if stripped and stripped != line:
                    indent = len(line) - len(stripped)
                    if indent % 4 != 0:
                        linter.append(f"Indentation warning: indentation level of {indent} spaces is not a multiple of 4.")
                        break
            if lang in ('javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust', 'kotlin', 'swift', 'csharp'):
                open_b = clean_code.count('{')
                close_b = clean_code.count('}')
                if open_b != close_b:
                    linter.append(f"Brace mismatch: found {open_b} opening braces and {close_b} closing braces.")
            elif lang == 'ruby':
                defs = len(re.findall(r'\bdef\b', clean_code))
                ends = len(re.findall(r'\bend\b', clean_code))
                if defs != ends:
                    linter.append(f"Block mismatch: found {defs} 'def' statements but {ends} 'end' tokens.")

        elif self.current_task_id == "efficiency-boost":
            if self._check_nested_loops_generic(clean_code, lang):
                linter.append("Nested loops detected (O(n^2)). Refactor to use a dictionary or set for O(n) lookups.")

        elif self.current_task_id == "security-audit":
            if re.search(r'(execute|query|exec)\s*\(', clean_code, re.IGNORECASE):
                if re.search(r'["\']\s*\+\s*\w+', clean_code) or re.search(r'\$\{', clean_code) or re.search(r'f["\']', clean_code):
                    linter.append("Potential SQL Injection vulnerability. Do not use string concatenation or interpolation in database queries.")

            dangerous_patterns = {
                'javascript': r'\beval\(|\bexec\(|child_process',
                'typescript': r'\beval\(|\bexec\(|child_process',
                'java': r'Runtime\.getRuntime\(\)\.exec|ProcessBuilder',
                'cpp': r'\bsystem\(|\bpopen\(',
                'c': r'\bsystem\(|\bpopen\(',
                'go': r'exec\.Command|os\.Exec',
                'rust': r'Command::new|std::process',
                'ruby': r'\bsystem\(|\bexec\(|\b`.*`',
                'kotlin': r'Runtime\.getRuntime\(\)\.exec|ProcessBuilder',
                'swift': r'Process\(\)|NSTask',
                'csharp': r'Process\.Start|System\.Diagnostics\.Process',
            }
            danger_pattern = dangerous_patterns.get(lang)
            if danger_pattern and re.search(danger_pattern, clean_code):
                linter.append("Unsafe system execution sink detected.")

        if not linter:
            linter.append("Analysis complete: No style or architectural issues detected.")
        return linter

    def _generate_dynamic_linter(self) -> List[str]:
        if hasattr(self, 'language') and self.language != "python":
            return self._generate_dynamic_linter_generic()

        linter = []
        if not self._is_code_safe_to_execute(self.code):
            linter.append("Security Warning: Dynamic code execution disabled for safety. Only static analysis was performed.")

        try:
            tree = ast.parse(self.code)
        except SyntaxError as e:
            return [f"Syntax error detected: {str(e)}"]
        except Exception:
            return ["Failed to parse code AST."]

        if self.current_task_id == "style-cleanup":
            imported_names = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names[alias.asname or alias.name] = alias.name
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imported_names[alias.asname or alias.name] = alias.name
            
            used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
            used_attrs = {node.value.id for node in ast.walk(tree) if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)}
            
            unused_imports = [name for alias, name in imported_names.items() if alias not in used_names and alias not in used_attrs]
            for unused in unused_imports:
                linter.append(f"Unused import '{unused}' detected.")

            is_indented = True
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While, ast.If, ast.With)):
                    for stmt in node.body:
                        if hasattr(stmt, 'col_offset') and stmt.col_offset != node.col_offset + 4:
                            is_indented = False
                            break
            if not is_indented:
                linter.append("Indentation error: expected exactly 4 spaces.")

            # Unused variables
            assigned_vars = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            assigned_vars[t.id] = node.lineno
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        assigned_vars[node.target.id] = node.lineno
            for var in assigned_vars:
                if var.startswith('_') or var == 'self':
                    continue
                if var not in used_names and var not in used_attrs:
                    linter.append(f"Unused variable '{var}' detected.")

            # Bare except
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    linter.append("Bare except block detected. Specify exception type.")

            # Mutable default arguments
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            linter.append(f"Mutable default argument (list/dict/set) detected in function '{node.name}'.")

            # Nested conditional depth
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    def get_if_depth(n):
                        max_child_depth = 0
                        for child in ast.iter_child_nodes(n):
                            if isinstance(child, ast.If):
                                max_child_depth = max(max_child_depth, get_if_depth(child))
                            else:
                                for grandchild in ast.walk(child):
                                    if isinstance(grandchild, ast.If):
                                        max_child_depth = max(max_child_depth, get_if_depth(grandchild))
                        return 1 + max_child_depth
                    if get_if_depth(node) >= 3:
                        linter.append("Excessive nested conditional blocks detected.")
                        break

        elif self.current_task_id == "efficiency-boost":
            all_loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
            is_nested = any(any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node) if child is not node) for node in all_loops)
            
            created_sets = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') in ['set', 'dict']:
                                created_sets.add(t.id)
                            elif isinstance(node.value, (ast.SetComp, ast.DictComp, ast.Set, ast.Dict)):
                                created_sets.add(t.id)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name) and node.value:
                        if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') in ['set', 'dict']:
                            created_sets.add(node.target.id)
                        elif isinstance(node.value, (ast.SetComp, ast.DictComp, ast.Set, ast.Dict)):
                            created_sets.add(node.target.id)
            
            uses_efficient_lookup = any(
                isinstance(node, ast.Compare) and 
                any(isinstance(op, ast.In) for op in node.ops) and 
                (getattr(node.comparators[0], 'id', '') in created_sets or 
                 isinstance(node.comparators[0], (ast.Set, ast.Dict)) or 
                 (isinstance(node.comparators[0], ast.Call) and getattr(node.comparators[0].func, 'id', '') in ['set', 'dict']))
                for node in ast.walk(tree)
            )

            if is_nested and not uses_efficient_lookup:
                linter.append("Nested loops detected (O(n^2)). Refactor to use a dictionary or set for O(n) lookups.")

        elif self.current_task_id == "security-audit":
            sql_vulnerable = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = getattr(node.func, 'attr', getattr(node.func, 'id', ''))
                    if func_name == 'execute' and len(node.args) > 0:
                        first_arg = node.args[0]
                        if isinstance(first_arg, ast.JoinedStr):
                            sql_vulnerable = True
            if sql_vulnerable:
                linter.append("SQL Injection vulnerability. Remove f-string and use parameterized queries (?, %s, or :param).")

            # Deprecated modules
            deprecated_modules = {'md5', 'sha1', 'pickle'}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in deprecated_modules:
                            linter.append(f"Use of deprecated or insecure module '{alias.name}' detected.")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in deprecated_modules:
                        linter.append(f"Use of deprecated or insecure module '{node.module}' detected.")

            # Unsafe exec shell sinks
            vulnerable_exec = False
            os_aliases = {'os'}
            os_imports = set()
            subprocess_aliases = {'subprocess'}
            subprocess_imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'os':
                            os_aliases.add(alias.asname or 'os')
                        elif alias.name == 'subprocess':
                            subprocess_aliases.add(alias.asname or 'subprocess')
                elif isinstance(node, ast.ImportFrom):
                    if node.module == 'os':
                        for name in node.names:
                            os_imports.add(name.name)
                    elif node.module == 'subprocess':
                        for name in node.names:
                            subprocess_imports.add(name.name)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    is_os_call = False
                    os_func_name = ""
                    if isinstance(node.func, ast.Name):
                        os_func_name = node.func.id
                        if os_func_name in os_imports:
                            is_os_call = True
                    elif isinstance(node.func, ast.Attribute):
                        os_func_name = node.func.attr
                        if getattr(node.func.value, 'id', '') in os_aliases:
                            is_os_call = True
                    
                    if os_func_name in ['system', 'popen'] and is_os_call:
                        vulnerable_exec = True

                    is_sub_call = False
                    sub_func_name = ""
                    if isinstance(node.func, ast.Name):
                        sub_func_name = node.func.id
                        if sub_func_name in subprocess_imports:
                            is_sub_call = True
                    elif isinstance(node.func, ast.Attribute):
                        sub_func_name = node.func.attr
                        if getattr(node.func.value, 'id', '') in subprocess_aliases:
                            is_sub_call = True
                    
                    if sub_func_name in ['run', 'call', 'Popen'] and is_sub_call:
                        for keyword in node.keywords:
                            if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                                vulnerable_exec = True

            if vulnerable_exec:
                linter.append("Unsafe shell execution sink detected (e.g., os.system or subprocess.run(shell=True)).")

        if not linter:
            linter.append("Analysis complete: No style or architectural issues detected.")
        return linter

    def _get_observation(self) -> Observation:
        task = TASKS.get(self.current_task_id, {})
        file_name = task.get("file_name", "custom.py")
        diff = self._build_diff(self.original_code, self.code)
        linter = self._generate_dynamic_linter()
        return Observation(
            file_name=file_name,
            code_content=self.code,
            diff=diff,
            linter_report=linter,
            current_task=self.current_task_id
        )

    def _build_diff(self, original: str, current: str) -> str:
        if original == current:
            return ""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile="original.py",
            tofile="current.py",
            n=0
        )
        return "".join(list(diff))

    def _verify_correctness(self, code: str) -> bool:
        if hasattr(self, 'language') and self.language == "python":
            try:
                ast.parse(code)
            except SyntaxError:
                return False
            if not self._is_code_safe_to_execute(code):
                return True

        if hasattr(self, 'language') and self.language != "python":
            if self.language == "javascript":
                try:
                    with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8") as f:
                        f.write(code)
                        f_path = f.name
                    res = subprocess.run(["node", "--check", f_path], capture_output=True, text=True, timeout=2.0)
                    os.unlink(f_path)
                    if res.returncode != 0:
                        return False
                except Exception:
                    pass
            return True

        encoded_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')
        test_script = f"""
import base64
import sys
import io
from contextlib import redirect_stdout

code_str = base64.b64decode({repr(encoded_code)}).decode('utf-8')
globals_dict = {{}}
"""
        if not (hasattr(self, 'test_cases') and self.test_cases):
            if self.current_task_id == "style-cleanup":
                test_script += """
try:
    exec(code_str, globals_dict)
    if 'hello_world' not in globals_dict:
        sys.exit(1)
    f = io.StringIO()
    with redirect_stdout(f):
        globals_dict['hello_world']()
    output = f.getvalue()
    if "Hello" not in output:
        sys.exit(1)
except Exception:
    sys.exit(1)
"""
            elif self.current_task_id == "efficiency-boost":
                test_script += """
try:
    exec(code_str, globals_dict)
    if 'find_duplicates' not in globals_dict:
        sys.exit(1)
    res1 = globals_dict['find_duplicates']([1, 2, 3], [2, 3, 4])
    res2 = globals_dict['find_duplicates']([1, 1, 2], [1, 3])
    if set(res1) != {2, 3} or set(res2) != {1}:
        sys.exit(1)
except Exception:
    sys.exit(1)
"""
            elif self.current_task_id == "security-audit":
                test_script += """
import sqlite3
import unittest.mock as mock

mock_conn = sqlite3.connect(":memory:")
try:
    mock_conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
    mock_conn.execute("INSERT INTO users VALUES ('admin', 'Administrator')")
    mock_conn.execute("INSERT INTO users VALUES ('user1', 'Normal User')")
    mock_conn.commit()
except Exception:
    pass

try:
    with mock.patch("sqlite3.connect", return_value=mock_conn):
        exec(code_str, globals_dict)
        if 'get_user_data' not in globals_dict:
            sys.exit(1)
        res = globals_dict['get_user_data']("admin")
        if not res or "admin" not in res:
            sys.exit(1)
except Exception:
    sys.exit(1)
"""
            else:
                test_script += """
try:
    exec(code_str, globals_dict)
except Exception:
    sys.exit(1)
"""
        else:
            test_script += f"""
test_cases = {repr(self.test_cases)}
try:
    exec(code_str, globals_dict)
    for tc in test_cases:
        func_name = tc["func_name"]
        args = tc["args"]
        expected_ret = tc["expected_return"]
        expected_stdout = tc["expected_stdout"]
        
        if func_name not in globals_dict:
            sys.exit(1)
        func = globals_dict[func_name]
        
        f_out = io.StringIO()
        with redirect_stdout(f_out):
            actual_ret = func(*args)
        actual_stdout = f_out.getvalue()
        
        if actual_ret != expected_ret or actual_stdout != expected_stdout:
            sys.exit(1)
except Exception:
    sys.exit(1)
"""

        try:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
                f.write(test_script)
                f_path = f.name
            
            res = subprocess.run([sys.executable, f_path], capture_output=True, text=True, timeout=5.0)
            try:
                os.unlink(f_path)
            except Exception:
                pass
            return res.returncode == 0
        except Exception:
            return False

    def _calculate_reward(self) -> float:
        if hasattr(self, 'language') and self.language != "python":
            return self._calculate_reward_generic()

        if self.current_task_id in TASKS:
            if not self._verify_correctness(self.code):
                return 0.01

        score = 0.01
        try:
            tree = ast.parse(self.code)
        except Exception:
            return 0.01

        if self.current_task_id == "style-cleanup":
            imported_names = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names[alias.asname or alias.name] = alias.name
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imported_names[alias.asname or alias.name] = alias.name
            
            used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
            used_attrs = {node.value.id for node in ast.walk(tree) if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)}
            
            unused_imports = [name for alias, name in imported_names.items() if alias not in used_names and alias not in used_attrs]
            if not unused_imports:
                score += 0.45

            is_indented = True
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While, ast.If, ast.With)):
                    for stmt in node.body:
                        if hasattr(stmt, 'col_offset') and stmt.col_offset != node.col_offset + 4:
                            is_indented = False
                            break
            if is_indented:
                score += 0.44

        elif self.current_task_id == "efficiency-boost":
            all_loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
            is_nested = any(any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node) if child is not node) for node in all_loops)
            is_nested_comp = any(
                isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) and len(node.generators) > 1
                for node in ast.walk(tree)
            )
            is_nested_loop_structure = is_nested or is_nested_comp

            created_sets = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') in ['set', 'dict']:
                                created_sets.add(t.id)
                            elif isinstance(node.value, (ast.SetComp, ast.DictComp, ast.Set, ast.Dict)):
                                created_sets.add(t.id)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name) and node.value:
                        if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') in ['set', 'dict']:
                            created_sets.add(node.target.id)
                        elif isinstance(node.value, (ast.SetComp, ast.DictComp, ast.Set, ast.Dict)):
                            created_sets.add(node.target.id)

            uses_efficient_lookup = any(
                isinstance(node, ast.Compare) and 
                any(isinstance(op, ast.In) for op in node.ops) and 
                (getattr(node.comparators[0], 'id', '') in created_sets or 
                 isinstance(node.comparators[0], (ast.Set, ast.Dict)) or 
                 (isinstance(node.comparators[0], ast.Call) and getattr(node.comparators[0].func, 'id', '') in ['set', 'dict']))
                for node in ast.walk(tree)
            )

            uses_comp = any(isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)) for node in ast.walk(tree))

            if is_nested_loop_structure:
                score = 0.30
            elif uses_efficient_lookup:
                score = 0.99
            elif uses_comp:
                score = 0.99
            elif len(all_loops) == 1:
                score = 0.99
            else:
                has_efficient_builtin = any(
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {'add', 'update', 'union', 'intersection', 'difference'}
                    for node in ast.walk(tree)
                )
                has_set_op = any(
                    isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.Sub))
                    for node in ast.walk(tree)
                )
                has_efficient_builtins = any(
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'max', 'min', 'sorted', 'sum', 'any', 'all', 'zip', 'map', 'filter', 'enumerate'}
                    for node in ast.walk(tree)
                )
                if has_efficient_builtin or has_set_op or len(created_sets) > 0:
                    score = 0.99
                elif has_efficient_builtins:
                    score = 0.90
                elif len(all_loops) == 0:
                    score = 0.90
                else:
                    score = 0.40

        elif self.current_task_id == "security-audit":
            vulnerable = False
            found_sink = False
            unsafe_vars = set()

            original_had_sink = False
            try:
                orig_tree = ast.parse(self.original_code)
                for node in ast.walk(orig_tree):
                    if isinstance(node, ast.Call):
                        if getattr(node.func, 'attr', '') == 'execute':
                            original_had_sink = True
                        elif isinstance(node.func, ast.Name) and node.func.id in ['system', 'popen', 'run', 'call', 'Popen']:
                            original_had_sink = True
                        elif isinstance(node.func, ast.Attribute) and node.func.attr in ['system', 'popen', 'run', 'call', 'Popen']:
                            original_had_sink = True
            except Exception:
                pass

            os_aliases = {'os'}
            os_imports = set()
            subprocess_aliases = {'subprocess'}
            subprocess_imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name_node in node.names:
                        if name_node.name == 'os':
                            os_aliases.add(name_node.asname or name_node.name)
                        elif name_node.name == 'subprocess':
                            subprocess_aliases.add(name_node.asname or name_node.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module == 'os':
                        for name_node in node.names:
                            if name_node.name in ['system', 'popen']:
                                os_imports.add(name_node.asname or name_node.name)
                    elif node.module == 'subprocess':
                        for name_node in node.names:
                            if name_node.name in ['run', 'call', 'Popen']:
                                subprocess_imports.add(name_node.asname or name_node.name)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(node.value, ast.JoinedStr):
                                unsafe_vars.add(target.id)
                            elif isinstance(node.value, ast.BinOp):
                                unsafe_vars.add(target.id)
                            elif isinstance(node.value, ast.Call):
                                if getattr(node.value.func, 'attr', '') == 'format':
                                    unsafe_vars.add(target.id)

                if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'execute':
                    found_sink = True
                    if node.args:
                        query_arg = node.args[0]
                        if isinstance(query_arg, (ast.JoinedStr, ast.BinOp)) or \
                           (isinstance(query_arg, ast.Call) and getattr(query_arg.func, 'attr', '') == 'format'):
                            vulnerable = True
                        elif isinstance(query_arg, ast.Name) and query_arg.id in unsafe_vars:
                            vulnerable = True
                    
                    for kw in node.keywords:
                        if isinstance(kw.value, ast.Name) and kw.value.id in unsafe_vars:
                            vulnerable = True
                        elif isinstance(kw.value, (ast.JoinedStr, ast.BinOp)):
                            vulnerable = True
                        elif isinstance(kw.value, ast.Call) and getattr(kw.value.func, 'attr', '') == 'format':
                            vulnerable = True

                if isinstance(node, ast.Call):
                    is_os_call = False
                    os_func_name = ""
                    if isinstance(node.func, ast.Name):
                        os_func_name = node.func.id
                        if os_func_name in os_imports:
                            is_os_call = True
                    elif isinstance(node.func, ast.Attribute):
                        os_func_name = node.func.attr
                        if getattr(node.func.value, 'id', '') in os_aliases:
                            is_os_call = True
                    
                    if os_func_name in ['system', 'popen'] and is_os_call:
                        found_sink = True
                        vulnerable = True

                    is_sub_call = False
                    sub_func_name = ""
                    if isinstance(node.func, ast.Name):
                        sub_func_name = node.func.id
                        if sub_func_name in subprocess_imports:
                            is_sub_call = True
                    elif isinstance(node.func, ast.Attribute):
                        sub_func_name = node.func.attr
                        if getattr(node.func.value, 'id', '') in subprocess_aliases:
                            is_sub_call = True
                    
                    if sub_func_name in ['run', 'call', 'Popen'] and is_sub_call:
                        found_sink = True
                        for keyword in node.keywords:
                            if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                                vulnerable = True
                                break

            if found_sink and not vulnerable:
                score = 0.99
            elif found_sink and vulnerable:
                score = 0.10
            else:
                if original_had_sink:
                    score = 0.10
                else:
                    score = 0.99

        # Main entry point guard bonus (0.09)
        has_main_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                test = node.test
                if isinstance(test.left, ast.Name) and test.left.id == '__name__':
                    if len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == '__main__':
                        if len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                            has_main_guard = True
                            break
        if has_main_guard:
            score += 0.09

        return round(float(max(0.01, min(0.99, score))), 2)

    def _calculate_reward_generic(self) -> float:
        score = 0.01
        code = self.code
        lang = getattr(self, 'language', 'python')
        if not code or not code.strip():
            return 0.01

        clean_code = self._strip_comments(code, lang)

        if self.current_task_id == "style-cleanup":
            lines = clean_code.splitlines()
            indent_sizes = set()
            for line in lines:
                stripped = line.lstrip()
                if stripped and stripped != line:
                    indent = len(line) - len(stripped)
                    indent_sizes.add(indent % 4 if indent > 0 else 0)
            consistent_indent = len(indent_sizes) <= 2
            if consistent_indent:
                score += 0.30

            has_naming = bool(re.search(r'\b[a-z][a-zA-Z0-9]*[A-Z]\w*\b', clean_code)) or bool(re.search(r'\b[a-z]+_[a-z]+\b', clean_code))
            if has_naming:
                score += 0.20

            has_comments = '//' in code or '/*' in code or '#' in code or '///' in code or '/**' in code
            if has_comments:
                score += 0.15

            if lang in ('javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust', 'kotlin', 'swift', 'csharp'):
                open_b = clean_code.count('{')
                close_b = clean_code.count('}')
                if open_b == close_b and open_b > 0:
                    score += 0.25
            elif lang == 'ruby':
                defs = len(re.findall(r'\bdef\b', clean_code))
                ends = len(re.findall(r'\bend\b', clean_code))
                if defs == ends:
                    score += 0.25
            else:
                score += 0.15

        elif self.current_task_id == "efficiency-boost":
            has_nested_loops = self._check_nested_loops_generic(clean_code, lang)
            loop_patterns = {
                'javascript': r'\bfor\b|\bwhile\b|\.forEach\b|\.map\b',
                'typescript': r'\bfor\b|\bwhile\b|\.forEach\b|\.map\b',
                'java': r'\bfor\b|\bwhile\b',
                'cpp': r'\bfor\b|\bwhile\b',
                'c': r'\bfor\b|\bwhile\b',
                'go': r'\bfor\b|\brange\b',
                'rust': r'\bfor\b|\bloop\b|\bwhile\b|\.iter\(\)',
                'ruby': r'\b(each|times|upto|downto|loop|while|for)\b',
                'kotlin': r'\bfor\b|\bwhile\b|\.forEach\b',
                'swift': r'\bfor\b|\bwhile\b|\.forEach\b',
                'csharp': r'\bfor\b|\bwhile\b|\bforeach\b',
            }
            pattern = loop_patterns.get(lang, r'\bfor\b|\bwhile\b')
            loop_matches = list(re.finditer(pattern, clean_code))

            if has_nested_loops:
                score = 0.30
            elif len(loop_matches) <= 1:
                score = 0.99
            else:
                score = 0.60

            efficient_patterns = {
                'javascript': r'\bSet\b|\bMap\b|\.has\(|\.includes\(',
                'typescript': r'\bSet\b|\bMap\b|\.has\(|\.includes\(',
                'java': r'\bHashSet\b|\bHashMap\b|\bTreeSet\b|\bTreeMap\b',
                'cpp': r'\bunordered_set\b|\bunordered_map\b|\bset\b|\bmap\b',
                'c': r'\bhash|\bsearch\b',
                'go': r'\bmap\[',
                'rust': r'\bHashSet\b|\bHashMap\b|\bBTreeSet\b',
                'ruby': r'\.to_set|\.include\?|Hash\.new',
                'kotlin': r'\bhashSetOf\b|\bhashMapOf\b|\bmutableSetOf\b',
                'swift': r'\bSet\b|\bDictionary\b',
                'csharp': r'\bHashSet\b|\bDictionary\b',
            }
            eff_pattern = efficient_patterns.get(lang)
            if eff_pattern and re.search(eff_pattern, clean_code):
                score = max(score, 0.99)

        elif self.current_task_id == "security-audit":
            vulnerable = False
            if re.search(r'(execute|query|exec)\s*\(', clean_code, re.IGNORECASE):
                if re.search(r'["\']\s*\+\s*\w+', clean_code) or re.search(r'\$\{', clean_code) or re.search(r'f["\']', clean_code):
                    vulnerable = True

            dangerous_patterns = {
                'javascript': r'\beval\(|\bexec\(|child_process',
                'typescript': r'\beval\(|\bexec\(|child_process',
                'java': r'Runtime\.getRuntime\(\)\.exec|ProcessBuilder',
                'cpp': r'\bsystem\(|\bpopen\(',
                'c': r'\bsystem\(|\bpopen\(',
                'go': r'exec\.Command|os\.Exec',
                'rust': r'Command::new|std::process',
                'ruby': r'\bsystem\(|\bexec\(|\b`.*`',
                'kotlin': r'Runtime\.getRuntime\(\)\.exec|ProcessBuilder',
                'swift': r'Process\(\)|NSTask',
                'csharp': r'Process\.Start|System\.Diagnostics\.Process',
            }
            danger_pattern = dangerous_patterns.get(lang)
            if danger_pattern and re.search(danger_pattern, clean_code):
                vulnerable = True

            orig_clean = self._strip_comments(self.original_code, lang)
            orig_had_sink = False
            if re.search(r'(execute|query|exec)\s*\(', orig_clean, re.IGNORECASE):
                orig_had_sink = True
            if danger_pattern and re.search(danger_pattern, orig_clean):
                orig_had_sink = True

            new_had_sink = False
            if re.search(r'(execute|query|exec)\s*\(', clean_code, re.IGNORECASE):
                new_had_sink = True
            if danger_pattern and re.search(danger_pattern, clean_code):
                new_had_sink = True

            if vulnerable:
                score = 0.10
            elif orig_had_sink and not new_had_sink:
                score = 0.10
            else:
                score = 0.99

        return round(float(max(0.01, min(0.99, score))), 2)
