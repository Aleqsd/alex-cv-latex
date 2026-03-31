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

const deriveFocusQueue = (store) => {
  const direct = [...(store.focusQueue || [])];
  if (direct.length) return direct;
  return [...(store.offers || [])]
    .filter(
      (offer) =>
        !offer.isDuplicate &&
        [
          "discovered",
          "screened",
          "scored",
          "shortlisted",
          "applied",
          "follow_up_due",
          "recruiter_contact",
          "interviewing",
        ].includes(offer.status)
    )
    .sort((left, right) => {
      return (
        Number(right?.nextAction?.priority || 0) - Number(left?.nextAction?.priority || 0) ||
        (left.status === "shortlisted" ? -1 : 0) - (right.status === "shortlisted" ? -1 : 0) ||
        Number(right?.scores?.final || 0) - Number(left?.scores?.final || 0) ||
        String(left.company || "").localeCompare(String(right.company || "")) ||
        String(left.role || "").localeCompare(String(right.role || ""))
      );
    })
    .slice(0, 18);
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
        note: "Shortlisted from Focus Queue",
      },
    };
  }
  if (offer.nextAction?.kind === "send_follow_up") {
    return {
      label: "Mark recruiter contacted",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "recruiter_contact",
        note: "Follow-up sent from Focus Queue",
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

const init = async () => {
  const store = await fetchStore();
  const offers = deriveFocusQueue(store);
  const searchInput = document.getElementById("focus-search");
  const actionSelect = document.getElementById("focus-action");
  const roleSelect = document.getElementById("focus-role-family");
  const statusSelect = document.getElementById("focus-status");
  const target = document.getElementById("focus-list");
  const output = document.getElementById("focus-action-output");
  const summary = document.getElementById("focus-summary");

  actionSelect.innerHTML = buildOptions(
    [...new Set(offers.map((offer) => offer.nextAction?.kind).filter(Boolean))],
    "next actions"
  );
  roleSelect.innerHTML = buildOptions(
    [...new Set(offers.map((offer) => offer.roleFamily).filter(Boolean))],
    "role families"
  );
  statusSelect.innerHTML = buildOptions(
    [...new Set(offers.map((offer) => offer.status).filter(Boolean))],
    "statuses"
  );

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
    const actionKind = actionSelect.value;
    const roleFamily = roleSelect.value;
    const status = statusSelect.value;
    const filtered = offers.filter((offer) => {
      if (actionKind && offer.nextAction?.kind !== actionKind) return false;
      if (roleFamily && offer.roleFamily !== roleFamily) return false;
      if (status && offer.status !== status) return false;
      return matchesSearch(offer, search);
    });

    summary.textContent = filtered.length
      ? `${filtered.length} high-priority offer(s) in focus. Use this page as the daily execution queue.`
      : "No focus offers match the current filters.";

    if (!filtered.length) {
      target.innerHTML = `<div class="empty-state">No focus offers match the current filters.</div>`;
      return;
    }

    target.innerHTML = filtered
      .map((offer, index) => {
        const primary = primaryActionForOffer(offer);
        return `
          <article class="decision-card application-card">
            <div class="preview-head">
              <strong>${offer.company} - ${offer.role}</strong>
              <div class="ready-meta">
                <span class="chip">${humanize(offer.roleFamily)}</span>
                <span class="chip">${humanize(offer.status)}</span>
                <span class="chip">${humanize(offer.nextAction?.kind || "manual_review")}</span>
                <span class="chip">score ${offer.scores.final}</span>
              </div>
            </div>
            <p class="decision-meta">${offer.location || "Unknown location"} | ${offer.nextAction?.label || "Review manually"}</p>
            <p>${offer.nextAction?.reason || offer.summary || "No reason computed yet."}</p>
            <div class="chip-wrap">
              ${(offer.keywordsRequired || []).slice(0, 8).map((keyword) => `<span class="chip">${humanize(keyword)}</span>`).join("")}
              ${offer.reviewNeeded ? `<span class="chip muted-chip">Review needed</span>` : ""}
              ${offer.followUpDueAt ? `<span class="chip">${offer.followUpOverdue ? "Follow-up overdue" : `Follow-up ${offer.followUpDueAt.slice(0, 10)}`}</span>` : ""}
            </div>
            <div class="action-bar compact-row">
              <button class="action-button primary" data-index="${index}" data-action="primary">${primary.label}</button>
              ${
                canMarkApplied(offer)
                  ? `<button class="action-button accent" data-index="${index}" data-action="applied">Mark applied</button>`
                  : ""
              }
              ${
                offer.status === "shortlisted"
                  ? `<button class="action-button secondary" data-index="${index}" data-action="unshortlist">Remove shortlist</button>`
                  : `<button class="action-button accent" data-index="${index}" data-action="shortlist">Shortlist</button>`
              }
              <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
              ${getRealOfferUrl(offer) ? `<a class="text-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Open offer</a>` : ""}
            </div>
            <div class="preview-grid compact">
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
                <p class="asset-meta">${offer.assets.fit_report ? "Fit report ready." : "Fit report missing."}</p>
                <p class="asset-meta">${offer.applicationQuestions?.length || 0} detected question(s) | ${offer.duplicateCount || 0} duplicate(s)</p>
                <p class="asset-meta">${offer.reviewNeeded ? "Manual review flagged before submit." : "No review flag currently active."}</p>
              </article>
            </div>
          </article>
        `;
      })
      .join("");

    target.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const offer = filtered[Number(button.dataset.index)];
        const action = button.dataset.action;
        if (action === "primary") {
          const primary = primaryActionForOffer(offer);
          runAction(primary.payload, `${primary.label} for ${offer.company}`).catch((error) => console.error(error));
          return;
        }
        if (action === "shortlist") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "shortlisted", note: "Shortlisted from Focus Queue" },
            `Shortlist ${offer.company}`
          ).catch((error) => console.error(error));
          return;
        }
        if (action === "applied") {
          runAction(
            buildMarkAppliedPayload(offer, "Submitted manually from Focus Queue"),
            `Mark ${offer.company} as applied`
          ).catch((error) => console.error(error));
          return;
        }
        if (action === "unshortlist") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "scored", note: "Removed from shortlist from Focus Queue" },
            `Remove shortlist for ${offer.company}`
          ).catch((error) => console.error(error));
          return;
        }
      });
    });
  };

  [searchInput, actionSelect, roleSelect, statusSelect].forEach((node) => {
    node.addEventListener("input", render);
    node.addEventListener("change", render);
  });

  render();
};

init().catch((error) => console.error(error));
