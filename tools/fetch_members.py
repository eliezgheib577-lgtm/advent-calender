#!/usr/bin/env python3
"""Read the LeMSIC member list from its shared link and update the website's ID list.

    python3 tools/fetch_members.py "https://1drv.ms/x/s!..."
    MEMBERS_SHEET_URL="https://..." python3 tools/fetch_members.py

Works with a shared link to an Excel file on OneDrive or SharePoint, or to a Google
Sheet. The link must allow anyone with it to view the file without signing in.
Optional: --column "LeMSIC ID" (or MEMBERS_ID_COLUMN) if the ID column's header
doesn't contain "ID", and --name-column "Full Name" (or MEMBERS_NAME_COLUMN) if the
names aren't in a "Full Name" / "Name" column (or "First Name" + "Last Name"), and
--tab "ID" (or MEMBERS_SHEET_TAB) to read a tab other than the first.

The scheduled GitHub workflow (.github/workflows/publish-site.yml) runs this every
30 minutes, so members added to the sheet can log in shortly after.
"""
import argparse
import base64
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_members import pick_members, rows_from_bytes, write_members  # noqa: E402

UA = "Mozilla/5.0 (compatible; LeMSIC-advent-calendar member sync)"


def with_param(url, key, value):
    parts = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    q = [(k, v) for k, v in q if k != key] + [(key, value)]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


def download_candidates(link):
    """Direct-download URLs to try for a shared link, best first."""
    host = urllib.parse.urlsplit(link).netloc.lower()
    out = []
    m = re.search(r"docs\.google\.com/spreadsheets/d/([\w-]+)", link)
    if m:
        gid = re.search(r"[#&?]gid=(\d+)", link)
        out.append(f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx"
                   + (f"&gid={gid.group(1)}" if gid else ""))
    elif "sharepoint.com" in host:
        out.append(with_param(link, "download", "1"))
    elif host in ("1drv.ms", "onedrive.live.com") or host.endswith(".onedrive.live.com"):
        token = base64.urlsafe_b64encode(link.encode()).decode().rstrip("=")
        out.append(f"https://api.onedrive.com/v1.0/shares/u!{token}/root/content")
        out.append(with_param(link, "download", "1"))
    out.append(link)
    return out


def fetch(link):
    errors = []
    for url in download_candidates(link):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            final = r.geturl()
            # a sharing page rather than the file: try its download form too
            if data[:2] != b"PK" and b"<html" in data[:2000].lower() and "download=1" not in final:
                with urllib.request.urlopen(urllib.request.Request(with_param(final, "download", "1"),
                                                                   headers={"User-Agent": UA}), timeout=60) as r2:
                    data2 = r2.read()
                if data2[:2] == b"PK":
                    return data2
            rows_from_bytes(data)                # raises if it's a web page, not a sheet
            return data
        except Exception as e:                   # try the next form of the link
            errors.append(f"{url[:80]}…: {e}")
    raise RuntimeError("Couldn't download the member list. Tried:\n  " + "\n  ".join(errors))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("link", nargs="?", default=os.environ.get("MEMBERS_SHEET_URL"))
    ap.add_argument("--column", default=os.environ.get("MEMBERS_ID_COLUMN") or None)
    ap.add_argument("--name-column", default=os.environ.get("MEMBERS_NAME_COLUMN") or None)
    ap.add_argument("--tab", default=os.environ.get("MEMBERS_SHEET_TAB") or None)
    args = ap.parse_args()
    if not args.link:
        sys.exit("Give the shared link to the member list (or set MEMBERS_SHEET_URL).")
    try:
        if os.path.exists(args.link):            # a local file works too, for testing
            with open(args.link, "rb") as f:
                data = f.read()
        else:
            data = fetch(args.link)
        members, used, name_used = pick_members(rows_from_bytes(data, sheet=args.tab), args.column, args.name_column)
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))
    changed = write_members(members)
    named = sum(1 for _, n in members if n)
    print(f'{len(members)} member IDs from "{used}", {named} with names'
          f'{f" from {name_used!r}" if name_used else " (no name column found)"}{" (updated)" if changed else " (no change)"}')


if __name__ == "__main__":
    main()
