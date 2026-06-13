import re
import ast

GRADIO_LANG_MAP = {
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "java": "java", "cpp": "cpp", "c": "c", "go": "go", "rust": "rust",
    "ruby": "ruby", "kotlin": "kotlin", "swift": "swift", "csharp": "csharp",
    "php": "php", "html": "html", "css": "css", "sql": "sql", "bash": "bash"
}

def detect_language(code: str) -> str:
    """Auto-detect programming language from syntax cues using keyword scoring."""
    if not code or not code.strip():
        return "python"
    
    scores = {lang: 0 for lang in GRADIO_LANG_MAP}
    
    # Python signals
    if re.search(r'\bdef\s+\w+\s*\(', code): scores["python"] += 3
    if re.search(r'\bimport\s+\w+', code) and 'from' not in code.split('\n')[0] if code.split('\n') else True: scores["python"] += 1
    if re.search(r'from\s+\w+\s+import', code): scores["python"] += 3
    if re.search(r':\s*$', code, re.MULTILINE): scores["python"] += 2
    if 'print(' in code: scores["python"] += 1
    if re.search(r'elif\s+', code): scores["python"] += 3
    if '"""' in code or "'''" in code: scores["python"] += 2
    if re.search(r'\bself\.\w+', code): scores["python"] += 2
    
    # JavaScript signals
    if re.search(r'\b(const|let|var)\s+\w+', code): scores["javascript"] += 2
    if re.search(r'\bfunction\s+\w+\s*\(', code): scores["javascript"] += 3
    if '=>' in code: scores["javascript"] += 2
    if 'console.log(' in code: scores["javascript"] += 3
    if re.search(r'\brequire\s*\(', code): scores["javascript"] += 2
    if 'document.' in code or 'window.' in code: scores["javascript"] += 2
    
    # TypeScript signals (inherits JS + type annotations)
    if re.search(r':\s*(string|number|boolean|void|any)\b', code): scores["typescript"] += 4
    if re.search(r'\binterface\s+\w+', code): scores["typescript"] += 4
    if re.search(r'<\w+>', code) and (re.search(r'\b(const|let)\b', code)): scores["typescript"] += 2
    
    # Java signals
    if re.search(r'\bpublic\s+(static\s+)?(?:void|int|String|class)\b', code): scores["java"] += 4
    if re.search(r'\bsystem\.(out|io|err)\.print', code, re.IGNORECASE): scores["java"] += 3
    if re.search(r'\bclass\s+\w+\s*\{', code) and ';' in code: scores["java"] += 2
    if re.search(r'\bnew\s+\w+\s*\(', code) and ';' in code: scores["java"] += 1
    if re.search(r'\bimport\s+java\.', code): scores["java"] += 4
    if 'ArrayList' in code or 'HashMap' in code: scores["java"] += 3
    
    # C++ signals
    if re.search(r'#include\s*<\w+>', code): scores["cpp"] += 4
    if 'cout' in code or 'cin' in code: scores["cpp"] += 3
    if 'std::' in code: scores["cpp"] += 3
    if re.search(r'\busing\s+namespace\s+std', code): scores["cpp"] += 3
    if re.search(r'\bvector\s*<', code) or 'unordered_map' in code: scores["cpp"] += 3
    if re.search(r'\bint\s+main\s*\(', code): scores["cpp"] += 2
    
    # C signals
    if re.search(r'#include\s*<stdio\.h>', code): scores["c"] += 5
    if re.search(r'#include\s*<stdlib\.h>', code): scores["c"] += 4
    if 'printf(' in code or 'scanf(' in code: scores["c"] += 3
    if re.search(r'\bint\s+main\s*\(', code) and 'cout' not in code and 'std::' not in code: scores["c"] += 2
    if 'malloc(' in code or 'free(' in code: scores["c"] += 3
    
    # Go signals
    if re.search(r'\bfunc\s+\w+\s*\(', code): scores["go"] += 3
    if 'fmt.Print' in code or 'fmt.Scan' in code: scores["go"] += 4
    if re.search(r'\bpackage\s+\w+', code): scores["go"] += 4
    if ':=' in code: scores["go"] += 3
    if re.search(r'\bgo\s+\w+', code): scores["go"] += 2
    
    # Rust signals
    if re.search(r'\bfn\s+\w+\s*\(', code): scores["rust"] += 3
    if 'println!(' in code or 'eprintln!(' in code: scores["rust"] += 4
    if re.search(r'\blet\s+mut\s+', code): scores["rust"] += 4
    if re.search(r'\bimpl\s+\w+', code): scores["rust"] += 3
    if '&str' in code or '&self' in code: scores["rust"] += 3
    if re.search(r'\buse\s+std::', code): scores["rust"] += 3
    
    # Ruby signals
    if re.search(r'\bputs\s+', code): scores["ruby"] += 3
    if re.search(r'\bdef\s+\w+', code) and re.search(r'\bend\b', code): scores["ruby"] += 3
    if re.search(r'\brequire\s+["\']', code): scores["ruby"] += 3
    if re.search(r'\bdo\s*\|', code): scores["ruby"] += 3
    if '.each' in code or '.map' in code: scores["ruby"] += 1
    if re.search(r'@\w+', code) and 'self.' not in code: scores["ruby"] += 2
    
    # Kotlin signals
    if re.search(r'\bfun\s+\w+\s*\(', code): scores["kotlin"] += 3
    if re.search(r'\bval\s+\w+', code) or re.search(r'\bvar\s+\w+\s*:', code): scores["kotlin"] += 3
    if 'println(' in code and 'System.out' not in code: scores["kotlin"] += 3
    if re.search(r'\bwhen\s*\(', code): scores["kotlin"] += 3
    if re.search(r'\bimport\s+kotlin\.', code): scores["kotlin"] += 4
    
    # Swift signals
    if re.search(r'\bfunc\s+\w+\s*\(', code) and re.search(r'\b(let|var)\s+\w+', code): scores["swift"] += 3
    if 'print(' in code and re.search(r'\b(let|var)\s+\w+\s*:', code): scores["swift"] += 2
    if re.search(r'\bguard\s+', code): scores["swift"] += 4
    if re.search(r'\bimport\s+Foundation', code) or re.search(r'\bimport\s+UIKit', code): scores["swift"] += 5
    if re.search(r'\bstruct\s+\w+\s*\{', code) and re.search(r'\bvar\s+\w+\s*:', code): scores["swift"] += 2
    
    # C# signals
    if re.search(r'\busing\s+System', code): scores["csharp"] += 5
    if re.search(r'\bnamespace\s+\w+', code): scores["csharp"] += 3
    if 'Console.Write' in code: scores["csharp"] += 4
    if re.search(r'\bstatic\s+void\s+Main\s*\(', code): scores["csharp"] += 4
    if re.search(r'\bclass\s+\w+\s*\{', code) and 'Console' in code: scores["csharp"] += 2
    
    # PHP signals
    if '<?php' in code: scores["php"] += 5
    if re.search(r'\$\w+\s*=', code): scores["php"] += 3
    if 'echo ' in code and ';' in code: scores["php"] += 1
    
    # HTML signals
    if '<html' in code or '<div' in code or '<body' in code or '<!DOCTYPE' in code: scores["html"] += 5
    if 'href=' in code or 'src=' in code: scores["html"] += 2
    
    # CSS signals
    if re.search(r'^\s*[\.\#]?\w+\s*\{[^}]*\}', code, re.MULTILINE): scores["css"] += 5
    
    # SQL signals
    if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\b', code, re.IGNORECASE): scores["sql"] += 5
    
    # Bash signals
    if '#!/bin/' in code: scores["bash"] += 5
    if 'echo ' in code and 'printf' not in code: scores["bash"] += 1

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        clean_code = code.strip()
        has_semicolon = clean_code.endswith(';') or ';' in clean_code
        has_braces = '{' in clean_code and '}' in clean_code
        has_c_comment = '//' in clean_code or '/*' in clean_code
        
        if 'system' in clean_code.lower() and ('print' in clean_code.lower() or 'out' in clean_code.lower() or 'io' in clean_code.lower()):
            if 'out' in clean_code.lower():
                return "java"
            return "csharp"
            
        if has_semicolon or has_braces or has_c_comment:
            if 'class ' in clean_code or 'public ' in clean_code or 'void ' in clean_code:
                return "java"
            if 'const ' in clean_code or 'let ' in clean_code or 'var ' in clean_code or 'function' in clean_code:
                return "javascript"
            return "java"
        return "python"
    return best

def fix_syntax_errors(code: str, language: str) -> str:
    """Attempt to fix common syntax errors based on the detected language."""
    if not code or not code.strip():
        return code
    
    if language == "python":
        return _fix_python_syntax(code)
    elif language in ("javascript", "typescript"):
        return _fix_js_syntax(code)
    elif language in ("java", "csharp", "kotlin"):
        return _fix_java_like_syntax(code)
    elif language in ("c", "cpp"):
        return _fix_c_syntax(code)
    elif language == "go":
        return _fix_go_syntax(code)
    elif language == "rust":
        return _fix_rust_syntax(code)
    elif language == "ruby":
        return _fix_ruby_syntax(code)
    elif language == "swift":
        return _fix_swift_syntax(code)
    return code

def _fix_python_syntax(code: str) -> str:
    """Fix common Python syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        indent = stripped[:len(stripped) - len(lstripped)]
        
        # Fix missing colons after def/if/elif/else/for/while/class/try/except/finally/with
        if re.match(r'^(def|if|elif|for|while|class|try|except|finally|with)\b', lstripped):
            # Only add colon if no colon is present in the line (excluding comments)
            clean_line = lstripped.split('#')[0].rstrip()
            if ':' not in clean_line:
                stripped = stripped + ':'
        # 'else' without colon
        if lstripped == 'else':
            stripped = indent + 'else:'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    # Fix unclosed string quotes (simple cases)
    for quote in ['"""', "'''"]:
        count = code.count(quote)
        if count % 2 != 0:
            code += '\n' + quote
    
    return code

def _fix_js_syntax(code: str) -> str:
    """Fix common JavaScript/TypeScript syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Don't add semicolons to control structures, comments, or lines ending with { or }
        if lstripped and not lstripped.startswith('//') and not lstripped.startswith('/*'):
            if not re.match(r'^\s*(if|else|for|while|switch|function|class|const\s+\w+\s*=\s*\(|let\s+\w+\s*=\s*\(|return\s*$|try|catch|finally)\b', lstripped):
                if not lstripped.endswith((';', '{', '}', ',', '(', '*/')) and lstripped:
                    stripped = stripped + ';'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    # Balance braces
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def _fix_java_like_syntax(code: str) -> str:
    """Fix common Java/C#/Kotlin syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Add missing semicolons to statement lines
        if lstripped and not lstripped.startswith('//') and not lstripped.startswith('/*'):
            if not re.match(r'^\s*(if|else|for|while|switch|class|public|private|protected|try|catch|finally|import|package|fun|when)\b', lstripped):
                if not lstripped.endswith((';', '{', '}', ',', '(', '*/', '@')):
                    stripped = stripped + ';'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def _fix_c_syntax(code: str) -> str:
    """Fix common C/C++ syntax errors."""
    if "printf" in code or "scanf" in code:
        if "#include" not in code:
            code = "#include <stdio.h>\n" + code

    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        if lstripped and not lstripped.startswith('//') and not lstripped.startswith('/*') and not lstripped.startswith('#'):
            if not re.match(r'^\s*(if|else|for|while|switch|struct|class|namespace|using|template|try|catch)\b', lstripped):
                if not lstripped.endswith((';', '{', '}', ',', '(', '*/')):
                    stripped = stripped + ';'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def _fix_go_syntax(code: str) -> str:
    """Fix common Go syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Go: opening brace must be on same line
        if re.match(r'^\s*(func|if|else|for|switch|type|struct)\b.*[^{]$', lstripped):
            if not lstripped.endswith(('{', '}', ',', '(', ')')):
                stripped = stripped + ' {'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def _fix_rust_syntax(code: str) -> str:
    """Fix common Rust syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Add missing semicolons to Rust statements
        if lstripped and not lstripped.startswith('//'):
            if not re.match(r'^\s*(fn|if|else|for|while|match|impl|struct|enum|trait|mod|use|pub|let|loop)\b', lstripped):
                if not lstripped.endswith((';', '{', '}', ',', '(', '->')):
                    stripped = stripped + ';'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def _fix_ruby_syntax(code: str) -> str:
    """Fix common Ruby syntax errors."""
    lines = code.splitlines()
    fixed = []
    open_blocks = 0
    
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Track block openers/closers
        if re.match(r'^\s*(def|class|module|if|unless|while|until|for|do|begin|case)\b', lstripped):
            open_blocks += 1
        if lstripped == 'end':
            open_blocks -= 1
        
        fixed.append(stripped)
    
    # Add missing 'end' keywords
    while open_blocks > 0:
        fixed.append('end')
        open_blocks -= 1
    
    return '\n'.join(fixed)

def _fix_swift_syntax(code: str) -> str:
    """Fix common Swift syntax errors."""
    lines = code.splitlines()
    fixed = []
    for line in lines:
        stripped = line.rstrip()
        lstripped = stripped.lstrip()
        
        # Swift: opening brace should be on same line for func/if/etc
        if re.match(r'^\s*(func|if|else|for|while|switch|guard|class|struct|enum)\b.*[^{]$', lstripped):
            if not lstripped.endswith(('{', '}', ',', '(', ')')):
                stripped = stripped + ' {'
        
        fixed.append(stripped)
    
    code = '\n'.join(fixed)
    
    open_braces = code.count('{') - code.count('}')
    if open_braces > 0:
        code += '\n' + '}' * open_braces
    
    return code

def deep_syntax_repair(code: str) -> str:
    """Fixes common AI errors like print(Hello World) or print(hello) without quotes."""
    defined_vars = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defined_vars.add(t.id)
            elif isinstance(node, ast.arg):
                defined_vars.add(node.arg)
            elif isinstance(node, ast.FunctionDef):
                defined_vars.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined_vars.add(node.name)
    except Exception:
        pass

    builtins = {'True', 'False', 'None', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple', 'bool'}

    def replacement(match):
        content = match.group(1).strip()
        if (content.startswith("'") and content.endswith("'")) or (content.startswith('"') and content.endswith('"')):
            return match.group(0)
        
        if content in defined_vars or content in builtins or content.isdigit():
            return match.group(0)
            
        try:
            escaped = content.replace('"', '\\"').replace("'", "\\'")
            return f'print("{escaped}")'
        except Exception:
            return match.group(0)
    
    code = re.sub(r'print\(\s*([a-zA-Z_]\w*)\s*\)', replacement, code)
    code = re.sub(
        r'print\(\s*((?:[a-zA-Z_]\w*\s+)+[a-zA-Z_]\w*)\s*\)',
        lambda m: f'print("{m.group(1)}")' if not any(q in m.group(1) for q in ['"', "'"]) else m.group(0),
        code
    )
    return code

def normalize_indentation(code: str, spaces: int = 4) -> str:
    """Ensures function bodies are properly indented while preserving relative nesting."""
    lines = code.splitlines()
    if not lines:
        return ""
        
    indents = []
    for line in lines:
        stripped = line.lstrip()
        if stripped and not stripped.startswith(("#", '"""', "'''")):
            indents.append(len(line) - len(stripped))
            
    if not indents:
        return code
        
    unique_indents = sorted(list(set(indents)))
    L_0 = unique_indents[0]
    
    diffs = [unique_indents[i+1] - unique_indents[i] for i in range(len(unique_indents)-1)]
    unit = min(diffs) if diffs else 4
    if unit <= 0:
        unit = 4
        
    indented = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            indented.append("")
            continue
            
        I = len(line) - len(stripped)
        if I <= L_0:
            new_I = 0
        else:
            new_I = round((I - L_0) / unit) * spaces
            
        indented.append(" " * new_I + stripped)
        
    return "\n".join(indented)
