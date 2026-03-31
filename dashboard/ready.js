import {
  buildMarkAppliedPayload,
  fetchStore,
  getApplyPageUrl,
  getRealOfferUrl,
  humanize,
  postAction,
  renderMarkdownPreview,
} from "/dashboard/shared.js";

const buildLink = (href, label) => {
  if (!href) return `<span class="chip muted-chip">${label} unavailable</span>`;
  return `<a class="text-link" href="/${href}">${label}</a>`;
};

const buildExternalLink = (href, label) => {
  if (!href) return `<span class="chip muted-chip">${label} unavailable</span>`;
  return `<a class="text-link" href="${href}" target="_blank" rel="noreferrer">${label}</a>`;
};

const buildOptions = (values, label) => [
  `<option value="">All ${label}</option>`,
  ...values.map((value) => `<option value="${value}">${humanize(value)}</option>`),
].join("");

const init = async () => {
  const store = await fetchStore();
  const allReadyOffers = store.offers.filter((offer) => offer.status === "shortlisted");
  const searchInput = document.getElementById("ready-search");
  const roleSelect = document.getElementById("ready-role-family");
  const duplicateToggle = document.getElementById("ready-duplicates");
  const output = document.getElementById("ready-action-output");
  const roleFamilies = [...new Set(allReadyOffers.map((offer) => offer.roleFamily).filter(Boolean))];
  roleSelect.innerHTML = buildOptions(roleFamilies, "role families");

  const target = document.getElementById("ready-list");
  if (!allReadyOffers.length) {
    document.getElementById("ready-summary").textContent = "No shortlisted offers yet. Use Discovery or Offers to keep the strongest roles.";
    target.innerHTML = `<div class="empty-state">No shortlisted offers yet.</div>`;
    return;
  }

  const runAction = async (payload, label) => {
    output.classList.remove("hidden", "error");
    output.textContent = `Running: ${label}...`;
    target.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    try {
      const result = await postAction("/api/offer-action", payload);
      output.textContent = `${label} completed successfully.${result.stdout ? `\n\n${result.stdout}` : ""}`;
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      output.classList.add("error");
      output.textContent = String(error.message || error);
      target.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
    }
  };

  const render = () => {
    const search = searchInput.value.trim().toLowerCase();
    const roleFamily = roleSelect.value;
    const showDuplicates = duplicateToggle.checked;
    const filtered = allReadyOffers.filter((offer) => {
      if (!showDuplicates && offer.isDuplicate) return false;
      if (roleFamily && offer.roleFamily !== roleFamily) return false;
      if (!search) return true;
      return [offer.company, offer.role, offer.location, offer.summary].join(" ").toLowerCase().includes(search);
    });
    const hiddenDuplicates = allReadyOffers.filter((offer) => offer.isDuplicate).length;

    document.getElementById("ready-summary").textContent = filtered.length
      ? `${filtered.length} shortlisted offer(s). ${showDuplicates ? "Duplicates included." : `${hiddenDuplicates} duplicate(s) hidden by default.`}`
      : "No shortlisted offers match the current filters.";

    if (!filtered.length) {
      target.innerHTML = `<div class="empty-state">No shortlisted offers match the current filters.</div>`;
      return;
    }

    target.innerHTML = filtered
      .map(
        (offer, index) => `
          <article class="ready-card">
            <div class="ready-top">
              <div>
                <p class="opportunity-company">${offer.company}</p>
                <p class="opportunity-role">${offer.role}</p>
              </div>
              <div class="score-pill">${offer.scores.final}</div>
            </div>
            <div class="ready-meta">
              <span class="chip">${humanize(offer.roleFamily)}</span>
              <span class="chip">${humanize(offer.status)}</span>
              <span class="chip">${offer.location || "Unknown location"}</span>
              <span class="chip">${offer.applicationQuestions?.length || 0} question(s)</span>
              ${offer.reviewNeeded ? `<span class="chip">${humanize("review_needed")}</span>` : ""}
              ${offer.isDuplicate ? `<span class="chip muted-chip">Duplicate</span>` : ""}
            </div>
            <div class="ready-links">
              ${buildExternalLink(getRealOfferUrl(offer), "Open real offer")}
              ${
                getApplyPageUrl(offer) && getApplyPageUrl(offer) !== getRealOfferUrl(offer)
                  ? buildExternalLink(getApplyPageUrl(offer), "Open apply page")
                  : ""
              }
              ${buildLink(offer.paths.fit_report, "Open fit report")}
              ${buildLink(offer.paths.research, "Open research")}
              ${buildLink(offer.paths.decision, "Open decision log")}
              <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
            </div>
            <div class="action-bar compact-row">
              <button class="action-button primary" data-action="applied" data-index="${index}">Mark applied</button>
              <button class="action-button secondary" data-action="refresh" data-index="${index}">Refresh apply page</button>
              <button class="action-button secondary" data-action="rescore" data-index="${index}">Rescore</button>
            </div>
            <div class="preview-grid compact">
              <article class="preview-card">
                <div class="preview-head">
                  <strong>Fit report</strong>
                  <a class="text-link" href="/${offer.paths.fit_report}">Open file</a>
                </div>
                ${renderMarkdownPreview(offer.assetPreview?.fit_report || offer.summary || "")}
              </article>
              <article class="preview-card">
                <div class="preview-head">
                  <strong>Research preview</strong>
                  <a class="text-link" href="/${offer.paths.research}">Open file</a>
                </div>
                ${renderMarkdownPreview(offer.assetPreview?.research || "")}
              </article>
            </div>
          </article>
        `
      )
      .join("");

    target.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const offer = filtered[Number(button.dataset.index)];
        if (button.dataset.action === "applied") {
          runAction(
            buildMarkAppliedPayload(offer, "Submitted manually from Ready page"),
            `Mark ${offer.company} as applied`
          ).catch((error) => console.error(error));
        } else if (button.dataset.action === "refresh") {
          runAction(
            { action: "refresh_apply", jobId: offer.id, browser: "auto" },
            `Refresh apply page for ${offer.company}`
          ).catch((error) => console.error(error));
        } else if (button.dataset.action === "rescore") {
          runAction(
            { action: "score_offer", jobId: offer.id },
            `Rescore ${offer.company}`
          ).catch((error) => console.error(error));
        }
      });
    });
  };

  [searchInput, roleSelect, duplicateToggle].forEach((node) => {
    node.addEventListener("input", render);
    node.addEventListener("change", render);
  });
  render();
};

init().catch((error) => console.error(error));
