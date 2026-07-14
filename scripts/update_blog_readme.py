#!/usr/bin/env python3
"""
update_blog_readme.py
---------------------
Fetches the latest posts from Shubham Bhati's RSS feed and updates
the GitHub profile README.md with a clean 2-column card grid layout.

Runs daily via GitHub Actions on Shubh2-0/Shubh2-0 profile repo.
"""

import re
import sys
import requests
from datetime import datetime
from xml.etree import ElementTree as ET

RSS_URL   = "https://shubhambhati.is-a.dev/backend-utility-tools/rss.xml"
README    = "README.md"
MAX_POSTS = 6   # must be even for clean 2-column grid

# Keyword → shield badge color map (topic auto-detection)
TAG_MAP = {
    "hikaricp":    ("HikariCP",          "0078D4"),
    "postgres":    ("PostgreSQL",        "316192"),
    "redis":       ("Redis",             "DD0031"),
    "kafka":       ("Apache_Kafka",      "231F20"),
    "jvm":         ("JVM_Optimization",  "1F6FEB"),
    "validation":  ("Validation",        "238636"),
    "security":    ("Spring_Security",   "6DB33F"),
    "jwt":         ("JWT",               "000000"),
    "jackson":     ("Jackson",           "DA3633"),
    "json":        ("JSON",              "6E40C9"),
    "transaction": ("Transactions",      "E16C34"),
    "docker":      ("Docker",            "2496ED"),
    "microservice":("Microservices",     "8957E5"),
    "hibernate":   ("Hibernate",         "59666C"),
    "spring":      ("Spring_Boot",       "6DB33F"),
    "profile":     ("Spring_Profiles",   "6DB33F"),
    "api":         ("REST_API",          "0078D4"),
    "config":      ("Configuration",     "8957E5"),
}

START = "<!-- BLOG-POST-LIST:START -->"
END   = "<!-- BLOG-POST-LIST:END -->"


def detect_tags(title: str, description: str) -> list[tuple[str, str]]:
    """Return up to 2 (label, color) badge tuples based on post keywords."""
    text = (title + " " + description).lower()
    found = []
    for keyword, (label, color) in TAG_MAP.items():
        if keyword in text:
            found.append((label, color))
        if len(found) == 2:
            break
    if not found:
        found.append(("Spring_Boot", "6DB33F"))
    return found


def badge_img(label: str, color: str) -> str:
    return f'<img src="https://img.shields.io/badge/{label}-{color}?style=flat-square" />'


def parse_date(pub_date: str) -> str:
    """Convert RSS pubDate string to 'Mon DD, YYYY' format."""
    try:
        dt = datetime.strptime(pub_date.strip(), "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return pub_date[:16]


def fetch_posts() -> list[dict]:
    print(f"[INFO] Fetching RSS from {RSS_URL}")
    resp = requests.get(RSS_URL, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    posts = []

    for item in channel.findall("item"):
        title       = (item.findtext("title") or "").strip()
        link        = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date    = (item.findtext("pubDate") or "").strip()

        if not title or not link:
            continue

        posts.append({
            "title":       title,
            "url":         link,
            "date":        parse_date(pub_date),
            "description": description,
            "tags":        detect_tags(title, description),
        })

        if len(posts) >= MAX_POSTS:
            break

    print(f"[INFO] Fetched {len(posts)} posts.")
    return posts


def build_card(post: dict) -> str:
    """Build one <td> card for a blog post."""
    badges = "\n      ".join(badge_img(lbl, col) for lbl, col in post["tags"])
    return (
        f'    <td width="50%" valign="top">\n'
        f'      <h4>🔷 &nbsp;<a href="{post["url"]}">{post["title"]}</a></h4>\n'
        f'      {badges}<br/>\n'
        f'      <sub>📅 {post["date"]}</sub>\n'
        f'    </td>'
    )


def build_cta_cell() -> str:
    return (
        '    <td width="50%" valign="top" align="center">\n'
        '      <br/><br/>\n'
        '      <a href="https://shubhambhati.is-a.dev/">\n'
        '        <img src="https://img.shields.io/badge/%E2%86%92%20Read%20All%20Posts-4FC3F7'
        '?style=for-the-badge&logo=readthedocs&logoColor=white" />\n'
        '      </a>\n'
        '    </td>'
    )


def build_grid(posts: list[dict]) -> str:
    """Pair posts into rows of 2 for the grid. Last cell = CTA if odd count."""
    rows_html = []

    for i in range(0, len(posts), 2):
        left  = build_card(posts[i])
        if i + 1 < len(posts):
            right = build_card(posts[i + 1])
        else:
            right = build_cta_cell()

        rows_html.append(f"  <tr>\n{left}\n{right}\n  </tr>")

    # If all posts filled neatly, add CTA as extra final row
    if len(posts) % 2 == 0:
        cta = build_cta_cell()
        filler = '    <td width="50%"></td>'
        rows_html.append(f"  <tr>\n{cta}\n{filler}\n  </tr>")

    table = '<table width="100%">\n' + "\n".join(rows_html) + "\n</table>"
    return table


def update_readme(grid_html: str):
    with open(README, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.DOTALL
    )

    new_block = f"{START}\n{grid_html}\n{END}"

    if not pattern.search(content):
        print("[ERROR] Could not find BLOG-POST-LIST markers in README.md")
        sys.exit(1)

    updated = pattern.sub(new_block, content)

    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)

    print("[SUCCESS] README.md updated with latest blog card grid.")


if __name__ == "__main__":
    posts = fetch_posts()
    if not posts:
        print("[WARN] No posts fetched. README unchanged.")
        sys.exit(0)

    grid = build_grid(posts)
    update_readme(grid)
