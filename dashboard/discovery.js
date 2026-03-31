import { fetchStore, humanize, postAction } from "/dashboard/shared.js";

const renderBreakdown = (target, data, emptyLabel) => {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    target.innerHTML = `<div class="empty-state">${emptyLabel}</div>`;
    return;
  }
  target.innerHTML = entries
    .map(
      ([label, count]) => `
        <article class="source-card">
          <strong>${humanize(label)}</strong>
          <p class="asset-meta">${count} tracked offer(s)</p>
        </article>
      `
    )
    .join("");
};

const init = async () => {
  const store = await fetchStore();
  const allDiscoveredOffers = store.offers
    .filter((offer) => offer.source === "auto_discovery" || offer.discoverySource || offer.sourceProvider)
    .sort((a, b) => String(b.lastSeenAt || b.updatedAt).localeCompare(String(a.lastSeenAt || a.updatedAt)));
  const duplicateToggle = document.getElementById("discovery-duplicates");

  document.getElementById("discovery-summary").textContent = allDiscoveredOffers.length
    ? `${allDiscoveredOffers.length} discovered offer(s), ${store.counts.discovered || 0} canonical offer(s) still untriaged.`
    : "No automatically discovered offers yet. Run discovery to populate this page.";

  renderBreakdown(document.getElementById("provider-grid"), store.providerBreakdown, "No providers seen yet.");
  renderBreakdown(document.getElementById("source-grid"), store.sourceBreakdown, "No configured discovery source has produced offers yet.");

  const freshList = document.getElementById("fresh-list");
  const output = document.getElementById("discovery-action-output");
  if (!allDiscoveredOffers.length) {
    freshList.innerHTML = `<div class="empty-state">No discovery output yet.</div>`;
    return;
  }

  const render = () => {
    const showDuplicates = duplicateToggle.checked;
    const discoveredOffers = allDiscoveredOffers.filter((offer) => showDuplicates || !offer.isDuplicate);
    const hiddenDuplicates = allDiscoveredOffers.filter((offer) => offer.isDuplicate).length;
    document.getElementById("discovery-summary").textContent = discoveredOffers.length
      ? `${discoveredOffers.length} discovered offer(s) visible, ${showDuplicates ? "including duplicates" : `${hiddenDuplicates} duplicate(s) hidden`}.`
      : "No discovery offers match the current view.";

    freshList.innerHTML = discoveredOffers.slice(0, 12)
      .map(
        (offer) => `
          <article class="ready-card">
            <div class="ready-top">
              <div>
                <p class="opportunity-company">${offer.company}</p>
                <p class="opportunity-role">${offer.role}</p>
              </div>
              <div class="score-pill">${offer.scores.final}</div>
            </div>
            <div class="ready-meta">
              <span class="chip">${humanize(offer.sourceProvider || offer.source || "manual")}</span>
              <span class="chip">${humanize(offer.discoverySource || "direct")}</span>
              <span class="chip">${humanize(offer.status)}</span>
              <span class="chip">${offer.location || "Unknown location"}</span>
              ${offer.isDuplicate ? `<span class="chip muted-chip">Duplicate</span>` : ""}
            </div>
            <div class="ready-links">
              <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
              ${offer.applicationUrl ? `<a class="text-link" href="${offer.applicationUrl}" target="_blank" rel="noreferrer">Open source</a>` : ""}
              ${offer.assets.fit_report ? `<a class="text-link" href="/${offer.paths.fit_report}">Open fit report</a>` : ""}
            </div>
            <div class="action-bar compact-row">
              ${
                offer.status === "shortlisted"
                  ? `<button class="action-button secondary" data-index="${offer.id}" data-action="unshortlist">Remove shortlist</button>`
                  : `<button class="action-button accent" data-index="${offer.id}" data-action="shortlist">Shortlist</button>`
              }
              <button class="action-button primary" data-index="${offer.id}" data-action="rescore">Rescore</button>
            </div>
          </article>
        `
      )
      .join("");

    freshList.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const offer = discoveredOffers.find((item) => item.id === button.dataset.index);
        if (!offer) return;
        output.classList.remove("hidden", "error");
        output.textContent = `Running: ${button.dataset.action} for ${offer.company}...`;
        freshList.querySelectorAll("button").forEach((node) => {
          node.disabled = true;
        });
        try {
          if (button.dataset.action === "shortlist") {
            await postAction("/api/offer-action", {
              action: "set_status",
              jobId: offer.id,
              status: "shortlisted",
              note: "Shortlisted from Discovery page",
            });
          } else if (button.dataset.action === "unshortlist") {
            await postAction("/api/offer-action", {
              action: "set_status",
              jobId: offer.id,
              status: "scored",
              note: "Removed from shortlist on Discovery page",
            });
          } else {
            await postAction("/api/offer-action", {
              action: "score_offer",
              jobId: offer.id,
            });
          }
          output.textContent = `Action completed for ${offer.company}.`;
          window.setTimeout(() => window.location.reload(), 700);
        } catch (error) {
          output.classList.add("error");
          output.textContent = String(error.message || error);
          freshList.querySelectorAll("button").forEach((node) => {
            node.disabled = false;
          });
        }
      });
    });
  };

  duplicateToggle.addEventListener("input", render);
  duplicateToggle.addEventListener("change", render);
  render();
};

init().catch((error) => console.error(error));
