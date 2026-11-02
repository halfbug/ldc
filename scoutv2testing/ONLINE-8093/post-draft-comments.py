#!/usr/bin/env python3
"""Add the ONLINE-8093 review comments to GitLab as DRAFT notes (a pending review). Nothing is submitted:
drafts are visible only to you until you press "Submit review" on the MR page.

Reads mr-review-comments.md next to this file. A comment whose file:line is on a line the MR's diff shows becomes
an inline draft on that line; any other comment (rows marked (general), lines outside the diff, files not in the MR)
becomes a general draft that starts with its file:line.

Usage (in your own terminal; the token needs the `api` scope):
    export GITLAB_TOKEN=glpat-...
    python3 post-draft-comments.py            # dry run: prints what it would add, sends nothing
    python3 post-draft-comments.py --apply    # adds the drafts
    python3 post-draft-comments.py --apply --only swo   # or --only rag

Re-running is safe: a draft whose text is already among your drafts on that MR is skipped.
Only the standard library is used.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GITLAB = os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/")
MRS = {
    # key: (project path, MR iid, heading in mr-review-comments.md, head commit the comments were written against)
    "swo": ("sw6/studiesw/swo-3.0", 6354, "## swo !6354", "41ace7e971"),
    "rag": ("sw6/ops/rag", 101, "## rag !101", "de38e41b"),
}
SOURCE = Path(__file__).with_name("mr-review-comments.md")


def api(method, path, token, data=None, params=None):
    url = f"{GITLAB}/api/v4{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, method=method, headers={
        "PRIVATE-TOKEN": token, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read() or b"null"), response.headers
    except urllib.error.HTTPError as error:
        sys.exit(f"{method} {path} -> {error.code}: {error.read().decode()[:400]}")


def paged(path, token):
    page = 1
    while True:
        items, headers = api("GET", path, token, params={"per_page": 100, "page": page})
        yield from items
        if not headers.get("X-Next-Page"):
            return
        page = int(headers["X-Next-Page"])


def parse_comments(text, heading):
    """Rows of the tables under `heading`, skipping the 'Fixed since' table. Returns dicts of target/body/level."""
    section = text.split(heading, 1)[1]
    section = re.split(r"\n## (?!#)", section, maxsplit=1)[0]
    level, comments = "", []
    for line in section.splitlines():
        if line.startswith("### "):
            level = line[4:].strip()
            continue
        if not line.startswith("| ") or line.startswith("| File:line") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) < 2:
            continue
        target, body = cells[0], " | ".join(cells[1:])
        general = "(general)" in target
        spec = re.search(r"`([^`]+)`", target)
        path, lines = None, []
        if spec:
            path, _, rest = spec.group(1).partition(":")
            lines = [int(n) for n in re.findall(r"\d+", rest)[:1]]
        comments.append({"path": path, "line": lines[0] if lines else None, "general": general or not lines,
                         "level": level, "target": target.replace("**", ""), "body": body})
    return comments


def added_and_context_lines(diffs):
    """new_path -> {new_line: old_line or None} for every line the MR diff shows."""
    shown = {}
    for diff in diffs:
        if diff.get("deleted_file"):
            continue
        lines, old, new = {}, 0, 0
        for row in (diff.get("diff") or "").splitlines():
            hunk = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
            if hunk:
                old, new = int(hunk.group(1)), int(hunk.group(2))
                continue
            if row.startswith("+"):
                lines[new] = None
                new += 1
            elif row.startswith("-"):
                old += 1
            elif row.startswith(" ") or row == "":
                lines[new] = old
                old += 1
                new += 1
        shown[diff["new_path"]] = lines
    return shown


def body_for(comment, inline):
    prefix = "Nit: " if comment["level"].lower().startswith("nit") else ""
    text = re.sub(r"`([^`]*)`", r"`\1`", comment["body"])
    if inline:
        return prefix + text
    where = comment["target"] if comment["path"] is None else f"`{comment['path']}" + (
        f":{comment['line']}`" if comment["line"] else "`")
    return f"{prefix}**{where}**: {text}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="add the drafts (default: dry run)")
    parser.add_argument("--only", choices=sorted(MRS), help="one MR only")
    args = parser.parse_args()
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        sys.exit("Set GITLAB_TOKEN (a personal access token with the api scope) first.")
    text = SOURCE.read_text()

    for key, (project, iid, heading, reviewed_head) in MRS.items():
        if args.only and key != args.only:
            continue
        pid = urllib.parse.quote(project, safe="")
        base = f"/projects/{pid}/merge_requests/{iid}"
        mr, _ = api("GET", base, token)
        refs = mr["diff_refs"]
        print(f"\n== {project} !{iid}: {mr['title']}\n   head {refs['head_sha'][:10]} (comments written against {reviewed_head})")
        if not refs["head_sha"].startswith(reviewed_head):
            print("   ⚠️  The MR has new commits since the review: line numbers may have moved. Check before --apply.")
        shown = added_and_context_lines(paged(f"{base}/diffs", token))
        existing = {d.get("note") for d in paged(f"{base}/draft_notes", token)}

        made = skipped = 0
        for comment in parse_comments(text, heading):
            on_diff = (not comment["general"] and comment["path"] in shown
                       and comment["line"] in shown[comment["path"]])
            note = body_for(comment, on_diff)
            if note in existing:
                skipped += 1
                continue
            data = {"note": note}
            if on_diff:
                old_line = shown[comment["path"]][comment["line"]]
                data["position"] = {
                    "position_type": "text", "base_sha": refs["base_sha"], "start_sha": refs["start_sha"],
                    "head_sha": refs["head_sha"], "new_path": comment["path"], "old_path": comment["path"],
                    "new_line": comment["line"], **({"old_line": old_line} if old_line else {}),
                }
            where = f"{comment['path']}:{comment['line']}" if on_diff else "general"
            print(f"   {'add ' if args.apply else 'would add'} [{where}] {note[:90]}")
            if args.apply:
                api("POST", f"{base}/draft_notes", token, data=data)
            made += 1
        print(f"   {made} {'added' if args.apply else 'to add'}, {skipped} already drafted")
    if not args.apply:
        print("\nDry run: nothing was sent. Re-run with --apply to add the drafts.")
    else:
        print("\nDrafts added. Review them on each MR page, then press 'Submit review' yourself when ready.")


if __name__ == "__main__":
    main()
