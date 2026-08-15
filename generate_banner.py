"""
Regenerates assets/neofetch_banner.png using LIVE data pulled from the
GitHub API for GITHUB_USERNAME below. No hardcoded/assumed profile fields —
everything on the right side comes directly from the API response.

Run manually:  python3 scripts/generate_banner.py
Run in CI:      triggered by .github/workflows/update-banner.yml
"""

import json
import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont

GITHUB_USERNAME = "codewithzubair07"
HEADERS = {"User-Agent": "banner-generator"}

# Use GITHUB_TOKEN if running inside Actions, to avoid API rate limits
# and to unlock GraphQL-only stats (commits, contributed-to repos).
TOKEN = os.environ.get("GITHUB_TOKEN")
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

CONTACT = {
    "GitHub": f"github.com/{GITHUB_USERNAME}",
    "LinkedIn": "linkedin.com/in/juber-quraishi-362215319",
    "Twitter": "@zubair_57",
}


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return json.loads(urllib.request.urlopen(req).read())


def fetch_graphql_stats():
    """Requires an authenticated token (available automatically in Actions).
    Returns (commits_past_year, contributed_repo_count) or (None, None)
    if no token is available (e.g. running locally without one)."""
    if not TOKEN:
        return None, None
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalRepositoriesWithContributedCommits
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"login": GITHUB_USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    try:
        result = json.loads(urllib.request.urlopen(req).read())
        cc = result["data"]["user"]["contributionsCollection"]
        return cc["totalCommitContributions"], cc["totalRepositoriesWithContributedCommits"]
    except Exception as e:
        print(f"GraphQL stats unavailable: {e}")
        return None, None


def get_profile():
    return fetch_json(f"https://api.github.com/users/{GITHUB_USERNAME}")


def get_all_repos():
    repos = []
    page = 1
    while True:
        batch = fetch_json(
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&page={page}"
        )
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if page > 10:  # safety cap
            break
    return repos


def compute_stats(repos):
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    langs = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    top_langs = sorted(langs.items(), key=lambda x: -x[1])[:5]
    return stars, top_langs


def build_banner(profile, stars, top_langs, repo_count, commits_past_year, contributed_repos):
    with open("robot_ascii.txt") as f:
        ascii_lines = f.read().split("\n")

    mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    mono_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
    ascii_font = ImageFont.truetype(mono, 8)
    info_font = ImageFont.truetype(mono, 15)
    header_font = ImageFont.truetype(mono_bold, 17)

    ascii_char_w = 8 * 0.6
    ascii_char_h = 8 * 1.05
    left_content_w = int(max(len(l) for l in ascii_lines) * ascii_char_w)
    left_content_h = int(len(ascii_lines) * ascii_char_h)
    left_pad = 40
    left_w = left_content_w + left_pad * 2

    line_h = 25
    right_w = 800
    top_pad = 45

    W = left_w + right_w
    H = 900
    bg = (5, 5, 6)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    orange = (255, 140, 0)
    orange_dim = (200, 110, 20)
    white = (230, 230, 230)
    green = (110, 220, 110)
    gray = (110, 110, 110)

    rx = left_w + 40
    ry = top_pad
    VAL_X = rx + 260

    def kv(y, label, value, value_color=white):
        draw.text((rx, y), label, font=info_font, fill=orange)
        label_w = draw.textlength(label, font=info_font)
        dots_start = rx + label_w + 6
        dots_w = draw.textlength(".", font=info_font)
        n_dots = max(0, int((VAL_X - dots_start) / dots_w))
        draw.text((dots_start, y), "." * n_dots, font=info_font, fill=gray)
        draw.text((VAL_X + 6, y), value, font=info_font, fill=value_color)
        return y + line_h

    name = profile.get("name") or GITHUB_USERNAME
    draw.text((rx, ry), f"{GITHUB_USERNAME}@github", font=header_font, fill=orange)
    hdr_w = draw.textlength(f"{GITHUB_USERNAME}@github", font=header_font)
    draw.line([(rx + hdr_w + 14, ry + 9), (rx + right_w - 40, ry + 9)], fill=gray, width=1)
    ry += line_h + 10

    ry = kv(ry, "Name", name)
    bio = profile.get("bio") or "—"
    ry = kv(ry, "Bio", bio if len(bio) < 45 else bio[:42] + "...")
    created = profile.get("created_at", "")[:7]  # YYYY-MM
    ry = kv(ry, "Member Since", created)
    ry += 14

    if top_langs:
        draw.text((rx, ry), "Top Languages", font=header_font, fill=orange)
        hdr_w = draw.textlength("Top Languages", font=header_font)
        draw.line([(rx + hdr_w + 14, ry + 9), (rx + right_w - 40, ry + 9)], fill=gray, width=1)
        ry += line_h + 10
        for lang, count in top_langs:
            ry = kv(ry, lang, f"{count} repos")
        ry += 14

    draw.text((rx, ry), "Contact", font=header_font, fill=orange)
    hdr_w = draw.textlength("Contact", font=header_font)
    draw.line([(rx + hdr_w + 14, ry + 9), (rx + right_w - 40, ry + 9)], fill=gray, width=1)
    ry += line_h + 10

    for label, value in CONTACT.items():
        ry = kv(ry, label, value)
    ry += 14

    draw.text((rx, ry), "GitHub Stats (live)", font=header_font, fill=orange)
    hdr_w = draw.textlength("GitHub Stats (live)", font=header_font)
    draw.line([(rx + hdr_w + 14, ry + 9), (rx + right_w - 40, ry + 9)], fill=gray, width=1)
    ry += line_h + 10

    ry = kv(ry, "Public Repos", str(repo_count), value_color=green)
    ry = kv(ry, "Total Stars", str(stars), value_color=green)
    ry = kv(ry, "Followers", str(profile.get("followers", 0)), value_color=green)
    ry = kv(ry, "Following", str(profile.get("following", 0)))
    if commits_past_year is not None:
        ry = kv(ry, "Commits (past yr)", str(commits_past_year), value_color=green)
    if contributed_repos is not None:
        ry = kv(ry, "Repos Contributed To", str(contributed_repos), value_color=green)

    right_bottom = ry

    total_right_h = right_bottom - top_pad
    art_y_start = top_pad + max(0, (total_right_h - left_content_h) // 2)

    y = art_y_start
    for line in ascii_lines:
        x = left_pad
        for ch in line:
            if ch != " ":
                if ch in "@%#":
                    c = (255, 190, 110)
                elif ch in "*+=":
                    c = orange
                else:
                    c = orange_dim
                draw.text((x, y), ch, font=ascii_font, fill=c)
            x += ascii_char_w
        y += ascii_char_h

    draw.line([(left_w, top_pad - 5), (left_w, right_bottom + 5)], fill=(55, 55, 55), width=1)

    final_h = right_bottom + 40
    img = img.crop((0, 0, W, final_h))
    d2 = ImageDraw.Draw(img)
    d2.rectangle([2, 2, W - 3, final_h - 3], outline=(70, 40, 0), width=1)

    img.save("neofetch_banner.png")
    print(f"Saved neofetch_banner.png ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    profile = get_profile()
    repos = get_all_repos()
    stars, top_langs = compute_stats(repos)
    commits_past_year, contributed_repos = fetch_graphql_stats()
    build_banner(
        profile,
        stars,
        top_langs,
        profile.get("public_repos", len(repos)),
        commits_past_year,
        contributed_repos,
    )
