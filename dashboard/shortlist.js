import {
  buildMarkAppliedPayload,
  canMarkApplied,
  fetchStore,
  getRealOfferUrl,
  humanize,
  postAction,
  renderMarkdownPreview,
} from "/dashboard/shared.js";

const buildOptions = (values, label) => [
  `<option value="">All ${label}</option>`,
  ...values.map((value) => `<option value="${value}">${humanize(value)}</option>`),
].join("");

const deriveCandidates = (store) => {
  const direct = [...(store.shortlistCandidates || [])];
  if (direct.length) return direct;
  return [...(store.offers || [])]
    .filter(
      (offer) =>
        !offer.isDuplicate &&
        ["discovered", "screened", "scored", "shortlisted"].includes(offer.status) &&
        ["apply", "maybe"].includes(offer.recommendation) &&
        Number(offer?.scores?.final || 0) >= 75
    )
    .sort((left, right) => {
      const statusRank = (offer) => (offer.status === "shortlisted" ? 0 : 1);
      return (
        statusRank(left) - statusRank(right) ||
        Number(right?.scores?.final || 0) - Number(left?.scores?.final || 0) ||
        String(left.company || "").localeCompare(String(right.company || "")) ||
        String(left.role || "").localeCompare(String(right.role || ""))
      );
    })
    .slice(0, 24);
};

const init = async () => {
  const store = await fetchStore();
  const candidates = deriveCandidates(store);
  const searchInput = document.getElementById("shortlist-search");
  const roleSelect = document.getElementById("shortlist-role-family");
  const statusSelect = document.getElementById("shortlist-status");
  const target = document.getElementById("shortlist-list");
  const output = document.getElementById("shortlist-action-output");

  roleSelect.innerHTML = buildOptions([...new Set(candidates.map((item) => item.roleFamily).filter(Boolean))], "role families");
  statusSelect.innerHTML = buildOptions([...new Set(candidates.map((item) => item.status).filter(Boolean))], "statuses");

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
    const status = statusSelect.value;
    const filtered = candidates.filter((offer) => {
      if (roleFamily && offer.roleFamily !== roleFamily) return false;
      if (status && offer.status !== status) return false;
      if (!search) return true;
      return [offer.company, offer.role, offer.location, offer.summary, ...(offer.keywordsRequired || [])]
        .join(" ")
        .toLowerCase()
        .includes(search);
    });

    document.getElementById("shortlist-summary").textContent = filtered.length
      ? `${filtered.length} shortlist candidate(s) visible. Explicitly shortlisted offers stay at the top; other entries are high-fit candidates that still need a keep/skip decision.`
      : "No shortlist candidates match the current filters.";

    if (!filtered.length) {
      target.innerHTML = `<div class="empty-state">No shortlist candidates match the current filters.</div>`;
      return;
    }

    target.innerHTML = filtered
      .map(
        (offer, index) => `
          <article class="decision-card application-card">
            <div class="preview-head">
              <strong>${offer.company} - ${offer.role}</strong>
              <div class="ready-meta">
                <span class="chip">${humanize(offer.roleFamily)}</span>
                <span class="chip">${humanize(offer.status)}</span>
                <span class="chip">score ${offer.scores.final}</span>
              </div>
            </div>
            <p class="decision-meta">${offer.location || "Unknown location"} | ${offer.nextAction?.label || "Review manually"}</p>
            <p>${offer.summary || "No fit summary yet."}</p>
            <div class="chip-wrap">
              ${(offer.keywordsRequired || []).slice(0, 8).map((keyword) => `<span class="chip">${humanize(keyword)}</span>`).join("")}
            </div>
            <div class="action-bar compact-row">
              ${
                canMarkApplied(offer)
                  ? `<button class="action-button primary" data-index="${index}" data-action="applied">Mark applied</button>`
                  : ""
              }
              ${
                offer.status === "shortlisted"
                  ? `<button class="action-button secondary" data-index="${index}" data-action="unshortlist">Remove shortlist</button>`
                  : `<button class="action-button accent" data-index="${index}" data-action="shortlist">Shortlist</button>`
              }
              <button class="action-button primary" data-index="${index}" data-action="refresh">Inspect source</button>
              <button class="action-button secondary" data-index="${index}" data-action="rescore">Rescore</button>
              <button class="action-button danger" data-index="${index}" data-action="reject">Reject</button>
              <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
              ${getRealOfferUrl(offer) ? `<a class="text-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Open offer</a>` : ""}
            </div>
            <div class="preview-grid compact">
              <article class="preview-card">
                <div class="preview-head">
                  <strong>Fit summary</strong>
                  ${offer.applicationUrl ? `<a class="text-link" href="${offer.applicationUrl}" target="_blank" rel="noreferrer">Open source</a>` : ""}
                </div>
                ${renderMarkdownPreview(offer.assetPreview?.fit_report || offer.summary || "")}
              </article>
              <article class="preview-card">
                <div class="preview-head">
                  <strong>Research note</strong>
                  ${offer.assets.research ? `<a class="text-link" href="/${offer.paths.research}">Open file</a>` : ""}
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
        const action = button.dataset.action;
        if (action === "shortlist") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "shortlisted", note: "Shortlisted from Shortlist page" },
            `Shortlist ${offer.company}`
          ).catch((error) => console.error(error));
        } else if (action === "applied") {
          runAction(
            buildMarkAppliedPayload(offer, "Submitted manually from Shortlist page"),
            `Mark ${offer.company} as applied`
          ).catch((error) => console.error(error));
        } else if (action === "unshortlist") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "scored", note: "Removed from shortlist" },
            `Remove shortlist for ${offer.company}`
          ).catch((error) => console.error(error));
        } else if (action === "refresh") {
          runAction(
            { action: "refresh_apply", jobId: offer.id, browser: "auto" },
            `Inspect source for ${offer.company}`
          ).catch((error) => console.error(error));
        } else if (action === "rescore") {
          runAction(
            { action: "score_offer", jobId: offer.id },
            `Rescore ${offer.company}`
          ).catch((error) => console.error(error));
        } else if (action === "reject") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "rejected", note: "Rejected from shortlist review" },
            `Reject ${offer.company}`
          ).catch((error) => console.error(error));
        }
      });
    });
  };

  [searchInput, roleSelect, statusSelect].forEach((node) => {
    node.addEventListener("input", render);
    node.addEventListener("change", render);
  });
  render();
};

init().catch((error) => console.error(error));
