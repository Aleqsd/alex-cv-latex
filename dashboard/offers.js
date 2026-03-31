import {
  buildMarkAppliedPayload,
  canMarkApplied,
  fetchStore,
  getApplyPageUrl,
  getRealOfferUrl,
  humanize,
  postAction,
  renderMarkdownPreview,
} from "/dashboard/shared.js";

const renderStatusMeta = (offer) => {
  const parts = [];
  if (typeof offer.statusAgeDays === "number") {
    parts.push(`${offer.statusAgeDays}d in status`);
  }
  if (offer.followUpDueAt) {
    const label = offer.followUpOverdue ? "follow-up overdue" : `follow-up ${offer.followUpDueAt.slice(0, 10)}`;
    parts.push(label);
  }
  return parts.length ? `<p class="asset-meta">${parts.join(" | ")}</p>` : "";
};

const buildOptions = (values, label) => [
  `<option value="">All ${label}</option>`,
  ...values.map((value) => `<option value="${value}">${humanize(value)}</option>`),
].join("");

const matchesSearch = (offer, search) => {
  if (!search) return true;
  const haystack = [
    offer.company,
    offer.role,
    offer.location,
    offer.roleFamily,
    offer.summary,
    ...(offer.keywordsRequired || []),
    ...(offer.keywordsPreferred || []),
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(search);
};

const primaryActionForOffer = (offer) => {
  if (offer.status === "shortlisted") {
    return {
      label: "Inspect source",
      payload: {
        action: "refresh_apply",
        jobId: offer.id,
        browser: "auto",
      },
    };
  }
  if (offer.nextAction?.kind === "shortlist_offer") {
    return {
      label: "Shortlist",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "shortlisted",
        note: "Shortlisted from Offers page",
      },
    };
  }
  return {
    label: "Rescore",
    payload: {
      action: "score_offer",
      jobId: offer.id,
    },
  };
};

const init = async () => {
  const store = await fetchStore();
  const offers = [...store.offers].sort((a, b) => (b.scores.final || 0) - (a.scores.final || 0));
  const searchInput = document.getElementById("offers-search");
  const statusSelect = document.getElementById("offers-status");
  const presetSelect = document.getElementById("offers-preset");
  const roleSelect = document.getElementById("offers-role-family");
  const duplicateToggle = document.getElementById("offers-duplicates");
  const uniqueStatuses = [...new Set(offers.map((offer) => offer.status).filter(Boolean))];
  const uniqueRoleFamilies = [...new Set(offers.map((offer) => offer.roleFamily).filter(Boolean))];
  statusSelect.innerHTML = [
    `<option value="active" selected>Active offers</option>`,
    ...uniqueStatuses.map((value) => `<option value="${value}">${humanize(value)}</option>`),
  ].join("");
  roleSelect.innerHTML = buildOptions(uniqueRoleFamilies, "role families");

  const table = document.getElementById("offer-table");
  const summary = document.getElementById("offers-summary");
  const output = document.getElementById("offers-action-output");

  const runAction = async (label, payload) => {
    output.classList.remove("hidden", "error");
    output.textContent = `Running: ${label}...`;
    table.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    try {
      const result = await postAction("/api/offer-action", payload);
      output.textContent = `${label} completed successfully.${result.stdout ? `\n\n${result.stdout}` : ""}`;
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      output.classList.add("error");
      output.textContent = String(error.message || error);
      table.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
    }
  };

  const render = () => {
    const search = searchInput.value.trim().toLowerCase();
    const status = statusSelect.value;
    const preset = presetSelect.value;
    const roleFamily = roleSelect.value;
    const showDuplicates = duplicateToggle.checked;
    const filtered = offers.filter(
      (offer) => {
        if (!showDuplicates && offer.isDuplicate) return false;
        if (status && (status === "active" ? offer.status === "archived" : offer.status !== status)) return false;
        if (roleFamily && offer.roleFamily !== roleFamily) return false;
        if (!matchesSearch(offer, search)) return false;
        if (preset === "best_fit") {
          return offer.autoShortlist || (offer.recommendation === "apply" && (offer.scores.final || 0) >= 85);
        }
        if (preset === "needs_review") {
          return !!offer.reviewNeeded || offer.nextAction?.kind === "manual_review" || offer.status === "shortlisted";
        }
        return true;
      }
    );
    const hiddenDuplicates = offers.filter((offer) => offer.isDuplicate).length;

    const totalVisibleBase = status === "active" ? offers.filter((offer) => offer.status !== "archived").length : offers.length;
    summary.textContent = filtered.length === totalVisibleBase
      ? `${totalVisibleBase} offer(s) shown`
      : `${filtered.length} of ${totalVisibleBase} offer(s) shown${showDuplicates ? "" : `, ${hiddenDuplicates} duplicate(s) hidden`}`;

    if (!filtered.length) {
      table.innerHTML = `<div class="empty-state">No offers match the current filters.</div>`;
      return;
    }

    table.innerHTML = `
      <div class="offer-table-head">
        <span>Company</span>
        <span>Role</span>
        <span>Status</span>
        <span>Scores</span>
        <span>Action</span>
      </div>
      ${filtered
        .map((offer, index) => {
          const primaryAction = primaryActionForOffer(offer);
          return `
            <article class="offer-entry">
              <div class="offer-row">
                <div>
                  <strong>${offer.company}</strong>
                  <p class="asset-meta">${humanize(offer.companyStage || "unknown_stage")} | ${offer.remoteProfile?.label || offer.location || "Unknown location"}</p>
                </div>
                <div>
                  <strong>${offer.role}</strong>
                  <p class="asset-meta">${humanize(offer.roleFamily)}</p>
                </div>
                <div>
                  <span class="chip">${humanize(offer.status)}</span>
                  ${offer.isDuplicate ? `<span class="chip muted-chip">Duplicate</span>` : ""}
                  ${offer.autoShortlist ? `<span class="chip">Auto shortlist</span>` : ""}
                  ${renderStatusMeta(offer)}
                </div>
                <div>
                  <strong>${offer.scores.final}</strong>
                  <p class="asset-meta">ATS ${offer.scores.ats} | Human ${offer.scores.human}</p>
                  <p class="asset-meta">${offer.nextAction?.label || "Monitor offer"}</p>
                  <p class="asset-meta">Source quality ${offer.sourceQualityScore || 0} | shortlist ${offer.autoShortlistScore || 0}</p>
                </div>
                <div class="offer-actions-cell">
                  <button class="action-button secondary" data-index="${index}" data-action="toggle-preview">Preview</button>
                  <button class="action-button primary" data-index="${index}" data-action="primary">${primaryAction.label}</button>
                  ${
                    canMarkApplied(offer)
                      ? `<button class="action-button accent" data-index="${index}" data-action="applied">Applied</button>`
                      : ""
                  }
                  ${
                    offer.status === "shortlisted"
                      ? `<button class="action-button secondary" data-index="${index}" data-action="unshortlist">Remove shortlist</button>`
                      : `<button class="action-button accent" data-index="${index}" data-action="shortlist">Shortlist</button>`
                  }
                  <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open</a>
                  ${getRealOfferUrl(offer) ? `<a class="text-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Offer</a>` : ""}
                  ${
                    getApplyPageUrl(offer) && getApplyPageUrl(offer) !== getRealOfferUrl(offer)
                      ? `<a class="text-link" href="${getApplyPageUrl(offer)}" target="_blank" rel="noreferrer">Apply</a>`
                      : ""
                  }
                </div>
              </div>
              <div class="offer-detail hidden" id="offer-preview-${index}">
                <div class="detail-grid">
                  <article class="preview-card">
                    <div class="preview-head">
                      <strong>Fit summary</strong>
                      ${offer.isDuplicate && offer.canonicalOfferId !== offer.id ? `<a class="text-link" href="/dashboard/offer.html?id=${offer.canonicalOfferId}">Open canonical</a>` : ""}
                    </div>
                    <p class="asset-meta">${offer.summary || "No fit summary generated yet."}</p>
                    ${offer.remoteProfile?.reason ? `<p class="asset-meta">${offer.remoteProfile.reason}</p>` : ""}
                    <div class="chip-wrap">
                      ${(offer.keywordsRequired || []).slice(0, 6).map((keyword) => `<span class="chip">${humanize(keyword)}</span>`).join("")}
                    </div>
                  </article>
                  <article class="preview-card">
                    <div class="preview-head">
                      <strong>Fit report</strong>
                      ${offer.assets.fit_report ? `<a class="text-link" href="/${offer.paths.fit_report}">Open file</a>` : ""}
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
                  <article class="preview-card">
                    <div class="preview-head">
                      <strong>Signals</strong>
                      ${getRealOfferUrl(offer) ? `<a class="text-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Open offer</a>` : ""}
                    </div>
                    <p class="asset-meta">${offer.reviewNeeded ? "Manual review recommended before submit." : "No manual review flag detected."}</p>
                    <p class="asset-meta">${offer.applicationQuestions?.length || 0} detected question(s) | fit report ${offer.assets.fit_report ? "ready" : "missing"}</p>
                    ${offer.duplicateCount ? `<p class="asset-meta">${offer.duplicateCount} related duplicate(s) detected in this group.</p>` : ""}
                  </article>
                </div>
              </div>
            </article>
          `;
        })
        .join("")}
    `;

    table.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const offer = filtered[Number(button.dataset.index)];
        if (button.dataset.action === "toggle-preview") {
          const panel = document.getElementById(`offer-preview-${button.dataset.index}`);
          panel.classList.toggle("hidden");
          return;
        }
        if (button.dataset.action === "shortlist") {
          runAction(
            `Shortlist ${offer.company}`,
            { action: "set_status", jobId: offer.id, status: "shortlisted", note: "Shortlisted from Offers page" }
          ).catch((error) => console.error(error));
          return;
        }
        if (button.dataset.action === "applied") {
          runAction(
            `Mark ${offer.company} as applied`,
            buildMarkAppliedPayload(offer, "Submitted manually from Offers page")
          ).catch((error) => console.error(error));
          return;
        }
        if (button.dataset.action === "unshortlist") {
          runAction(
            `Remove shortlist for ${offer.company}`,
            { action: "set_status", jobId: offer.id, status: "scored", note: "Removed from shortlist on Offers page" }
          ).catch((error) => console.error(error));
          return;
        }
        if (button.dataset.action === "primary") {
          const action = primaryActionForOffer(offer);
          runAction(`${action.label} for ${offer.company}`, action.payload).catch((error) => console.error(error));
        }
      });
    });
  };

  if (!offers.length) {
    table.innerHTML = `<div class="empty-state">No offers yet. Ingest one from URL or description to populate this page.</div>`;
    return;
  }

  [searchInput, statusSelect, presetSelect, roleSelect, duplicateToggle].forEach((node) => node.addEventListener("input", render));
  [statusSelect, presetSelect, roleSelect, duplicateToggle].forEach((node) => node.addEventListener("change", render));
  render();
};

init().catch((error) => console.error(error));
