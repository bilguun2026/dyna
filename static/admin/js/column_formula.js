// Prevent re-initialization
if (window.formulaEditorInitialized) {
  return;
}
window.formulaEditorInitialized = true;

document.addEventListener("DOMContentLoaded", function () {
  const formulaInput = document.querySelector(".formula-input");
  const previewResult = document.getElementById("preview-result");
  const suggestionsDiv = document.getElementById("column-suggestions");
  const calcButtons = document.querySelectorAll(".calc-btn");

  if (!formulaInput) return;

  const columns = formulaInput.dataset.columns
    ? formulaInput.dataset.columns.split(",")
    : [];
  const functions = formulaInput.dataset.functions
    ? formulaInput.dataset.functions.split(",")
    : [];

  // Named function for calc button click handler
  function handleCalcButtonClick() {
    const value = this.dataset.value;
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    formulaInput.value =
      formulaInput.value.substring(0, start) +
      value +
      formulaInput.value.substring(end);
    formulaInput.focus();
    formulaInput.selectionStart = formulaInput.selectionEnd =
      start + value.length;
    updatePreview();
  }

  // Attach click event listeners to calculator buttons
  calcButtons.forEach((button) => {
    // Remove any existing listeners to prevent duplicates
    button.removeEventListener("click", handleCalcButtonClick);
    button.addEventListener("click", handleCalcButtonClick);
  });
  console.log("Available columns:", columns);

  // Autocomplete suggestions
  formulaInput.addEventListener("input", function (e) {
    updatePreview();
    const cursorPos = this.selectionStart;
    const textBeforeCursor = this.value.substring(0, cursorPos);
    const lastWord = textBeforeCursor.split(/[\s+\-*/()]+/).pop();

    if (lastWord.length > 0) {
      const matches = [...columns, ...functions].filter((item) =>
        item.startsWith(lastWord)
      );
      if (matches.length > 0) {
        suggestionsDiv.innerHTML = matches
          .map((match) => `<div class="suggestion-item">${match}</div>`)
          .join("");
        suggestionsDiv.style.display = "block";
        suggestionsDiv.style.left = `${formulaInput.offsetLeft}px`;
        suggestionsDiv.style.width = `${formulaInput.offsetWidth}px`;
        suggestionsDiv.style.top = `${
          formulaInput.offsetTop + formulaInput.offsetHeight
        }px`;
      } else {
        suggestionsDiv.style.display = "none";
      }
    } else {
      suggestionsDiv.style.display = "none";
    }
  });

  // Handle suggestion clicks
  suggestionsDiv.addEventListener("click", function (e) {
    if (e.target.classList.contains("suggestion-item")) {
      const suggestion = e.target.textContent;
      const cursorPos = formulaInput.selectionStart;
      const textBeforeCursor = formulaInput.value.substring(0, cursorPos);
      const textAfterCursor = formulaInput.value.substring(cursorPos);
      const lastWord = textBeforeCursor.split(/[\s+\-*/()]+/).pop();
      const newText =
        textBeforeCursor.substring(
          0,
          textBeforeCursor.length - lastWord.length
        ) + suggestion;
      formulaInput.value = newText + textAfterCursor;
      formulaInput.focus();
      formulaInput.selectionStart = formulaInput.selectionEnd = newText.length;
      suggestionsDiv.style.display = "none";
      updatePreview();
    }
  });

  // Hide suggestions when clicking outside
  document.addEventListener("click", function (e) {
    if (
      !formulaInput.contains(e.target) &&
      !suggestionsDiv.contains(e.target)
    ) {
      suggestionsDiv.style.display = "none";
    }
  });

  // Handle column dropdown selection
  const columnSelect = document.getElementById("id_selected_columns");
  if (columnSelect) {
    columnSelect.addEventListener("change", function () {
      try {
        const selected = Array.from(this.selectedOptions)
          .map((option) => option.value)
          .join(" + ");
        formulaInput.value += (formulaInput.value ? " + " : "") + selected;
        formulaInput.focus();
        updatePreview();
      } catch (error) {
        console.error("Error in column selection:", error);
      }
    });
  }

  // Real-time preview (simplified for demo)
  function updatePreview() {
    const formula = formulaInput.value.trim();
    if (!formula) {
      previewResult.textContent = "Enter a formula to see the preview";
      return;
    }

    try {
      previewResult.textContent =
        "Validating... (Full calculation requires backend)";
    } catch (e) {
      previewResult.textContent = "Invalid formula";
      console.error("Preview error:", e);
    }
  }

  // Initial preview update
  updatePreview();
});
