/**
 * LeMSIC Advent Calendar: records every answer in a Google Sheet, so the team can
 * see who answered all 24 days.
 *
 * Setup (once):
 *   1. Create a Google Sheet. Optional: add a tab named "Members" with the LeMSIC IDs
 *      in column A (paste them from the Excel list); answers from other IDs are refused.
 *   2. In the sheet: Extensions > Apps Script. Paste this whole file and save.
 *   3. Deploy > New deployment > type "Web app". Execute as: Me.
 *      Who has access: Anyone. Deploy, and copy the web app URL.
 *   4. Put that URL in site/config.js as answersEndpoint.
 *
 * Tabs it fills in:
 *   Answers   one row per answer: when, ID, day, answer, whether it was on the right day
 *   Progress  one row per member: days answered on time, and "Yes" once all 24 are done
 */
const TZ = 'Asia/Beirut';

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const data = JSON.parse(e.postData.contents);
    const id = normalise(data.id);
    const day = Number(data.day);
    if (!id || !(day >= 1 && day <= 24)) return reply({ ok: false, reason: 'bad request' });

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const members = ss.getSheetByName('Members');
    if (members) {
      const known = members.getRange(1, 1, Math.max(members.getLastRow(), 1), 1).getValues().map((r) => normalise(r[0]));
      if (known.indexOf(id) === -1) return reply({ ok: false, reason: 'unknown member' });
    }

    const now = new Date();
    const onTime = Number(Utilities.formatDate(now, TZ, 'M')) === 12 && Number(Utilities.formatDate(now, TZ, 'd')) === day;
    const answers = sheet(ss, 'Answers', ['Received', 'LeMSIC ID', 'Day', 'Answer', 'On the day']);
    answers.appendRow([now, id, day, String(data.answer || '').slice(0, 400), onTime ? 'Yes' : 'No']);
    const count = updateProgress(ss, answers, id);
    return reply({ ok: true, onTime: onTime, daysAnswered: count });
  } finally {
    lock.releaseLock();
  }
}

function updateProgress(ss, answers, id) {
  const rows = answers.getDataRange().getValues().slice(1);
  const days = {};
  rows.forEach((r) => { if (r[1] === id && r[4] === 'Yes') days[r[2]] = true; });
  const count = Object.keys(days).length;
  const progress = sheet(ss, 'Progress', ['LeMSIC ID', 'Days answered on time', 'All 24 done']);
  const ids = progress.getDataRange().getValues().map((r) => r[0]);
  const row = ids.indexOf(id);
  const values = [[id, count, count >= 24 ? 'Yes' : '']];
  if (row === -1) progress.appendRow(values[0]);
  else progress.getRange(row + 1, 1, 1, 3).setValues(values);
  return count;
}

function sheet(ss, name, header) {
  const s = ss.getSheetByName(name) || ss.insertSheet(name);
  if (s.getLastRow() === 0) s.appendRow(header);
  return s;
}

function normalise(v) {
  return String(v || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
