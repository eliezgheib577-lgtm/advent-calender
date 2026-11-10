// Settings for the LeMSIC Advent Calendar. Edit these, then reload the page.
window.ADVENT_CONFIG = {
  // The December the calendar runs in, and the clock it follows.
  year: 2026,
  timeZone: "Asia/Beirut",

  // Organiser preview: set a day (1-24) to try the calendar before December,
  // or add #day-7 (any day) to the page address. Set back to null before launch.
  previewDay: null,

  // Optional: the web-app URL of a Google Apps Script that records answers in a
  // Google Sheet (see backend/answers-sheet.gs). Leave empty to keep answers in
  // each student's own browser only.
  answersEndpoint: "",

  // Test mode, for organisers: type this code instead of a LeMSIC ID at the door.
  // Every ornament opens (with a "Skip to the picture" button), and nothing is saved
  // or sent. Anyone who reads this file can see the code, so it only guards the
  // surprise, not the answers. Set it to "" to switch test mode off.
  testCode: "LEMSIC-TEST",

  // Shown when a student has answered all 24 days.
  prize: "You opened every door from 1 to 24 December. Show this screen to the LeMSIC team to claim your prize!",
};
