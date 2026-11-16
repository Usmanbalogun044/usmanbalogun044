#!/usr/bin/env python3
"""Generate an account-wide public GitHub profile stats SVG."""

from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

USERNAME = "Usmanbalogun044"
API_ROOT = "https://api.github.com"
OUTPUT = Path("profile/metrics.svg")
PALETTE = [
    "#58a6ff", "#a371f7", "#3fb950", "#f0883e",
    "#db61a2", "#79c0ff", "#d29922", "#8b949e",
]
LANGUAGE_COLORS = {
    "PHP": "#777bb4", "Go": "#00add8", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Python": "#3572a5", "HTML": "#e34c26",
    "CSS": "#563d7c", "Shell": "#89e051", "Blade": "#f7523f",
    "Vue": "#41b883", "Dockerfile": "#384d54", "Java": "#b07219",
    "C": "#555555", "C++": "#f34b7d", "Ruby": "#701516",
}


def api_get(path: str):
    token = os.environ.get("GH_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "usmanbalogun044-profile-stats",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_ROOT}/{path.lstrip('/')}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach GitHub API: {exc.reason}") from exc


def fetch_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        batch = api_get(
            f"users/{USERNAME}/repos?type=owner&sort=updated&per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected response while fetching public repositories.")
        repositories.extend(repo for repo in batch if not repo.get("private", False))
        if len(batch) < 100:
            break
        page += 1
        if page > 20:
            break
    return repositories


def collect_language_bytes(repositories: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repositories:
        if repo.get("fork"):
            continue
        language_url = repo.get("languages_url")
        if not language_url:
            continue
        path = language_url.removeprefix(f"{API_ROOT}/")
        try:
            languages = api_get(path)
            for language, byte_count in languages.items():
                totals[language] = totals.get(language, 0) + int(byte_count)
        except Exception as exc:  # one inaccessible repository should not break the profile
            print(f"Skipping language data for {repo.get('full_name', 'unknown')}: {exc}", file=sys.stderr)
    return totals


def fmt(value: int) -> str:
    return f"{value:,}"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def build_svg(profile: dict, repositories: list[dict], languages: dict[str, int]) -> str:
    originals = [repo for repo in repositories if not repo.get("fork")]
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in originals)
    forks = sum(int(repo.get("forks_count", 0)) for repo in originals)
    followers = int(profile.get("followers", 0))
    public_repos = int(profile.get("public_repos", len(repositories)))
    public_gists = int(profile.get("public_gists", 0))

    ranked_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:8]
    total_bytes = sum(languages.values())
    following = int(profile.get("following", 0))
    now = datetime.now(timezone.utc).astimezone(ZoneInfo("Africa/Lagos"))
    updated = now.strftime("%d %b %Y · %H:%M WAT")

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="610" viewBox="0 0 1000 610" role="img" aria-labelledby="title desc">',
        '<title id="title">GitHub profile overview for Usman Balogun</title>',
        '<desc id="desc">Public repository, follower, star, fork and programming language statistics.</desc>',
        '<defs><linearGradient id="accent" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#58a6ff"/><stop offset="100%" stop-color="#a371f7"/></linearGradient></defs>',
        '<rect width="1000" height="610" rx="18" fill="#0d1117"/>',
        '<rect x="1" y="1" width="998" height="608" rx="17" fill="none" stroke="#30363d"/>',
        '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        '<text x="38" y="48" fill="#f0f6fc" font-size="23" font-weight="700">GitHub Profile Overview</text>',
        '<text x="38" y="73" fill="#8b949e" font-size="12">Public account statistics · @Usmanbalogun044</text>',
        f'<text x="962" y="48" fill="#8b949e" font-size="11" text-anchor="end">Updated {esc(updated)}</text>',
    ]

    cards = [
        ("PUBLIC REPOSITORIES", fmt(public_repos), "Owned public repositories"),
        ("FOLLOWERS", fmt(followers), "People following this profile"),
        ("STARS EARNED", fmt(stars), "Stars across original public repos"),
        ("FORKS", fmt(forks), "Forks across original public repos"),
    ]
    x_positions = [38, 275, 512, 749]
    for index, (label, value, note) in enumerate(cards):
        x = x_positions[index]
        parts.extend([
            f'<rect x="{x}" y="103" width="213" height="112" rx="12" fill="#161b22" stroke="#30363d"/>',
            f'<rect x="{x}" y="103" width="213" height="3" rx="2" fill="{PALETTE[index]}"/>',
            f'<text x="{x + 17}" y="133" fill="#8b949e" font-size="10" font-weight="700" letter-spacing=".8">{esc(label)}</text>',
            f'<text x="{x + 17}" y="174" fill="#f0f6fc" font-size="31" font-weight="700">{esc(value)}</text>',
            f'<text x="{x + 17}" y="197" fill="#8b949e" font-size="10">{esc(note)}</text>',
        ])

    parts.extend([
        '<text x="38" y="260" fill="#f0f6fc" font-size="17" font-weight="700">Most-used languages</text>',
        f'<text x="962" y="260" fill="#8b949e" font-size="11" text-anchor="end">{len(languages)} languages detected · {fmt(total_bytes)} bytes</text>',
    ])

    bar_x, bar_y, bar_w, bar_h = 38, 279, 924, 16
    if total_bytes > 0:
        offset = 0.0
        for index, (language, byte_count) in enumerate(ranked_languages):
            width = bar_w * byte_count / total_bytes
            if width < 1:
                continue
            color = LANGUAGE_COLORS.get(language, PALETTE[index % len(PALETTE)])
            parts.append(
                f'<rect x="{bar_x + offset:.2f}" y="{bar_y}" width="{max(width, 1):.2f}" height="{bar_h}" fill="{color}"/>'
            )
            offset += width
    else:
        parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="8" fill="#30363d"/>')

    legend_y = 324
    if ranked_languages:
        for index, (language, byte_count) in enumerate(ranked_languages):
            col = index % 4
            row = index // 4
            x = 40 + col * 232
            y = legend_y + row * 34
            color = LANGUAGE_COLORS.get(language, PALETTE[index % len(PALETTE)])
            pct = (byte_count / total_bytes * 100) if total_bytes else 0
            parts.extend([
                f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{color}"/>',
                f'<text x="{x + 19}" y="{y}" fill="#c9d1d9" font-size="12" font-weight="600">{esc(language)}</text>',
                f'<text x="{x + 208}" y="{y}" fill="#8b949e" font-size="11" text-anchor="end">{pct:.1f}%</text>',
            ])
    else:
        parts.append('<text x="40" y="324" fill="#8b949e" font-size="12">No language data was returned for public repositories.</text>')

    parts.extend([
        '<text x="38" y="408" fill="#f0f6fc" font-size="17" font-weight="700">Account footprint</text>',
        '<text x="962" y="408" fill="#8b949e" font-size="11" text-anchor="end">Public GitHub profile data</text>',
    ])

    footprint = [
        ("ORIGINAL PUBLIC REPOSITORIES", fmt(len(originals)), "Excludes forked repositories"),
        ("FOLLOWING", fmt(following), "GitHub accounts followed"),
        ("PUBLIC GISTS", fmt(public_gists), "Public code snippets"),
    ]
    for index, (label, value, note) in enumerate(footprint):
        x = 38 + index * 312
        parts.extend([
            f'<rect x="{x}" y="430" width="288" height="105" rx="12" fill="#161b22" stroke="#30363d"/>',
            f'<text x="{x + 16}" y="458" fill="#8b949e" font-size="10" font-weight="700" letter-spacing=".5">{esc(label)}</text>',
            f'<text x="{x + 16}" y="500" fill="#f0f6fc" font-size="28" font-weight="700">{esc(value)}</text>',
            f'<text x="{x + 16}" y="519" fill="#8b949e" font-size="10">{esc(note)}</text>',
        ])

    parts.extend([
        '<line x1="38" y1="574" x2="962" y2="574" stroke="#30363d"/>',
        '<text x="38" y="593" fill="#8b949e" font-size="10">Public GitHub data only · Private repository activity is not included</text>',
        '<text x="962" y="593" fill="#8b949e" font-size="10" text-anchor="end">Generated automatically with GitHub Actions</text>',
        '</g></svg>',
    ])
    return "\n".join(parts)


def main() -> None:
    profile = api_get(f"users/{USERNAME}")
    repositories = fetch_repositories()
    languages = collect_language_bytes(repositories)
    svg = build_svg(profile, repositories, languages)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(
        f"Generated {OUTPUT}: {profile.get('public_repos', 0)} public repos, "
        f"{profile.get('followers', 0)} followers, "
        f"{len(languages)} languages."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Profile stats generation failed: {exc}", file=sys.stderr)
        sys.exit(1)
