"""
bench_real/collectors/base.py

Base collector framework for real-world PR evaluation cases.
Implements rate limiting, OSI license checks, and repository isolation enforcement.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
import httpx

from bench_real.schema import RealBenchmarkCase

logger = logging.getLogger(__name__)

# Permissible open-source licenses for evaluation benchmark ingestion
PERMISSIBLE_OSI_LICENSES: Set[str] = {
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "mpl-2.0",
    "unlicense",
}

# Repositories permanently blacklisted from bench_real because they appeared in training/v1.0 test sets
BLACKLISTED_REPOSITORIES: Set[str] = {
    "aion/synthetic-bench",
    "aion/clean-controls",
    "urllib3/urllib3",
    "prettier/prettier",
    "trpc/trpc",
    "boto/botocore",
    "pytest-dev/pytest",
    "reduxjs/redux-toolkit",
    "pyca/cryptography",
    "expressjs/express",
    "pallets/flask",
    "tiangolo/fastapi",
    "cypress-io/cypress",
    "lodash/lodash",
    "django/django",
    "pmndrs/zustand",
    "docker/docker-py",
    "nestjs/nest",
    "webpack/webpack",
    "matplotlib/matplotlib",
    "facebook/react",
    "encode/httpx",
    "vuejs/core",
    "axios/axios",
    "textualize/rich",
    "chalk/chalk",
    "numpy/numpy",
    "sveltejs/svelte",
    "colinhacks/zod",
    "python-attrs/attrs",
    "pallets/jinja",
    "psf/requests",
    "pallets/click",
    "celery/celery",
    "prisma/prisma",
    "TanStack/query",
    "fastify/fastify",
    "graphql/graphql-js",
    "marshmallow-code/marshmallow",
    "gitpython-developers/GitPython",
    "ansible/ansible",
    "pydantic/pydantic",
    "vercel/next.js",
    "sqlalchemy/sqlalchemy",
    "vitejs/vite",
    "tiangolo/typer",
    "typescript-eslint/typescript-eslint",
    "tj/commander.js",
    "pandas-dev/pandas",
    "sindresorhus/got",
    "microsoft/playwright",
    "scipy/scipy",
}


class BaseCollector:
    """
    Abstract base class for sourcing real pull request candidates.
    Enforces repository isolation, license adherence, and respectful rate limits.
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        timeout_seconds: float = 10.0,
        offline_mode: bool = False,
    ) -> None:
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.timeout_seconds = min(timeout_seconds, 10.0)  # Hard cap <= 10s per HARD-06
        self.offline_mode = offline_mode or (not self.github_token)
        self.client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self.client is None or self.client.is_closed:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Aion-Bench-Collector/1.1",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            self.client = httpx.Client(headers=headers, timeout=self.timeout_seconds)
        return self.client

    def validate_repository(self, owner: str, repo: str, license_key: str = "mit") -> bool:
        """
        Asserts repository is eligible for bench_real:
        1. Repo is not in training episodes or benchmark test splits.
        2. License is an OSI-approved permissive license.
        """
        slug = f"{owner}/{repo}".lower().strip()
        if slug in BLACKLISTED_REPOSITORIES:
            logger.warning("Repository %s is blacklisted from bench_real (isolation guard).", slug)
            return False

        norm_license = license_key.lower().strip()
        if norm_license not in PERMISSIBLE_OSI_LICENSES:
            logger.warning("Repository %s license %s is not an approved permissive license.", slug, norm_license)
            return False

        return True

    def safe_github_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Executes GitHub REST request with exponential backoff on 429/403 rate limits.
        Returns None if offline or rate limit exhausted.
        """
        if self.offline_mode:
            return None

        client = self._get_client()
        url = endpoint if endpoint.startswith("http") else f"https://api.github.com/{endpoint.lstrip('/')}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (403, 429):
                    reset_time = int(response.headers.get("x-ratelimit-reset", time.time() + 5))
                    sleep_duration = max(1.0, min(reset_time - time.time(), 5.0))
                    logger.warning("GitHub rate limit hit; backing off for %.1fs", sleep_duration)
                    time.sleep(sleep_duration)
                elif response.status_code == 404:
                    return None
                else:
                    logger.error("GitHub request failed: %s %s", response.status_code, response.text)
                    return None
            except Exception as e:
                logger.error("HTTP error during GitHub request to %s: %s", url, e)
                if attempt == max_retries - 1:
                    return None
                time.sleep(1.0)
        return None

    def close(self) -> None:
        if self.client and not self.client.is_closed:
            self.client.close()
