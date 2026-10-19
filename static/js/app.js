/* Small vanilla JavaScript helpers (no frameworks). */
document.addEventListener("DOMContentLoaded", function () {
  /* 1. Custody form: show / hide the From and To fields depending on the action. */
  var action = document.getElementById("id_action_type");
  var fromBox = document.getElementById("wrap_from_party");
  var toBox = document.getElementById("wrap_to_party");
  if (action && fromBox && toBox) {
    var update = function () {
      var needsRoute = action.value === "TRANSFERRED" || action.value === "RETURNED";
      fromBox.style.display = needsRoute || fromBox.querySelector("input").value ? "" : "none";
      toBox.style.display = needsRoute || toBox.querySelector("input").value ? "" : "none";
    };
    action.addEventListener("change", update);
    update();
  }

  /* 2. Confirm before actions marked with data-confirm. */
  document.querySelectorAll("[data-confirm]").forEach(function (element) {
    element.addEventListener("submit", function (event) {
      if (!window.confirm(element.getAttribute("data-confirm"))) { event.preventDefault(); }
    });
  });

  /* 3. Disable submit buttons after the first click (prevents double submissions
        while a large evidence file is being hashed). */
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("button[type=submit]");
      if (button) { button.disabled = true; button.textContent = "Working..."; }
    });
  });
});
