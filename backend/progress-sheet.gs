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
 *   (After changing this script later: Deploy > Manage deployments > edit > New version.
 *   If the Progress tab was made by an older version, it is rebuilt in the new layout from the
 *   Log the next time a picture comes in; to do it straight away, choose rebuildProgress in
 *   the editor's toolbar and press Run.)
 *
 * Tabs it fills in:
 *   Progress  one row per member: name, LeMSIC ID, then the days 1 to 24 (a tick under each
 *             day whose picture they hung on its day), and at the end "All 24": Yes once all
 *             24 are filled in, and then the whole row turns green.
 *   Log       one row per picture hung: when, ID, name, day, and whether it was on its day.
 *
 * Practice runs: in the website's test mode, ticking "Practice run" makes it behave like a member on
 * the day the test pretends it is, and each picture comes here under the ID TEST (name "Test run").
 * Those rows show how real ones will look; "Remove TEST from the sheet" on the test panel takes them
 * all out again. Only the ID TEST is let in this way.
 */
const TZ = 'Asia/Beirut';
const TEST_ID = 'TEST';
const DAYS = 24;
const TICK = '✓';
const PROGRESS_HEAD = ['Name', 'LeMSIC ID'].concat(Array.from({ length: DAYS }, (_, i) => i + 1), ['All 24']);
const COMPLETE = '#b7e1cd';                      // the green of a row with all 24

// the website sends one picture hung: {id, name, day, at}
function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const data = JSON.parse(e.postData.contents);
    const id = normalise(data.id);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const practice = data.test === true && id === TEST_ID;          // a practice run from the website's test mode
    if (practice && data.clear) return reply({ ok: true, removed: removePractice(ss) });
    const day = Number(data.day);
    if (!id || !(day >= 1 && day <= 24)) return reply({ ok: false, reason: 'bad request' });

    const known = practice ? null : memberNames(ss);
    if (known && !(id in known)) return reply({ ok: false, reason: 'unknown member' });
    const name = practice ? 'Test run' : (known && known[id]) || String(data.name || '').slice(0, 120);

    const now = new Date();
    // on its day: hung on that day of December in Lebanon (a practice run: on the day the test pretends it is)
    const onTime = practice ? Number(data.today) === day
      : Number(Utilities.formatDate(now, TZ, 'M')) === 12 && Number(Utilities.formatDate(now, TZ, 'd')) === day;
    const log = sheet(ss, 'Log', ['Received', 'LeMSIC ID', 'Name', 'Day', 'On its day']);
    log.appendRow([now, id, name, day, onTime ? 'Yes' : 'No']);
    const days = updateProgress(ss, log, id, name);
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
  return everyonesDays(log)[id] || [];
}

// from the Log: each member's days hung on their day ({id: [days]}), and their names ({id: name})
function everyonesDays(log, names) {
  const days = {};
  log.getDataRange().getValues().slice(1).forEach((r) => {
    const id = normalise(r[1]);
    if (!id) return;
    if (names) names[id] = String(r[2] || names[id] || '');
    days[id] = days[id] || {};
    if (r[4] === 'Yes') days[id][Number(r[3])] = true;
  });
  const out = {};
  Object.keys(days).forEach((id) => { out[id] = Object.keys(days[id]).map(Number).sort((a, b) => a - b); });
  return out;
}

// one member's row on the Progress tab (row: its row number, for the All 24 check)
function progressRow(row, id, name, days) {
  const ticks = [];
  for (let d = 1; d <= DAYS; d++) ticks.push(days.indexOf(d) >= 0 ? TICK : '');
  return [name, id].concat(ticks, [`=IF(COUNTA(C${row}:Z${row})=${DAYS},"Yes","")`]);
}

function updateProgress(ss, log, id, name) {
  const days = daysFor(log, id);
  let tab = ss.getSheetByName('Progress');
  const head = tab && tab.getLastRow() ? tab.getRange(1, 1, 1, PROGRESS_HEAD.length).getValues()[0].join('|') : '';
  if (head !== PROGRESS_HEAD.join('|')) {
    rebuildProgress();                               // (new, or made by an older version of this script)
    return days;
  }
  const ids = tab.getRange(1, 2, tab.getLastRow(), 1).getValues().map((r) => normalise(r[0]));
  const row = ids.indexOf(id) >= 0 ? ids.indexOf(id) + 1 : tab.getLastRow() + 1;
  if (row > tab.getMaxRows()) tab.insertRowsAfter(tab.getMaxRows(), 100);
  tab.getRange(row, 1, 1, PROGRESS_HEAD.length).setValues([progressRow(row, id, name, days)]);
  return days;
}

// the Progress tab made again from the Log: name, ID, a tick for each of the days 1 to 24, and All 24;
// a row with all 24 filled in turns green
function rebuildProgress() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = sheet(ss, 'Log', ['Received', 'LeMSIC ID', 'Name', 'Day', 'On its day']);
  const known = memberNames(ss) || {};
  const names = {};
  const days = everyonesDays(log, names);
  const tab = ss.getSheetByName('Progress') || ss.insertSheet('Progress');
  tab.clear();
  tab.getRange(1, 1, 1, PROGRESS_HEAD.length).setValues([PROGRESS_HEAD]).setFontWeight('bold').setHorizontalAlignment('center');
  tab.setFrozenRows(1);
  tab.setFrozenColumns(2);
  tab.setColumnWidth(1, 190);
  tab.setColumnWidth(2, 120);
  tab.setColumnWidths(3, DAYS, 32);
  tab.setColumnWidth(PROGRESS_HEAD.length, 64);
  const rows = Object.keys(days).map((id, k) => progressRow(k + 2, id, known[id] || names[id], days[id]));
  if (rows.length) tab.getRange(2, 1, rows.length, PROGRESS_HEAD.length).setValues(rows);
  const body = tab.getRange(2, 1, tab.getMaxRows() - 1, PROGRESS_HEAD.length);
  tab.getRange(2, 3, tab.getMaxRows() - 1, DAYS + 1).setHorizontalAlignment('center');
  tab.setConditionalFormatRules([SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied(`=COUNTA($C2:$Z2)=${DAYS}`)
    .setBackground(COMPLETE)
    .setBold(true)
    .setRanges([body])
    .build()]);
  return tab;
}

// takes every practice-run row (ID TEST) out of the Log and Progress tabs; returns how many pictures went
function removePractice(ss) {
  let removed = 0;
  [['Log', 1], ['Progress', 1]].forEach(([name, col]) => {
    const tab = ss.getSheetByName(name);
    if (!tab) return;
    const rows = tab.getDataRange().getValues();
    for (let i = rows.length - 1; i >= 1; i--) {
      if (normalise(rows[i][col]) === TEST_ID) {
        tab.deleteRow(i + 1);
        if (name === 'Log') removed += 1;
      }
    }
  });
  return removed;
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
