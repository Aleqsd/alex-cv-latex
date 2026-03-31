import { fetchStore, humanize, postAction } from "/dashboard/shared.js";

const buildOptions = (values, label) => [
  `<option value="">All ${label}</option>`,
  ...values.map((value) => `<option value="${value}">${humanize(value)}</option>`),
].join("");

const init = async () => {
  const store = await fetchStore();
  const groups = [...(store.duplicateGroups || [])];
  const searchInput = document.getElementById("duplicates-search");
  const roleSelect = document.getElementById("duplicates-role-family");
  const minSizeSelect = document.getElementById("duplicates-min-size");
  const target = document.getElementById("duplicates-list");
  const output = document.getElementById("duplicates-action-output");

  roleSelect.innerHTML = buildOptions([...new Set(groups.map((group) => group.roleFamily).filter(Boolean))], "role families");

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
    const minSize = Number(minSizeSelect.value || 2);
    const filtered = groups.filter((group) => {
      if (roleFamily && group.roleFamily !== roleFamily) return false;
      if ((group.offers?.length || 0) < minSize) return false;
      if (!search) return true;
      return [group.company, group.role, ...(group.offers || []).map((offer) => `${offer.location} ${offer.role}`)]
        .join(" ")
        .toLowerCase()
        .includes(search);
    });

    document.getElementById("duplicates-summary").textContent = filtered.length
      ? `${filtered.length} duplicate group(s) visible. Each group shows one canonical offer and its related reposts.`
      : "No duplicate groups match the current filters.";

    if (!filtered.length) {
      target.innerHTML = `<div class="empty-state">No duplicate groups match the current filters.</div>`;
      return;
    }

    target.innerHTML = filtered
      .map(
        (group, groupIndex) => `
          <article class="decision-card">
            <div class="preview-head">
              <strong>${group.company} - ${group.role}</strong>
              <div class="ready-meta">
                <span class="chip">${group.offers.length} related offers</span>
                <span class="chip">${humanize(group.roleFamily)}</span>
              </div>
            </div>
            <p class="decision-meta">Canonical offer: <a class="inline-link" href="/dashboard/offer.html?id=${group.canonical.id}">${group.canonical.role}</a> | score ${group.canonical.scores.final}</p>
            <div class="action-bar compact-row">
              <button class="action-button accent" data-group-index="${groupIndex}" data-action="shortlist-canonical">Shortlist canonical</button>
              <button class="action-button primary" data-group-index="${groupIndex}" data-action="refresh-canonical">Inspect canonical</button>
              <a class="text-link" href="/dashboard/offer.html?id=${group.canonical.id}">Open canonical</a>
            </div>
            <div class="decision-cards nestedless">
              ${group.offers
                .map(
                  (offer, offerIndex) => `
                    <article class="source-card rich">
                      <div class="source-head">
                        <div>
                          <strong>${offer.role}</strong>
                          <p class="asset-meta">${offer.location || "Unknown location"} | ${humanize(offer.status)} | score ${offer.scores.final}</p>
                        </div>
                        <span class="chip ${offer.id === group.canonicalOfferId ? "" : "muted-chip"}">${offer.id === group.canonicalOfferId ? "Canonical" : "Duplicate"}</span>
                      </div>
                      <div class="ready-links">
                        <a class="text-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a>
                        ${offer.applicationUrl ? `<a class="text-link" href="${offer.applicationUrl}" target="_blank" rel="noreferrer">Open source</a>` : ""}
                      </div>
                      <div class="action-bar compact-row">
                        ${
                          offer.id !== group.canonicalOfferId
                            ? `<button class="action-button danger" data-group-index="${groupIndex}" data-offer-index="${offerIndex}" data-action="reject-duplicate">Reject duplicate</button>`
                            : `<span class="chip">Canonical offer</span>`
                        }
                        ${
                          offer.status !== "shortlisted"
                            ? `<button class="action-button secondary" data-group-index="${groupIndex}" data-offer-index="${offerIndex}" data-action="shortlist-offer">Shortlist</button>`
                            : `<button class="action-button secondary" data-group-index="${groupIndex}" data-offer-index="${offerIndex}" data-action="unshortlist-offer">Remove shortlist</button>`
                        }
                      </div>
                    </article>
                  `
                )
                .join("")}
            </div>
          </article>
        `
      )
      .join("");

    target.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const group = filtered[Number(button.dataset.groupIndex)];
        const offer = button.dataset.offerIndex !== undefined
          ? group.offers[Number(button.dataset.offerIndex)]
          : group.canonical;
        const action = button.dataset.action;
        if (action === "shortlist-canonical") {
          runAction(
            { action: "set_status", jobId: group.canonical.id, status: "shortlisted", note: "Canonical offer shortlisted from duplicate review" },
            `Shortlist canonical ${group.company}`
          ).catch((error) => console.error(error));
        } else if (action === "refresh-canonical") {
          runAction(
            { action: "refresh_apply", jobId: group.canonical.id, browser: "auto" },
            `Inspect canonical ${group.company}`
          ).catch((error) => console.error(error));
        } else if (action === "reject-duplicate") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "rejected", note: "Rejected as duplicate from duplicate review" },
            `Reject duplicate ${offer.company || group.company}`
          ).catch((error) => console.error(error));
        } else if (action === "shortlist-offer") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "shortlisted", note: "Shortlisted from duplicate review" },
            `Shortlist ${offer.company || group.company}`
          ).catch((error) => console.error(error));
        } else if (action === "unshortlist-offer") {
          runAction(
            { action: "set_status", jobId: offer.id, status: "scored", note: "Removed from shortlist during duplicate review" },
            `Remove shortlist for ${offer.company || group.company}`
          ).catch((error) => console.error(error));
        }
      });
    });
  };

  [searchInput, roleSelect, minSizeSelect].forEach((node) => {
    node.addEventListener("input", render);
    node.addEventListener("change", render);
  });
  render();
};

init().catch((error) => console.error(error));
