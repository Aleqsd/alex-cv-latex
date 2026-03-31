import {
  buildMarkAppliedPayload,
  canMarkApplied,
  copyAssetText,
  fetchStore,
  fetchTextAsset,
  getApplyPageUrl,
  getRealOfferUrl,
  humanize,
  postAction,
  renderAssetStatus,
  renderMarkdownPreview,
  renderScoreCards,
} from "/dashboard/shared.js";

const params = new URLSearchParams(window.location.search);
const offerId = params.get("id");

const sourceLinkMarkup = (offer, classes = "text-link") => {
  const href = getRealOfferUrl(offer);
  if (!href) return "";
  return `<a class="${classes}" href="${href}" target="_blank" rel="noreferrer">Open real offer</a>`;
};

const renderList = (target, items) => {
  target.innerHTML = items.length
    ? items.map((item) => `<li>${item}</li>`).join("")
    : `<li>No entries</li>`;
};

const renderArtifactPreviews = async (offer) => {
  const target = document.getElementById("detail-markdown-previews");
  const cards = [
    ["Fit report", offer.paths.fit_report, offer.assetPreview?.fit_report || ""],
    ["Research", offer.paths.research, offer.assetPreview?.research || ""],
    ["Decision log", offer.paths.decision, offer.assetPreview?.decision || ""],
  ];

  const rendered = await Promise.all(
    cards.map(async ([label, path, fallback]) => {
      let text = fallback;
      if (path) {
        try {
          text = await fetchTextAsset(path);
        } catch {
          text = fallback;
        }
      }
      return `
        <article class="preview-card">
          <div class="preview-head">
            <strong>${label}</strong>
            <div class="preview-actions">
              <button class="action-button secondary small" data-copy-path="${path}" data-copy-label="${label}">Copy</button>
              <a class="text-link" href="/${path}">Open file</a>
            </div>
          </div>
          ${renderMarkdownPreview(text)}
        </article>
      `;
    })
  );
  target.innerHTML = rendered.join("");

  const pdfTarget = document.getElementById("detail-pdf-preview");
  const realOfferUrl = getRealOfferUrl(offer);
  const applyPageUrl = getApplyPageUrl(offer);
  pdfTarget.innerHTML = `
    <div class="empty-state">Tailored CV generation has been removed from this workflow.</div>
    <p class="asset-meta">
      ${realOfferUrl ? `<a class="text-link" href="${realOfferUrl}" target="_blank" rel="noreferrer">Open real offer</a>` : "No source URL captured for this offer."}
      ${
        applyPageUrl && applyPageUrl !== realOfferUrl
          ? ` | <a class="text-link" href="${applyPageUrl}" target="_blank" rel="noreferrer">Open apply page</a>`
          : ""
      }
    </p>
  `;
};

const renderDuplicates = (offer, store) => {
  const target = document.getElementById("detail-duplicates");
  const related = (offer.duplicateOfferIds || [])
    .map((id) => store.offers.find((item) => item.id === id))
    .filter(Boolean);

  if (!related.length || related.length === 1) {
    target.innerHTML = `<div class="empty-state">No related duplicates or reposts detected for this offer.</div>`;
    return;
  }

  const canonical = store.offers.find((item) => item.id === offer.canonicalOfferId);
  const intro = offer.isDuplicate && canonical
    ? `<article class="decision-card"><strong>This offer is a duplicate view</strong><p class="decision-meta">Canonical offer: <a class="inline-link" href="/dashboard/offer.html?id=${canonical.id}">${canonical.company} - ${canonical.role}</a></p><p>Use the canonical entry for queue decisions unless this duplicate has a better apply surface.</p></article>`
    : "";

  target.innerHTML = intro + related
    .map(
      (item) => `
        <article class="decision-card">
          <strong>${item.company} - ${item.role}</strong>
          <p class="decision-meta">${humanize(item.status)} | ${item.location || "Unknown location"} | score ${item.scores.final}</p>
          <p>${item.id === offer.id ? "Current offer entry." : (item.isDuplicate ? "Detected as related duplicate or repost." : "Canonical offer in this duplicate group.")}</p>
          <p><a class="inline-link" href="/dashboard/offer.html?id=${item.id}">Open related offer</a></p>
        </article>
      `
    )
    .join("");
};

const buildOfferActions = (offer) => {
  const realOfferUrl = getRealOfferUrl(offer);
  const applyPageUrl = getApplyPageUrl(offer);
  const actions = [
    ...(realOfferUrl
      ? [
          {
            label: "Open real offer",
            type: "link",
            href: realOfferUrl,
            tone: "primary",
          },
        ]
      : []),
    ...(applyPageUrl && applyPageUrl !== realOfferUrl
      ? [
          {
            label: "Open apply page",
            type: "link",
            href: applyPageUrl,
            tone: "secondary",
          },
        ]
      : []),
    ...(canMarkApplied(offer)
      ? [
          {
            label: "Mark applied",
            type: "offer",
            payload: buildMarkAppliedPayload(offer, "Submitted manually from offer detail"),
            tone: "accent",
          },
        ]
      : []),
    {
      label: "Refresh apply page",
      type: "offer",
      payload: { action: "refresh_apply", jobId: offer.id, browser: "auto" },
      tone: "secondary",
    },
    {
      label: "Rescore offer",
      type: "offer",
      payload: { action: "score_offer", jobId: offer.id },
      tone: "secondary",
    },
  ];

  if (offer.status !== "rejected" && !canMarkApplied(offer)) {
    actions.unshift({
      label: offer.status === "shortlisted" ? "Refresh source" : "Rescore offer",
      type: "offer",
      payload: offer.status === "shortlisted"
        ? { action: "refresh_apply", jobId: offer.id, browser: "auto" }
        : { action: "score_offer", jobId: offer.id },
      tone: "primary",
    });
  }

  if (offer.status === "shortlisted") {
    actions.push({
      label: "Remove shortlist",
      type: "offer",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "scored",
        note: "Removed from shortlist from detail page",
      },
      tone: "secondary",
    });
  } else if (["discovered", "screened", "scored"].includes(offer.status)) {
    actions.push({
      label: "Shortlist offer",
      type: "offer",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "shortlisted",
        note: "Shortlisted from detail page",
      },
      tone: "accent",
    });
  }

  if (offer.status === "applied" || offer.status === "follow_up_due") {
    actions.push({
      label: "Mark follow-up sent",
      type: "offer",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "recruiter_contact",
        note: "Follow-up sent manually",
      },
      tone: "accent",
    });
  }

  if (offer.status !== "interviewing" && offer.status !== "rejected") {
    actions.push({
      label: "Mark interviewing",
      type: "offer",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "interviewing",
        note: "Interview process started",
      },
      tone: "secondary",
    });
  }

  if (offer.status !== "rejected") {
    actions.push({
      label: "Archive / reject",
      type: "offer",
      payload: {
        action: "set_status",
        jobId: offer.id,
        status: "rejected",
        note: "Rejected or intentionally skipped",
      },
      tone: "danger",
    });
  }

  return actions;
};

const wireActionButtons = (offer) => {
  const target = document.getElementById("detail-actions");
  const output = document.getElementById("detail-action-output");
  const actions = buildOfferActions(offer);
  target.innerHTML = actions
    .map(
      (action, index) => `
        ${
          action.type === "link"
            ? `<a class="action-button ${action.tone}" href="${action.href}" target="_blank" rel="noreferrer">${action.label}</a>`
            : `<button class="action-button ${action.tone}" data-action-index="${index}">${action.label}</button>`
        }
      `
    )
    .join("");

  const runAction = async (action) => {
    output.classList.remove("hidden", "error");
    output.textContent = `Running: ${action.label}...`;
    target.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    try {
      const path = action.type === "pipeline" ? "/api/pipeline-action" : "/api/offer-action";
      const result = await postAction(path, action.payload);
      const stdout = result.stdout ? `\n\n${result.stdout}` : "";
      output.textContent = `${action.label} completed successfully.${stdout}`;
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      output.classList.add("error");
      output.textContent = String(error.message || error);
      target.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
    }
  };

  target.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.actionIndex);
      runAction(actions[index]).catch((error) => console.error(error));
    });
  });
};

const wireCopyButtons = () => {
  const output = document.getElementById("detail-action-output");
  document.querySelectorAll("button[data-copy-path]").forEach((button) => {
    button.addEventListener("click", () => {
      output.classList.remove("hidden", "error");
      output.textContent = `Copying ${button.dataset.copyLabel || "artifact"}...`;
      copyAssetText(button.dataset.copyPath)
        .then(() => {
          output.textContent = `${button.dataset.copyLabel || "Artifact"} copied to clipboard.`;
        })
        .catch((error) => {
          output.classList.add("error");
          output.textContent = String(error.message || error);
        });
    });
  });
};

const init = async () => {
  const store = await fetchStore();
  const offer = store.offers.find((item) => item.id === offerId);

  if (!offer) {
    document.getElementById("detail-title").textContent = "Offer not found";
    document.getElementById("detail-meta").textContent = "Check the query string or ingest the offer first.";
    return;
  }

  document.getElementById("detail-title").textContent = `${offer.company} - ${offer.role}`;
  document.getElementById("detail-meta").textContent = `${humanize(offer.roleFamily)} | ${humanize(offer.status)} | ${offer.location || "Unknown location"} | ${offer.remotePolicy || "Unknown remote policy"}`;
  document.getElementById("detail-source-links").innerHTML = [
    sourceLinkMarkup(offer, "action-button secondary"),
    getApplyPageUrl(offer) && getApplyPageUrl(offer) !== getRealOfferUrl(offer)
      ? `<a class="action-button secondary" href="${getApplyPageUrl(offer)}" target="_blank" rel="noreferrer">Open apply page</a>`
      : "",
  ]
    .filter(Boolean)
    .join("");
  document.getElementById("detail-next-action").innerHTML = `
    <article class="decision-card">
      <strong>${offer.nextAction?.label || "Review manually"}</strong>
      <p class="decision-meta">${humanize(offer.status)} | score ${offer.scores.final}</p>
      <p>${offer.nextAction?.reason || "No next action computed yet."}</p>
      ${
        offer.rawStatus && offer.rawStatus !== offer.status
          ? `<p class="decision-meta">Stored status: ${humanize(offer.rawStatus)}. Display status was adjusted because the current artifact set is incomplete.</p>`
          : ""
      }
      ${
        offer.nextAction?.command
          ? `<p><strong>CLI fallback:</strong> <code>${offer.nextAction.command}</code></p>`
          : ""
      }
      ${sourceLinkMarkup(offer, "inline-link")}
    </article>
  `;
  wireActionButtons(offer);
  renderDuplicates(offer, store);

  renderScoreCards(document.getElementById("detail-scores"), offer.scores);

  document.getElementById("detail-required").innerHTML = (offer.keywordsRequired.length ? offer.keywordsRequired : ["No keywords extracted"])
    .map((keyword) => `<span class="chip">${humanize(keyword)}</span>`)
    .join("");

  document.getElementById("detail-evidence").innerHTML = Object.entries(offer.evidenceQuality || {})
    .map(([key, value]) => `<div class="breakdown-row"><span>${humanize(key)}</span><strong>${value}</strong></div>`)
    .join("");

  renderList(document.getElementById("detail-strengths"), offer.strengths || []);
  renderList(document.getElementById("detail-risks"), offer.risks || []);

  document.getElementById("detail-description").textContent = offer.description || "No description snapshot available.";

  document.getElementById("detail-application-meta").innerHTML = [
    ["Real offer", getRealOfferUrl(offer) ? `<a class="inline-link" href="${getRealOfferUrl(offer)}" target="_blank" rel="noreferrer">Open real offer</a>` : "Not captured"],
    ["Apply page", getApplyPageUrl(offer) ? `<a class="inline-link" href="${getApplyPageUrl(offer)}" target="_blank" rel="noreferrer">Open apply page</a>` : "Not captured"],
    ["Platform", humanize(offer.applicationPlatform || "custom")],
    ["Inspection", humanize(offer.pageSignals?.inspection_mode || "static")],
    ["Clicked action", offer.pageSignals?.clicked_apply_action || "None"],
    ["Detected questions", String(offer.applicationQuestions?.length || 0)],
    ["Review needed", offer.reviewNeeded ? "Yes" : "No"],
    ["Status age", typeof offer.statusAgeDays === "number" ? `${offer.statusAgeDays} day(s)` : "Unknown"],
    ["Follow-up due", offer.followUpDueAt ? offer.followUpDueAt.slice(0, 10) : "Not scheduled"],
    ["Next action", offer.nextAction?.label || "Monitor offer"],
    ["Fit report", offer.assets.fit_report ? "Ready" : "Missing"],
  ]
    .map(([label, value]) => `<div class="breakdown-row"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");

  document.getElementById("detail-questions").innerHTML = (offer.applicationQuestions?.length ? offer.applicationQuestions : [{ prompt: "No explicit form questions detected on the source page.", kind: "review", required: false }])
    .map(
      (question, index) => `
        <article class="decision-card">
          <strong>${index + 1}. ${question.prompt}</strong>
          <p class="decision-meta">${humanize(question.kind || "unknown")} | ${question.required ? "required" : "optional"}</p>
          <p>Review the live source page before deciding how to answer this field.</p>
        </article>
      `
    )
    .join("");

  if (offer.reviewReasons?.length) {
    document.getElementById("detail-questions").insertAdjacentHTML(
      "afterbegin",
      `
        <article class="decision-card">
          <strong>Manual review recommended</strong>
          <p class="decision-meta">${offer.reviewReasons.join(" ")}</p>
          <p>Open the source page before submitting and verify the remaining compliance or demographic fields.</p>
        </article>
      `
    );
  }

  if (offer.nextAction?.command) {
    document.getElementById("detail-application-meta").insertAdjacentHTML(
      "beforeend",
      `<div class="breakdown-row"><span>CLI</span><strong><code>${offer.nextAction.command}</code></strong></div>`
    );
  }

  const assets = [
    ["Fit report", "Scoring breakdown and rationale", offer.assets.fit_report, "fit_report"],
    ["Research", "Company or offer notes", offer.assets.research, "research"],
    ["Decision log", "Why to keep, skip, or apply", offer.assets.decision, "decision"],
    ["Raw snapshot", "Saved source text for the offer", offer.assets.raw, "raw"],
  ];

  document.getElementById("detail-assets").innerHTML = assets
    .map(([name, detail, exists, key]) =>
      renderAssetStatus(
        name,
        detail,
        exists ? "done" : "pending",
        exists ? "Ready" : "Draft",
        offer.paths[key]
      )
    )
    .join("");

  await renderArtifactPreviews(offer);
  wireCopyButtons();
};

init().catch((error) => console.error(error));
