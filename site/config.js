// Settings for the LeMSIC Advent Calendar. Edit these, then reload the page.
window.ADVENT_CONFIG = {
  // The December the calendar runs in, and the clock it follows.
  year: 2026,
  timeZone: "Asia/Beirut",

  // Organiser preview: set a day (1-24) to try the calendar before December.
  // Set back to null before launch. (Test mode has its own date picker.)
  previewDay: null,

  // Optional: the web-app URL of the Google Sheet that keeps everyone's progress
  // (see backend/progress-sheet.gs for the 5-minute setup). With it, every picture a
  // member hangs is recorded there, and their wall follows them to other devices.
  // Leave empty to keep each student's wall in their own browser only.
  progressEndpoint: "https://script.google.com/macros/s/AKfycbz7uyPZwqCHPzygUJPfv1s7CfCW2Y7LUAXXN-5BDmvurUelF9Al39z3lJU7Ph6w9mR6dA/exec",

  // Test mode, for organisers: type this code instead of a LeMSIC ID at the door.
  // Every ornament on the tree opens, and nothing is saved or sent. Anyone who reads
  // this file can see the code, so it only guards the surprise. "" switches it off.
  testCode: "nta27",

  // Guests who aren't LeMSIC members type this to come in (shown under the door's
  // button). Their wall is kept in their own browser and never sent to the sheet.
  // "" switches it off.
  guestCode: "0000",

  // Shown when a student has hung all 24 pictures on their wall.
  prize: "You opened every ornament from 1 to 24 December and hung all 24 pictures on your wall. Show this screen to the LeMSIC team to claim your prize!",
};
