// Applied before paint so the stored theme does not flash.
(function () {
  try {
    var stored = localStorage.getItem("wiserone-theme");
    if (stored === "dark" || stored === "light") {
      document.documentElement.setAttribute("data-theme", stored);
    }
  } catch (e) {
    /* storage unavailable — fall back to prefers-color-scheme */
  }
})();
