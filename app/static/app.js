(() => {
  const buttonTimers = new WeakMap();
  let statusTimer;

  function legacyCopy(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    textarea.style.pointerEvents = "none";
    document.body.appendChild(textarea);
    textarea.select();

    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) {
      throw new Error("Clipboard copy failed");
    }
  }

  function legacyCopyElement(element) {
    const selection = window.getSelection();
    if (!selection) {
      throw new Error("Selection API is unavailable");
    }

    const savedRanges = [];
    for (let index = 0; index < selection.rangeCount; index += 1) {
      savedRanges.push(selection.getRangeAt(index));
    }

    const range = document.createRange();
    range.selectNodeContents(element);
    selection.removeAllRanges();
    selection.addRange(range);

    let copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      selection.removeAllRanges();
      savedRanges.forEach((savedRange) => selection.addRange(savedRange));
    }

    if (!copied) {
      throw new Error("Rich clipboard copy failed");
    }
  }

  async function copyPlainText(text) {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    legacyCopy(text);
  }

  async function copyArticle(element) {
    const html = element.innerHTML.trim();
    const plainText = element.innerText.trim();

    if (
      navigator.clipboard?.write &&
      window.ClipboardItem &&
      window.isSecureContext
    ) {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": new Blob([html], { type: "text/html" }),
            "text/plain": new Blob([plainText], { type: "text/plain" }),
          }),
        ]);
        return;
      } catch (error) {
        // Try the browser's selection-based copy path below.
      }
    }

    try {
      legacyCopyElement(element);
      return;
    } catch (error) {
      // The final fallback copies the HTML source as plain text.
    }

    await copyPlainText(html);
  }

  function showStatus(message, type) {
    const status = document.querySelector("#copy-status");
    if (!status) {
      return;
    }

    window.clearTimeout(statusTimer);
    status.textContent = message;
    status.className = `copy-status copy-status-${type} is-visible`;
    status.hidden = false;

    statusTimer = window.setTimeout(() => {
      status.classList.remove("is-visible");
      window.setTimeout(() => {
        status.hidden = true;
      }, 180);
    }, 3600);
  }

  function showButtonSuccess(button) {
    const currentTimer = buttonTimers.get(button);
    if (currentTimer) {
      window.clearTimeout(currentTimer);
    }

    button.textContent = button.dataset.successLabel;
    button.classList.add("is-copied");

    const timer = window.setTimeout(() => {
      button.textContent = button.dataset.defaultLabel;
      button.classList.remove("is-copied");
      buttonTimers.delete(button);
    }, 2400);
    buttonTimers.set(button, timer);
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy-target]");
    if (!button) {
      return;
    }

    const target = document.querySelector(button.dataset.copyTarget);
    if (!target) {
      showStatus("コピー対象が見つかりませんでした。", "error");
      return;
    }

    button.disabled = true;
    try {
      if (button.dataset.copyKind === "article") {
        await copyArticle(target);
        showStatus(
          "記事本文をコピーしました。記事編集画面へそのまま貼り付けられます。",
          "success",
        );
      } else {
        await copyPlainText(target.value);
        showStatus("記事タイトルをコピーしました。", "success");
      }
      showButtonSuccess(button);
    } catch (error) {
      showStatus(
        "コピーできませんでした。ブラウザのクリップボード権限を確認してください。",
        "error",
      );
    } finally {
      button.disabled = false;
    }
  });
})();
