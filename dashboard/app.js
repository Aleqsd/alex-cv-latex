import { fetchStore, humanize, renderScoreCards, renderAssetStatus } from "/dashboard/shared.js";

const renderPipeline = (target, stages) => {
  target.innerHTML = stages
    .map(
      (stage) => `
        <article class="pipeline-stage">
          <h3>${stage.name}</h3>
          <p class="pipeline-count">${stage.count}</p>
          <p class="pipeline-note">${stage.note}</p>
        </article>
      `
    )
    .join("");
};

const renderOpportunities = (target, offers) => {
  target.innerHTML = offers
    .map(
      (offer) => `
        <article class="opportunity-card">
          <div class="opportunity-top">
            <div>
              <p class="opportunity-company">${offer.company}</p>
              <p class="opportunity-role">${offer.role}</p>
            </div>
            <div class="score-pill">${offer.score}</div>
          </div>
          <div class="opportunity-tags">
            ${offer.tags.map((tag) => `<span class="chip">${humanize(tag)}</span>`).join("")}
          </div>
          <a class="card-link" href="/dashboard/offer.html?id=${offer.id || ""}">Open detail</a>
        </article>
      `
    )
    .join("");
};

const renderSimpleCards = (target, items) => {
  target.innerHTML = items
    .map(
      (item) => `
        <article class="decision-card">
          <strong>${item.title}</strong>
          <p class="decision-meta">${item.meta}</p>
          <p>${item.body}</p>
        </article>
      `
    )
    .join("");
};

const renderOpsCards = (target, items) => {
  target.innerHTML = items
    .map(
      (item) => `
        <article class="score-card">
          <div class="label">${item.label}</div>
          <div class="value">${item.value}</div>
          <div class="delta">${item.note}</div>
        </article>
      `
    )
    .join("");
};

const init = async () => {
  const store = await fetchStore();
  const data = store.overview;
  const enabledSources = (store.sources || []).filter((source) => source.enabled).length;
  const followUpsDue = store.offers.filter((offer) => offer.status === "follow_up_due" || offer.followUpOverdue).length;

  document.getElementById("focus-role").textContent = data.hero.role;
  document.getElementById("focus-mode").textContent = data.hero.mode;
  document.getElementById("focus-meta").textContent = data.hero.meta;
  document.getElementById("focus-progress").style.width = `${data.hero.progress}%`;

  renderScoreCards(document.getElementById("score-grid"), data.scores);
  renderOpsCards(document.getElementById("ops-grid"), [
    {
      label: "Enabled Sources",
      value: enabledSources,
      note: `${store.sources?.length || 0} configured feeds`,
    },
    {
      label: "Duplicates Collapsed",
      value: store.counts.duplicates || 0,
      note: `${store.duplicateGroups?.length || 0} duplicate group(s) need review`,
    },
    {
      label: "Auto Shortlist",
      value: store.counts.autoShortlisted || 0,
      note: `${store.counts.shortlisted || 0} manually shortlisted`,
    },
    {
      label: "Shortlisted",
      value: store.counts.shortlisted || 0,
      note: "Offers explicitly kept for closer review",
    },
    {
      label: "Follow-ups Due",
      value: followUpsDue,
      note: followUpsDue ? "Offers page needs attention" : "No stale applications right now",
    },
  ]);
  renderPipeline(document.getElementById("pipeline"), data.pipeline);

  const enrichedTopMatches = data.topMatches.map((match) => {
    const full = store.offers.find((offer) => offer.company === match.company && offer.role === match.role);
    return { ...match, id: full?.id || "" };
  });
  renderOpportunities(document.getElementById("opportunity-list"), enrichedTopMatches);

  document.getElementById("asset-list").innerHTML = data.assets
    .map((asset) => renderAssetStatus(asset.name, asset.detail, asset.status, asset.label))
    .join("");

  renderSimpleCards(document.getElementById("decision-cards"), data.decisions);
  renderSimpleCards(document.getElementById("source-ranking"), data.topSources || []);
};

init().catch((error) => console.error(error));
