// Small progressive enhancements. Every page works without this file.
(function () {
  "use strict";

  // "/" focuses the search box unless the user is typing somewhere.
  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    var target = event.target;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable) return;
    var search = document.querySelector("[data-search]");
    if (search) { event.preventDefault(); search.focus(); }
  });

  // Outcome list filters: buttons carry data-filter, rows carry data-kind.
  document.querySelectorAll("[data-filters]").forEach(function (group) {
    var list = document.getElementById(group.dataset.filters);
    if (!list) return;
    group.hidden = false;
    group.querySelectorAll("button").forEach(function (button) {
      button.addEventListener("click", function () {
        group.querySelectorAll("button").forEach(function (other) {
          other.setAttribute("aria-pressed", String(other === button));
        });
        var filter = button.dataset.filter;
        list.querySelectorAll("[data-kind]").forEach(function (row) {
          row.hidden = filter !== "all" && row.dataset.kind.split(" ").indexOf(filter) < 0;
        });
      });
    });
  });

  // Chart bars open the outcome they point at.
  document.querySelectorAll(".bars a[href^='#']").forEach(function (bar) {
    bar.addEventListener("click", function () {
      var row = document.getElementById(bar.getAttribute("href").slice(1));
      if (row && row.tagName === "DETAILS") row.open = true;
    });
  });

  // Grade editor: live percentage, inline checks and unsaved-change count.
  var form = document.querySelector("[data-grade-form]");
  if (!form) return;
  var FILL = [[0, [166, 61, 61]], [40, [194, 101, 42]], [60, [192, 138, 43]], [75, [125, 139, 53]], [85, [62, 123, 85]], [100, [45, 106, 79]]];
  var TEXT = [[0, [142, 47, 47]], [40, [159, 76, 23]], [60, [143, 101, 20]], [75, [91, 103, 36]], [85, [46, 99, 67]], [100, [36, 86, 63]]];
  function mix(stops, value) {
    for (var i = 1; i < stops.length; i++) {
      if (value <= stops[i][0]) {
        var a = stops[i - 1], b = stops[i], t = (value - a[0]) / (b[0] - a[0]);
        return "rgb(" + a[1].map(function (x, k) { return Math.round(x + t * (b[1][k] - x)); }).join(",") + ")";
      }
    }
    return "rgb(" + stops[stops.length - 1][1].join(",") + ")";
  }
  function format(value) { return (Math.round(value * 100) / 100).toFixed(2).replace(/\.00$/, ""); }

  var inputs = form.querySelectorAll("input[data-max]");
  var pending = form.querySelector("[data-pending]");
  var dirty = false;
  inputs.forEach(function (input) { input.dataset.initial = input.value.trim(); });

  function update(input) {
    var live = document.getElementById(input.id + "_live");
    var raw = input.value.trim().replace(",", ".");
    var max = parseFloat(input.dataset.max);
    var bad = false;
    if (live) { live.className = "live"; live.removeAttribute("style"); }
    if (raw === "") {
      if (live) { live.className = "live empty"; live.textContent = "Not graded yet"; }
    } else if (!/^\d+(\.\d{1,2})?$/.test(raw)) {
      bad = "Use a number like 42.5";
    } else if (parseFloat(raw) > max) {
      bad = "Maximum is " + input.dataset.max;
    } else if (live) {
      var percent = parseFloat(raw) / max * 100;
      live.style.setProperty("--c", mix(FILL, percent));
      live.style.setProperty("--t", mix(TEXT, percent));
      live.innerHTML = '<i class="sf" aria-hidden="true"></i><span class="sc"></span>';
      live.querySelector(".sc").textContent = format(percent) + "%";
    }
    if (bad && live) { live.className = "live err"; live.textContent = bad; }
    if (bad) input.setAttribute("aria-invalid", "true"); else if (!input.dataset.serverError) input.removeAttribute("aria-invalid");
    input.classList.toggle("changed", input.value.trim() !== input.dataset.initial);
    return { changed: input.value.trim() !== input.dataset.initial, bad: !!bad };
  }
  function refresh() {
    var changed = 0, bad = 0;
    inputs.forEach(function (input) {
      var state = update(input);
      if (state.changed) changed++;
      if (state.bad) bad++;
    });
    dirty = changed > 0;
    if (pending) {
      pending.textContent = bad ? bad + (bad === 1 ? " score needs fixing" : " scores need fixing")
        : changed ? changed + (changed === 1 ? " unsaved change" : " unsaved changes") : "No changes yet";
      pending.className = "pending" + (changed && !bad ? " has" : "");
    }
  }
  inputs.forEach(function (input) {
    if (input.getAttribute("aria-invalid") === "true") input.dataset.serverError = "1";
    input.addEventListener("input", function () { delete input.dataset.serverError; refresh(); });
  });
  refresh();

  // Grade book: Enter or the arrow keys move down/up the same assessment column.
  if (form.hasAttribute("data-grid")) {
    form.addEventListener("keydown", function (event) {
      var input = event.target;
      if (!input.matches || !input.matches("input[data-max]")) return;
      var step = event.key === "Enter" || event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
      if (!step) return;
      event.preventDefault();
      var cell = input.closest("td"), row = cell.parentElement;
      var column = Array.prototype.indexOf.call(row.children, cell);
      var next = step > 0 ? row.nextElementSibling : row.previousElementSibling;
      var target = next && next.children[column] && next.children[column].querySelector("input[data-max]");
      if (target) { target.focus(); target.select(); }
    });
  }

  // "Enter grade" links point at one assessment (#id_score_N): start typing there.
  var target = location.hash && document.getElementById(location.hash.slice(1));
  if (target && target.matches("input[data-max]")) { target.focus(); target.select(); }
  form.addEventListener("submit", function () { dirty = false; });
  window.addEventListener("beforeunload", function (event) {
    if (dirty) { event.preventDefault(); event.returnValue = ""; }
  });
})();
