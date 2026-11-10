/**
 * LeMSIC Advent Calendar: keeps everyone's progress in a Google Sheet.
 *
 * Every time a student hangs a day's picture on their wall, the website sends it here.
 * The sheet then shows, for each member, how many of the 24 they have and which days,
 * so the team can see who has completed all 24 (and claim the prize). It also lets a
 * student's wall follow them from one phone or computer to another.
 *
 * Setup (once, about 5 minutes):
 *   1. Create a new Google Sheet (e.g. "LeMSIC Advent progress").
 *      Optional but recommended: add a tab named "Members" with a column of LeMSIC IDs and a
 *      column of full names, with headers such as "ID_to_email" and "Full Name" in row 1 (in
 *      either order; without headers, IDs go in column A and names in column B). Then only
 *      those IDs are recorded, and the names come from your list.
 *   2. In the sheet: Extensions > Apps Script. Delete what's there, paste this whole file,
 *      and save.
 *   3. Deploy > New deployment > Select type: Web app.
 *      Execute as: Me.  Who has access: Anyone.  Deploy, allow access, and copy the
 *      web app URL (it ends in /exec).
 *   4. Put that URL in site/config.js as progressEndpoint.
 *   (After changing this script later: Deploy > Manage deployments > edit > New version.)
 *
 * Tabs it fills in:
 *   Progress  one row per member: ID, name, how many of the 24 they've hung, which days,
 *             when they were last in, and "Yes" once all 24 are on their wall.
 *   Log       one row per picture hung: when, ID, name, day, and whether it was on its day.
 */
const TZ = 'Asia/Beirut';

// the website sends one picture hung: {id, name, day, at}
function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const data = JSON.parse(e.postData.contents);
    const id = normalise(data.id);
    const day = Number(data.day);
    if (!id || !(day >= 1 && day <= 24)) return reply({ ok: false, reason: 'bad request' });

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const known = memberNames(ss);
    if (known && !(id in known)) return reply({ ok: false, reason: 'unknown member' });
    const name = (known && known[id]) || String(data.name || '').slice(0, 120);

    const now = new Date();
    const onTime = Number(Utilities.formatDate(now, TZ, 'M')) === 12 && Number(Utilities.formatDate(now, TZ, 'd')) === day;
    const log = sheet(ss, 'Log', ['Received', 'LeMSIC ID', 'Name', 'Day', 'On its day']);
    log.appendRow([now, id, name, day, onTime ? 'Yes' : 'No']);
    const days = updateProgress(ss, log, id, name, now);
    return reply({ ok: true, onTime: onTime, count: days.length });
  } finally {
    lock.releaseLock();
  }
}

// the website asks which days a member has hung, to restore their wall on another device
function doGet(e) {
  const id = normalise(e && e.parameter && e.parameter.id);
  if (!id) return reply({ ok: false, reason: 'no id' });
  const log = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Log');
  return reply({ ok: true, days: log ? daysFor(log, id) : [] });
}

function daysFor(log, id) {
  const days = {};
  log.getDataRange().getValues().slice(1).forEach((r) => {
    if (normalise(r[1]) === id && r[4] === 'Yes') days[Number(r[3])] = true;
  });
  return Object.keys(days).map(Number).sort((a, b) => a - b);
}

function updateProgress(ss, log, id, name, now) {
  const days = daysFor(log, id);
  const progress = sheet(ss, 'Progress', ['LeMSIC ID', 'Name', 'Pictures hung (of 24)', 'Days', 'Last in', 'All 24']);
  const ids = progress.getDataRange().getValues().map((r) => normalise(r[0]));
  const row = ids.indexOf(id);
  const values = [id, name, days.length, days.join(', '), now, days.length >= 24 ? 'Yes' : ''];
  if (row === -1) progress.appendRow(values);
  else progress.getRange(row + 1, 1, 1, values.length).setValues([values]);
  return days;
}

// the optional Members tab: found by its headers (an "ID" column and a "Name" column, in any
// order), or without headers, IDs in column A and names in column B
function memberNames(ss) {
  const members = ss.getSheetByName('Members');
  if (!members || members.getLastRow() === 0) return null;
  const rows = members.getDataRange().getValues();
  const head = rows[0].map((h) => String(h || '').trim().toLowerCase());
  let idCol = head.findIndex((h) => /(^|[^a-z])id([^a-z]|$)/.test(h));
  let nameCol = head.findIndex((h) => /name/.test(h));
  let start = 1;
  if (idCol === -1) { idCol = 0; nameCol = 1; start = 0; }
  if (nameCol === -1 || nameCol === idCol) nameCol = idCol === 0 ? 1 : 0;
  const out = {};
  rows.slice(start).forEach((r) => {
    const id = normalise(r[idCol]);
    if (id) out[id] = String(r[nameCol] || '').trim();
  });
  return out;
}

function sheet(ss, name, header) {
  const s = ss.getSheetByName(name) || ss.insertSheet(name);
  if (s.getLastRow() === 0) {
    s.appendRow(header);
    s.setFrozenRows(1);
    s.getRange(1, 1, 1, header.length).setFontWeight('bold');
  }
  return s;
}

function normalise(v) {
  return String(v || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
