#!/usr/bin/env python3
"""Turn the LeMSIC member list into the list the website checks IDs against.

    python3 tools/import_members.py members.xlsx
    python3 tools/import_members.py members.xlsx --column "LeMSIC ID" --name-column "Full Name"
    python3 tools/import_members.py members.csv

Reads the first sheet (or a CSV). The ID column is the one whose header mentions "ID"
(or the column you name); the name column is "Full Name", "Name", or "First Name" +
"Last Name" together (or the column you name). Writes site/assets/members.js.

The website never receives the IDs, and it never receives the names in a readable form:
  * each ID is normalised (upper case, letters and digits only) and stored as a salted
    SHA-256 fingerprint; the browser fingerprints what a student types the same way;
  * each full name is encrypted with a key made from that member's own ID (PBKDF2), so
    the page can show "Welcome, <name>" only to someone who types that exact ID.
The salt is kept from one run to the next, so the file only changes when the list does.

To read the list straight from a shared Excel / Google Sheets link, see fetch_members.py.
"""
import argparse
import base64
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
NAME_ROUNDS = 20000                     # PBKDF2 rounds for the key that opens a name


def normalise(value):
    return re.sub(r"[^A-Z0-9]", "", str(value if value is not None else "").strip().upper())


def clean_name(value):
    return re.sub(r"\s+", " ", str(value if value is not None else "")).strip()


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


def find_column(header, wanted):
    matches = [i for i, h in enumerate(header) if h.lower() == wanted.lower()]
    if not matches:
        raise ValueError(f'No column called "{wanted}". Columns: {", ".join(header)}')
    return matches[0]


def pick_members(rows, column=None, name_column=None):
    """[(id, full name)], with the headers used. Names may be empty if the sheet has none."""
    rows = [r for r in rows if any(c not in (None, "") for c in r)]
    if not rows:
        raise ValueError("The sheet is empty.")
    header = [str(c or "").strip() for c in rows[0]]
    if column:
        col = find_column(header, column)
    else:
        # a header with "ID" as a word of its own, e.g. "LeMSIC ID", "Member-ID", "id_to_email"
        candidates = [i for i, h in enumerate(header) if re.search(r"(?<![a-z])id(?![a-z])", h, re.I)]
        col = candidates[0] if candidates else 0
    has_header = not normalise(rows[0][col]) or bool(re.search(r"id|member|name", header[col], re.I))
    # the name: a named column, "full name", "name", or first + last
    low = [h.lower() for h in header]
    name_cols, name_used = [], ""
    if name_column:
        name_cols = [find_column(header, name_column)]
    elif has_header:
        full = [i for i, h in enumerate(low) if "full name" in h or h in ("name", "member name", "student name")]
        first = [i for i, h in enumerate(low) if re.search(r"first\s*name|given", h)]
        last = [i for i, h in enumerate(low) if re.search(r"last\s*name|surname|family", h)]
        if full:
            name_cols = [full[0]]
        elif first:
            name_cols = first[:1] + last[:1]
    name_cols = [i for i in name_cols if i != col]
    if name_cols:
        name_used = " + ".join(header[i] for i in name_cols)
    members = {}
    for r in (rows[1:] if has_header else rows):
        if col >= len(r):
            continue
        mid = normalise(r[col])
        if not mid:
            continue
        name = clean_name(" ".join(str(r[i]) for i in name_cols if i < len(r) and r[i] not in (None, "")))
        if not members.get(mid):
            members[mid] = name
    if not members:
        raise ValueError("No IDs found in that column.")
    return sorted(members.items()), (header[col] if has_header else f"column {col + 1}"), name_used


def pick_ids(rows, column=None):
    """The IDs alone (kept for older callers)."""
    members, used, _ = pick_members(rows, column)
    return [m for m, _ in members], used


def seal_name(salt, member_id, name):
    """The name, encrypted with a key only that member's ID can make (the page reverses this)."""
    if not name:
        return ""
    data = name.encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", member_id.encode(), ("name:" + salt).encode(), NAME_ROUNDS, 32)
    stream = b"".join(hashlib.sha256(key + i.to_bytes(4, "big")).digest() for i in range(len(data) // 32 + 1))
    return base64.b64encode(bytes(a ^ b for a, b in zip(data, stream))).decode()


def existing_salt():
    try:
        with open(OUT) as f:
            m = re.search(r'"salt":\s*"([0-9a-f]+)"', f.read())
            return m.group(1) if m else None
    except OSError:
        return None


def write_members(members, salt=None, sample=False):
    """Write members.js from [(id, name)] (or plain IDs); returns True if its contents changed."""
    members = [(m, "") if isinstance(m, str) else m for m in members]
    salt = salt or os.environ.get("MEMBERS_SALT") or existing_salt() or secrets.token_hex(16)
    table = {hashlib.sha256((salt + mid).encode()).hexdigest(): seal_name(salt, mid, name) for mid, name in members}
    data = {"salt": salt, "count": len(table), "rounds": NAME_ROUNDS, "members": dict(sorted(table.items()))}
    if sample:
        data["sample"] = True
    content = ("// Generated from the LeMSIC member list by tools/import_members.py.\n"
               "// Fingerprints only: the IDs are not in this file, and each name opens only with its own ID.\n"
               "window.LEMSIC_MEMBERS = " + json.dumps(data) + ";\n")
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
    ap.add_argument("--name-column", help='header of the column holding the full names (default: "Full Name" or "Name")')
    args = ap.parse_args()
    try:
        with open(args.sheet, "rb") as f:
            members, used, name_used = pick_members(rows_from_bytes(f.read(), args.sheet), args.column, args.name_column)
    except ValueError as e:
        sys.exit(str(e))
    changed = write_members(members, sample=os.path.basename(args.sheet) == "sample-members.csv")
    named = sum(1 for _, n in members if n)
    print(f'{len(members)} member IDs from "{used}", {named} with names'
          f'{f" from {name_used!r}" if name_used else " (no name column found)"} -> {os.path.relpath(OUT, ROOT)}'
          f'{"" if changed else " (no change)"}')


if __name__ == "__main__":
    main()
