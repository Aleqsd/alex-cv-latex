import {
  fetchStore,
  getApplyPageUrl,
  getRealOfferUrl,
  humanize,
  postAction,
  renderMarkdownPreview,
  renderScoreCards,
} from "/dashboard/shared.js";

const TRACKED_STATUSES = ["applied", "follow_up_due", "recruiter_contact", "interviewing"];

const buildOptions = (values, label) => [
  `<option value="">All ${label}</option>`,
  ...values.map((value) => `<option value="${value}">${humanize(value)}</option>`),
].join("");

const nextActionKinds = (offers) =>
  [...new Set(offers.map((offer) => offer.nextAction?.kind).filter(Boolean))];

const actionButtonsForOffer = (offer) => {
  const buttons = [];
  if (offer.status === "applied") {
    buttons.push(["Mark follow-up due", "follow_up_due", "accent"]);
    buttons.push(["Mark interviewing", "interviewing", "secondary"]);
  } else if (offer.status === "follow_up_due") {
    buttons.push(["Mark follow-up sent", "recruiter_contact", "accent"]);
    buttons.push(["Mark interviewing", "interviewing", "secondary"]);
  } else if (offer.status === "recruiter_contact") {
    buttons.push(["Mark interviewing", "interviewing", "secondary"]);
    buttons.push(["Reset to applied", "applied", "secondary"]);
  } else if (offer.status === "interviewing") {
    buttons.push(["Back to recruiter contact", "recruiter_contact", "secondary"]);
  }
  buttons.push(["Archive / reject", "rejected", "danger"]);
  return buttons;
};

const init = async () => {
  const store = await fetchStore();
  const tracked = store.offers
    .filter((offer) => TRACKED_STATUSES.includes(offer.status))
    .sort((a, b) => {
      if (a.followUpOverdue !== b.followUpOverdue) return a.followUpOverdue ? -1 : 1;
      return (b.scores.final || 0) - (a.scores.final || 0);
    });

  const followUpsDue = tracked.filter((offer) => offer.status === "follow_up_due" || offer.followUpOverdue);
  const interviewing = tracked.filter((offer) => offer.status === "interviewing");
  const awaitingReply = tracked.filter((offer) => offer.status === "applied" || offer.status === "recruiter_contact");

  document.getElementById("applications-summary").textContent = tracked.length
    ? `${tracked.length} tracked application process(es): ${followUpsDue.length} follow-up item(s), ${interviewing.length} interview pipeline item(s).`
    : "No submitted applications tracked yet. Mark offers as applied after manual submission.";

  renderScoreCards(document.getElementById("application-score-grid"), {
    ats: tracked.length,
    human: awaitingReply.length,
    strategic: followUpsDue.length,
    final: interviewing.length,
  });

  document.getElementById("application-score-grid").querySelectorAll(".score-card .label")[0].textContent = "Tracked";
  document.getElementById("application-score-grid").querySelectorAll(".score-card .label")[1].textContent = "Awaiting Reply";
  document.getElementById("application-score-grid").querySelectorAll(".score-card .label")[2].textContent = "Follow-ups";
  document.getElementById("application-score-grid").querySelectorAll(".score-card .label")[3].textContent = "Interviewing";

  const searchInput = document.getElementById("applications-search");
  const statusSelect = document.getElementById("applications-status");
  const actionSelect = document.getElementById("applications-action");
  const output = document.getElementById("applications-action-output");
  const target = document.getElementById("applications-list");

  statusSelect.innerHTML = buildOptions([...new Set(tracked.map((offer) => offer.status))], "statuses");
  actionSelect.innerHTML = buildOptions(nextActionKinds(tracked), "next actions");

  if (!tracked.length) {
    target.innerHTML = `<div class="empty-state">No active applications yet. Mark an offer as applied once you submit it manually.</div>`;
    return;
  }

  const runStatusAction = async (offer, status, note, label) => {
    output.classList.remove("hidden", "error");
    output.textContent = `Running: ${label}...`;
    target.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    try {
      const result = await postAction("/api/offer-action", {
        action: "set_status",
        jobId: offer.id,
        status,
        note,
      });
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
    const status = statusSelect.value;
    const action = actionSelect.value;
    const filtered = tracked.filter((offer) => {
      if (status && offer.status !== status) return false;
      if (action && offer.nextAction?.kind !== action) return false;
      if (!search) return true;
      return [offer.company, offer.role, offer.summary, offer.location].join(" ").toLowerCase().includes(search);
    });

    if (!filtered.length) {
      target.innerHTML = `<div class="empty-state">No tracked applications match the current filters.</div>`;
      return;
    }

    target.innerHTML = filtered
      .map(
        (offer, index) => `
          <article class="decision-card application-card">
            <div class="preview-head">
              <strong>${offer.company} - ${offer.role}</strong>
              <span class="chip">${humanize(offer.status)}</span>
            </div>
            <p class="decision-meta">
              score ${offer.scores.final}
              ${typeof offer.statusAgeDays === "number" ? `| ${offer.statusAgeDays}d in status` : ""}
              ${offer.followUpDueAt ? `| follow-up ${offer.followUpOverdue ? "overdue" : offer.followUpDueAt.slice(0, 10)}` : ""}
            </p>
            <p>${offer.nextAction?.reason || "No next action recorded yet."}</p>
            <div class="ready-links">
              <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
              ${offer.assets.fit_report ? `<a class="text-link" href="/${offer.paths.fit_report}">Open fit report</a>` : ""}
              ${getRealOfferUrl(offer) ? `<a class="text-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Open offer</a>` : ""}
              ${
                getApplyPageUrl(offer) && getApplyPageUrl(offer) !== getRealOfferUrl(offer)
                  ? `<a class="text-link" href="${getApplyPageUrl(offer)}" target="_blank" rel="noreferrer">Open apply page</a>`
                  : ""
              }
            </div>
            <div class="action-bar compact-row">
              ${actionButtonsForOffer(offer)
                .map(
                  ([label, nextStatus, tone]) =>
                    `<button class="action-button ${tone}" data-index="${index}" data-status="${nextStatus}" data-label="${label}">${label}</button>`
                )
                .join("")}
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
                  <strong>Decision log</strong>
                  ${offer.assets.decision ? `<a class="text-link" href="/${offer.paths.decision}">Open file</a>` : ""}
                </div>
                ${renderMarkdownPreview(offer.assetPreview?.decision || "")}
              </article>
            </div>
          </article>
        `
      )
      .join("");

    target.querySelectorAll("button[data-status]").forEach((button) => {
      button.addEventListener("click", () => {
        const offer = filtered[Number(button.dataset.index)];
        const status = button.dataset.status;
        let note = "";
        if (status === "follow_up_due") note = "Follow-up now due";
        if (status === "recruiter_contact") note = "Follow-up sent manually";
        if (status === "interviewing") note = "Interview process active";
        if (status === "applied") note = "Moved back to applied";
        if (status === "rejected") note = "Archived from applications view";
        runStatusAction(offer, status, note, `${button.dataset.label} for ${offer.company}`).catch((error) => console.error(error));
      });
    });

  };

  [searchInput, statusSelect, actionSelect].forEach((node) => {
    node.addEventListener("input", render);
    node.addEventListener("change", render);
  });

  render();
};

init().catch((error) => console.error(error));
