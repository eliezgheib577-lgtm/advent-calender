#!/usr/bin/env python3
"""Turn the LeMSIC member list into the list the website checks IDs against.

    python3 tools/import_members.py members.xlsx
    python3 tools/import_members.py members.xlsx --column "LeMSIC ID"
    python3 tools/import_members.py members.csv

Reads the first sheet (or a CSV), takes the ID column (the one whose header mentions
"ID", or the column you name), and writes site/assets/members.js.

The website never receives the IDs themselves: each ID is normalised (upper case,
letters and digits only) and stored as a salted SHA-256 fingerprint. The browser
fingerprints what a student types the same way and looks for a match. The salt is
kept from one run to the next, so the file only changes when the list changes.

To read the list straight from a shared Excel / Google Sheets link, see fetch_members.py.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "assets", "members.js")


def normalise(value):
    return re.sub(r"[^A-Z0-9]", "", str(value if value is not None else "").strip().upper())


def rows_from_bytes(data, name_hint=""):
    """Rows of the first sheet of an .xlsx, or of a CSV."""
    if data[:2] == b"PK":                               # .xlsx is a zip file
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    head = data[:512].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        raise ValueError("Got a web page instead of a spreadsheet. Make sure the link lets "
                         "anyone with the link view the file (no sign-in).")
    text = data.decode("utf-8-sig", errors="replace")
    return [row for row in csv.reader(io.StringIO(text))]


def pick_ids(rows, column=None):
    rows = [r for r in rows if any(c not in (None, "") for c in r)]
    if not rows:
        raise ValueError("The sheet is empty.")
    header = [str(c or "").strip() for c in rows[0]]
    if column:
        matches = [i for i, h in enumerate(header) if h.lower() == column.lower()]
        if not matches:
            raise ValueError(f'No column called "{column}". Columns: {", ".join(header)}')
        col = matches[0]
    else:
        candidates = [i for i, h in enumerate(header) if re.search(r"\bid\b", h, re.I)]
        col = candidates[0] if candidates else 0
    has_header = not normalise(rows[0][col]) or bool(re.search(r"id|member|name", header[col], re.I))
    values = [r[col] for r in (rows[1:] if has_header else rows) if col < len(r)]
    ids = sorted({normalise(v) for v in values if normalise(v)})
    if not ids:
        raise ValueError("No IDs found in that column.")
    return ids, (header[col] if has_header else f"column {col + 1}")


def existing_salt():
    try:
        with open(OUT) as f:
            m = re.search(r'"salt":\s*"([0-9a-f]+)"', f.read())
            return m.group(1) if m else None
    except OSError:
        return None


def write_members(ids, salt=None):
    """Write members.js; returns True if its contents changed."""
    salt = salt or os.environ.get("MEMBERS_SALT") or existing_salt() or secrets.token_hex(16)
    hashes = sorted(hashlib.sha256((salt + i).encode()).hexdigest() for i in ids)
    content = ("// Generated from the LeMSIC member list by tools/import_members.py.\n"
               "// Fingerprints only: the IDs themselves are not in this file.\n"
               "window.LEMSIC_MEMBERS = " + json.dumps({"salt": salt, "count": len(hashes), "hashes": hashes}) + ";\n")
    try:
        with open(OUT) as f:
            if f.read() == content:
                return False
    except OSError:
        pass
    with open(OUT, "w") as f:
        f.write(content)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", help="the member list (.xlsx or .csv)")
    ap.add_argument("--column", help="header of the column holding the LeMSIC IDs")
    args = ap.parse_args()
    try:
        with open(args.sheet, "rb") as f:
            ids, used = pick_ids(rows_from_bytes(f.read(), args.sheet), args.column)
    except ValueError as e:
        sys.exit(str(e))
    changed = write_members(ids)
    print(f'{len(ids)} member IDs from "{used}" -> {os.path.relpath(OUT, ROOT)}'
          f'{"" if changed else " (no change)"}')


if __name__ == "__main__":
    main()
