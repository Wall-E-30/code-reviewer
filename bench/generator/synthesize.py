"""
bench/generator/synthesize.py

Corpus Synthesizer for Aion-Bench (BENCH-02, BENCH-03).
Combines:
  1. Synthetic Injected Bugs (~50%)
  2. Clean-Diff Negatives (~30%, measuring False-Positive Rate)
  3. Mined Real PR Reviews (~20%)
Produces an evaluation dataset of at least 200 verifiable BenchmarkCase records
spanning Python and TypeScript.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from bench.generator.clean import CleanDiffGenerator
from bench.generator.injector import BugInjector
from bench.mined.miner import ReviewMiner
from bench.schema import BenchmarkCase, save_cases_to_file


# =====================================================================
# Rich Snippet Templates for Parameterized Synthesis
# =====================================================================

PARAMETRIC_BUG_TEMPLATES_PYTHON = [
    # Invert comparison
    ("invert_comparison", "def validate_port(port):\n    if port >= 1024 and port <= 65535:\n        return True\n    return False\n"),
    ("invert_comparison", "def check_credit(score, min_required):\n    if score > min_required:\n        return 'approved'\n    return 'denied'\n"),
    ("invert_comparison", "def is_active_member(user):\n    if user.status == 'active':\n        return True\n    return False\n"),
    ("invert_comparison", "def within_tolerance(delta, threshold):\n    if delta < threshold:\n        return True\n    return False\n"),
    ("invert_comparison", "def has_role(role, authorized_roles):\n    if role in authorized_roles:\n        return True\n    return False\n"),
    ("invert_comparison", "def is_non_empty(container):\n    if len(container) != 0:\n        return True\n    return False\n"),
    ("invert_comparison", "def verify_checksum(calc, expected):\n    if calc == expected:\n        return True\n    return False\n"),
    ("invert_comparison", "def check_retry_count(attempt, max_attempts):\n    if attempt <= max_attempts:\n        return True\n    return False\n"),
    ("invert_comparison", "def is_safe_temperature(temp):\n    if temp >= 0 and temp <= 100:\n        return 'normal'\n    return 'warning'\n"),
    ("invert_comparison", "def is_admin_authorized(user, scope):\n    if user.is_admin and scope == 'all':\n        return True\n    return False\n"),

    # Off by one
    ("off_by_one", "def get_matrix_row(matrix, idx):\n    if idx < len(matrix):\n        return matrix[idx]\n    return None\n"),
    ("off_by_one", "def print_buffer(buffer):\n    for i in range(len(buffer)):\n        sys.stdout.write(buffer[i])\n"),
    ("off_by_one", "def chunk_records(records, chunk_size):\n    for i in range(len(records)):\n        yield records[i]\n"),
    ("off_by_one", "def process_page(items, page_size):\n    for idx in range(page_size):\n        handle(items[idx])\n"),
    ("off_by_one", "def inspect_chars(word):\n    for i in range(len(word)):\n        print(word[i])\n"),
    ("off_by_one", "def sum_first_k(elements, k):\n    total = 0\n    for idx in range(k):\n        total += elements[idx]\n    return total\n"),
    ("off_by_one", "def fetch_window(stream, window_len):\n    for i in range(len(stream)):\n        emit(stream[i])\n"),
    ("off_by_one", "def validate_index_bounds(pos, array):\n    if pos < len(array):\n        return True\n    return False\n"),

    # None dereference
    ("none_dereference", "def read_header(headers):\n    return headers.get('authorization', 'Bearer anonymous')\n"),
    ("none_dereference", "def get_retry_policy(cfg):\n    return cfg.get('max_retries', 3)\n"),
    ("none_dereference", "def get_db_port(settings):\n    return settings.get('port', 5432)\n"),
    ("none_dereference", "def retrieve_cache_ttl(options):\n    return options.get('ttl', 300)\n"),
    ("none_dereference", "def extract_currency(payment):\n    return payment.get('currency', 'USD')\n"),
    ("none_dereference", "def get_user_locale(profile):\n    return profile.get('locale', 'en-US')\n"),
    ("none_dereference", "def get_page_limit(params):\n    return params.get('limit', 50)\n"),
    ("none_dereference", "def fetch_api_version(client_conf):\n    return client_conf.get('api_version', 'v1')\n"),

    # Resource leak
    ("resource_leak", "def load_config_data(path):\n    with open(path, 'r', encoding='utf-8') as f:\n        return json.load(f)\n"),
    ("resource_leak", "def write_manifest(manifest_path, content):\n    with open(manifest_path, 'w', encoding='utf-8') as f:\n        f.write(content)\n"),
    ("resource_leak", "def save_checkpoint(ckpt_path, blob):\n    with open(ckpt_path, 'wb') as f:\n        f.write(blob)\n"),
    ("resource_leak", "def export_csv_data(filepath, rows):\n    with open(filepath, 'w', newline='') as f:\n        writer = csv.writer(f)\n        writer.writerows(rows)\n"),
    ("resource_leak", "def read_binary_signature(sig_file):\n    with open(sig_file, 'rb') as f:\n        return f.read(32)\n"),
    ("resource_leak", "def append_audit_log(log_path, entry):\n    with open(log_path, 'a', encoding='utf-8') as f:\n        f.write(entry + '\\n')\n"),

    # Unsafe command sink
    ("unsafe_command_sink", "import subprocess\ndef execute_tar(archive, target_dir):\n    return subprocess.run(['tar', '-xzf', archive, '-C', target_dir], check=True)\n"),
    ("unsafe_command_sink", "import subprocess\ndef run_git_status(repo_dir):\n    return subprocess.run(['git', 'status', repo_dir], capture_output=True)\n"),
    ("unsafe_command_sink", "def get_account_balance(cursor, account_id):\n    return cursor.execute('SELECT balance FROM accounts WHERE id = ?', (account_id,))\n"),
    ("unsafe_command_sink", "def find_order_by_ref(cursor, order_ref):\n    return cursor.execute('SELECT * FROM orders WHERE ref = ?', (order_ref,))\n"),
    ("unsafe_command_sink", "import subprocess\ndef execute_grep(pattern, file_path):\n    return subprocess.run(['grep', '-n', pattern, file_path], capture_output=True)\n"),
    ("unsafe_command_sink", "def lookup_session_token(cursor, token):\n    cursor.execute('SELECT user_id FROM sessions WHERE token = ?', (token,))\n    return cursor.fetchone()\n"),

    # Swallowed exception
    ("swallowed_exception", "def convert_timestamp(epoch_str):\n    try:\n        return int(epoch_str)\n    except (ValueError, TypeError) as err:\n        raise ValueError('Invalid epoch format') from err\n"),
    ("swallowed_exception", "def read_json_dict(raw):\n    try:\n        return json.loads(raw)\n    except json.JSONDecodeError as exc:\n        logger.warning(exc)\n        raise\n"),
    ("swallowed_exception", "def send_metric_packet(socket, packet):\n    try:\n        socket.send(packet)\n    except (OSError, socket.error) as net_err:\n        reconnect()\n        raise net_err\n"),
    ("swallowed_exception", "def parse_port_int(port_str):\n    try:\n        return int(port_str)\n    except (ValueError, TypeError) as parse_err:\n        logger.error('Port parse failure')\n        raise parse_err\n"),
]

PARAMETRIC_BUG_TEMPLATES_TYPESCRIPT = [
    # Loose equality
    ("loose_equality", "export function isAuthorizedUser(token: string, secret: string): boolean {\n    return token === secret;\n}\n"),
    ("loose_equality", "export function isCompleted(status: string): boolean {\n    return status === 'completed';\n}\n"),
    ("loose_equality", "export function isValidStatus(code: number): boolean {\n    return code !== 500;\n}\n"),
    ("loose_equality", "export function checkUserRole(role: string): boolean {\n    return role === 'admin';\n}\n"),
    ("loose_equality", "export function verifySignature(calc: string, sig: string): boolean {\n    return calc === sig;\n}\n"),
    ("loose_equality", "export function isZero(val: number): boolean {\n    return val === 0;\n}\n"),
    ("loose_equality", "export function isExpectedType(t: string): boolean {\n    return t === 'standard';\n}\n"),
    ("loose_equality", "export function matchesTarget(a: string, b: string): boolean {\n    return a !== b;\n}\n"),

    # Missing await
    ("missing_await", "export async function getDocumentById(docId: string): Promise<Doc> {\n    const doc = await repository.fetch(docId);\n    return doc;\n}\n"),
    ("missing_await", "export async function persistLogEntry(entry: Log): Promise<void> {\n    await storage.write(entry);\n    console.log('Logged');\n}\n"),
    ("missing_await", "export async function queryAccountBalance(id: string): Promise<number> {\n    const bal = await ledger.getBalance(id);\n    return bal;\n}\n"),
    ("missing_await", "export async function deleteTempDirectory(dir: string): Promise<void> {\n    await fs.rm(dir);\n    console.log('Removed');\n}\n"),
    ("missing_await", "export async function updateSessionCache(sid: string, data: any): Promise<void> {\n    await redis.set(sid, data);\n    console.log('Cached');\n}\n"),
    ("missing_await", "export async function signPayloadData(payload: Buffer): Promise<string> {\n    const signature = await kms.sign(payload);\n    return signature;\n}\n"),
    ("missing_await", "export async function refreshAccessToken(refreshToken: string): Promise<string> {\n    const newToken = await auth.refresh(refreshToken);\n    return newToken;\n}\n"),
    ("missing_await", "export async function invalidateCacheKey(key: string): Promise<void> {\n    await cache.delete(key);\n    console.log('Evicted');\n}\n"),

    # Unhandled promise
    ("unhandled_promise", "export function initializeDatabase(): void {\n    db.connect()\n        .then(() => logger.info('DB connected'))\n        .catch(err => logger.error('DB failed', err));\n}\n"),
    ("unhandled_promise", "export function dispatchWebhook(url: string, payload: any): void {\n    httpClient.post(url, payload)\n        .then(res => res.json())\n        .catch(error => alertAdmin(error));\n}\n"),
    ("unhandled_promise", "export function flushEventBuffer(events: Event[]): void {\n    sink.send(events)\n        .then(() => markSent())\n        .catch(err => retryBuffer(err));\n}\n"),
    ("unhandled_promise", "export function bootstrapWorker(): void {\n    worker.start()\n        .then(() => ready())\n        .catch(e => process.exit(1));\n}\n"),
    ("unhandled_promise", "export function syncCatalog(): void {\n    catalog.sync()\n        .then(() => complete())\n        .catch(err => reportSyncFailure(err));\n}\n"),
]

PARAMETRIC_CLEAN_TEMPLATES_PYTHON = [
    ("reformat_whitespace", "def compute_area(width, height):\n    area=width*height\n    return area\n"),
    ("reformat_whitespace", "def get_full_url(host, path):\n    url=host+'/'+path\n    return url\n"),
    ("reformat_whitespace", "def calculate_ratio(numerator, denominator):\n    ratio=numerator/denominator if denominator!=0 else 0.0\n    return ratio\n"),
    ("add_docstrings", "def parse_hex_color(hex_str):\n    return int(hex_str.lstrip('#'), 16)\n"),
    ("add_docstrings", "def normalize_slug(text):\n    return re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()\n"),
    ("add_docstrings", "def compute_hypotenuse(a, b):\n    return math.sqrt(a**2 + b**2)\n"),
    ("add_type_hints", "def greet_user(username):\n    return f'Welcome, {username}'\n"),
    ("add_type_hints", "def calculate_discount(price, pct):\n    return price * (1.0 - pct)\n"),
    ("add_type_hints", "def is_eligible(age, citizenship):\n    return age >= 18 and citizenship == 'US'\n"),
    ("safe_rename", "def sum_positive_elements(numbers):\n    res = []\n    for x in numbers:\n        if x > 0:\n            res.append(x)\n    return sum(res)\n"),
    ("safe_rename", "def filter_valid_keys(data_dict, allowed_keys):\n    res = {}\n    for k, v in data_dict.items():\n        if k in allowed_keys:\n            res[k] = v\n    return res\n"),
    ("add_unit_tests", "def square(n):\n    return n * n\n"),
    ("add_unit_tests", "def cube(n):\n    return n * n * n\n"),
    ("add_unit_tests", "def reverse_string(s):\n    return s[::-1]\n"),
]

PARAMETRIC_CLEAN_TEMPLATES_TYPESCRIPT = [
    ("reformat_whitespace", "export function multiplyNumbers(a: number, b: number): number {\n    const product=a*b;\n    return product;\n}\n"),
    ("reformat_whitespace", "export function buildPath(dir: string, file: string): string {\n    const fullPath=dir+'/'+file;\n    return fullPath;\n}\n"),
    ("add_docstrings", "export function truncateText(text: string, maxLen: number): string {\n    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;\n}\n"),
    ("add_docstrings", "export function roundCurrency(val: number): number {\n    return Math.round(val * 100) / 100;\n}\n"),
    ("add_type_hints", "export function parseTimeout(msString) {\n    return parseInt(msString, 10) || 5000;\n}\n"),
    ("safe_rename", "export function filterOdds(list: number[]): number[] {\n    const res = [];\n    for (const val of list) {\n        if (val % 2 !== 0) res.push(val);\n    }\n    return res;\n}\n"),
    ("add_unit_tests", "export function repeatString(str: string, count: number): string {\n    return str.repeat(count);\n}\n"),
]


# =====================================================================
# Synthesis Pipeline
# =====================================================================

def synthesize_benchmark_corpus(
    target_count: int = 250,
    seed: int = 42,
) -> List[BenchmarkCase]:
    """
    Synthesize a rich, diverse benchmark corpus meeting all Phase 2 criteria.

    Proportions:
    - ~50% Injected Bugs (Python & TypeScript)
    - ~30% Clean-Diff Negatives (Python & TypeScript)
    - ~20% Mined Real PR Reviews (Python & TypeScript)

    Guarantees >= 200 total cases.
    """
    random.seed(seed)
    injector = BugInjector()
    clean_gen = CleanDiffGenerator()
    miner = ReviewMiner()

    cases: List[BenchmarkCase] = []

    # Target allocations
    target_buggy = int(target_count * 0.50)      # e.g. 125
    target_clean = int(target_count * 0.30)      # e.g. 75
    target_mined = target_count - target_buggy - target_clean  # e.g. 50

    # -------------------------------------------------------------
    # 1. Mined Real PR Reviews (~20%)
    # -------------------------------------------------------------
    mined_cases = miner.get_bundled_mined_cases()
    # If target_mined is <= len(mined_cases), take sample/slice; else take all
    if len(mined_cases) >= target_mined:
        cases.extend(mined_cases[:target_mined])
    else:
        cases.extend(mined_cases)

    # -------------------------------------------------------------
    # 2. Clean-Diff Negatives (~30%)
    # -------------------------------------------------------------
    clean_python_target = target_clean // 2
    clean_ts_target = target_clean - clean_python_target

    clean_count = 0
    # Python clean cases
    while clean_count < clean_python_target:
        for op, tmpl in PARAMETRIC_CLEAN_TEMPLATES_PYTHON:
            if clean_count >= clean_python_target:
                break
            idx = clean_count + 1
            # Add minor variable variation for uniqueness
            code = tmpl.replace("def ", f"def v{idx}_") if "def " in tmpl else tmpl
            c = clean_gen.generate_clean_diff(
                code=code,
                operator=op,
                language="python",
                file_path=f"src/clean/py_module_{idx}.py",
                case_id=f"clean-py-{op}-{idx}",
                repository="aion/clean-controls",
            )
            cases.append(c)
            clean_count += 1

    # TypeScript clean cases
    clean_ts_count = 0
    while clean_ts_count < clean_ts_target:
        for op, tmpl in PARAMETRIC_CLEAN_TEMPLATES_TYPESCRIPT:
            if clean_ts_count >= clean_ts_target:
                break
            idx = clean_ts_count + 1
            code = tmpl.replace("function ", f"function v{idx}_")
            c = clean_gen.generate_clean_diff(
                code=code,
                operator=op,
                language="typescript",
                file_path=f"src/clean/ts_module_{idx}.ts",
                case_id=f"clean-ts-{op}-{idx}",
                repository="aion/clean-controls",
            )
            cases.append(c)
            clean_ts_count += 1

    # -------------------------------------------------------------
    # 3. Injected Bugs (~50%)
    # -------------------------------------------------------------
    bug_python_target = target_buggy // 2
    bug_ts_target = target_buggy - bug_python_target

    bug_py_count = 0
    while bug_py_count < bug_python_target:
        for op, tmpl in PARAMETRIC_BUG_TEMPLATES_PYTHON:
            if bug_py_count >= bug_python_target:
                break
            idx = bug_py_count + 1
            code = tmpl.replace("def ", f"def v{idx}_") if "def " in tmpl else tmpl
            try:
                c = injector.inject_bug(
                    code=code,
                    operator=op,
                    language="python",
                    file_path=f"src/injected/py_vuln_{idx}.py",
                    case_id=f"inj-py-{op}-{idx}",
                    repository="aion/synthetic-bench",
                )
                cases.append(c)
                bug_py_count += 1
            except Exception:
                continue

    bug_ts_count = 0
    while bug_ts_count < bug_ts_target:
        for op, tmpl in PARAMETRIC_BUG_TEMPLATES_TYPESCRIPT:
            if bug_ts_count >= bug_ts_target:
                break
            idx = bug_ts_count + 1
            code = tmpl.replace("function ", f"function v{idx}_")
            try:
                c = injector.inject_bug(
                    code=code,
                    operator=op,
                    language="typescript",
                    file_path=f"src/injected/ts_vuln_{idx}.ts",
                    case_id=f"inj-ts-{op}-{idx}",
                    repository="aion/synthetic-bench",
                )
                cases.append(c)
                bug_ts_count += 1
            except Exception:
                continue

    # Shuffle cases reproducibly
    random.shuffle(cases)

    # Validate all cases against schema
    for c in cases:
        BenchmarkCase.model_validate(c)

    return cases


def print_corpus_summary(cases: List[BenchmarkCase]) -> None:
    """Print structured summary table of the synthesized corpus."""
    total = len(cases)
    clean_count = sum(1 for c in cases if c.is_clean_diff)
    buggy_count = total - clean_count

    languages: Dict[str, int] = {}
    for c in cases:
        languages[c.language] = languages.get(c.language, 0) + 1

    sources: Dict[str, int] = {}
    for c in cases:
        s = c.metadata.get("source") or c.metadata.get("synthesizer") or "other"
        sources[s] = sources.get(s, 0) + 1

    print("\n" + "=" * 65)
    print(" AION-BENCH CORPUS SYNTHESIS SUMMARY")
    print("=" * 65)
    print(f" Total Synthesized Cases: {total:<6}")
    print(f" Clean-Diff Negatives:    {clean_count:<6} ({clean_count / total * 100:.1f}%) [FPR Control]")
    print(f" Buggy Diffs:             {buggy_count:<6} ({buggy_count / total * 100:.1f}%) [Recall Target]")
    print("-" * 65)
    print(" Language Distribution:")
    for lang, cnt in languages.items():
        print(f"   - {lang:<14}: {cnt:<5} ({cnt / total * 100:.1f}%)")
    print("-" * 65)
    print(" Source Distribution:")
    for src, cnt in sources.items():
        print(f"   - {src:<20}: {cnt:<5} ({cnt / total * 100:.1f}%)")
    print("=" * 65 + "\n")


# =====================================================================
# CLI Entrypoint
# =====================================================================

def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aion-Bench Corpus Synthesizer: Generates >= 200 benchmark cases across Python and TypeScript."
    )
    parser.add_argument(
        "--target",
        type=int,
        default=250,
        help="Target number of benchmark cases to generate (default: 250, minimum 200).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/benchmark_cases_raw.json",
        help="Output JSON filepath (default: data/benchmark_cases_raw.json).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic reproducibility (default: 42).",
    )
    return parser.parse_args(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    target = max(200, args.target)

    print(f"[*] Synthesizing Aion-Bench corpus (target={target}, seed={args.seed})...")
    cases = synthesize_benchmark_corpus(target_count=target, seed=args.seed)

    output_path = Path(args.output)
    save_cases_to_file(cases, output_path)
    print(f"[+] Saved {len(cases)} validated cases to {output_path}")

    print_corpus_summary(cases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
