import { fetchStore, humanize, postAction } from "/dashboard/shared.js";

const init = async () => {
  const store = await fetchStore();
  const sources = [...(store.sources || [])].sort((a, b) => Number(b.enabled) - Number(a.enabled));
  const summary = document.getElementById("sources-summary");
  const list = document.getElementById("sources-list");
  const output = document.getElementById("sources-action-output");

  summary.textContent = sources.length
    ? `${sources.filter((source) => source.enabled).length} enabled source(s), ${store.counts.duplicates || 0} duplicate offer(s) currently collapsed from the main queue.`
    : "No sources configured yet. Add feeds to data/job_sources.yaml to pilot discovery here.";

  const runAction = async (payload, label) => {
    output.classList.remove("hidden", "error");
    output.textContent = `Running: ${label}...`;
    list.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    document.getElementById("discover-enabled").disabled = true;
    try {
      const result = await postAction("/api/source-action", payload);
      output.textContent = `${label} completed successfully.${result.stdout ? `\n\n${result.stdout}` : ""}`;
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      output.classList.add("error");
      output.textContent = String(error.message || error);
      list.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
      document.getElementById("discover-enabled").disabled = false;
    }
  };

  document.getElementById("discover-enabled").addEventListener("click", () => {
    runAction({ action: "discover_enabled" }, "Discover enabled sources").catch((error) => console.error(error));
  });

  if (!sources.length) {
    list.innerHTML = `<div class="empty-state">No source config found yet.</div>`;
    return;
  }

  list.innerHTML = sources
    .map(
      (source, index) => `
        <article class="source-card rich">
          <div class="source-head">
            <div>
              <strong>${source.company}</strong>
              <p class="asset-meta">${humanize(source.provider)} | ${source.id}</p>
            </div>
            <span class="chip ${source.enabled ? "" : "muted-chip"}">${source.enabled ? "Enabled" : "Disabled"}</span>
          </div>
          <div class="ready-meta">
            <span class="chip">${source.counts.canonical} canonical offer(s)</span>
            <span class="chip">${source.counts.duplicates} duplicate(s)</span>
            <span class="chip">${source.counts.ready} ready pack(s)</span>
            <span class="chip">Avg score ${source.averageScore}</span>
          </div>
          <p class="asset-meta">${source.notes || "No source notes recorded."}</p>
          <p class="asset-meta">${source.baseUrl || source.boardToken || "No URL/token configured."}</p>
          <p class="asset-meta">${source.latestSeenAt ? `Last seen ${source.latestSeenAt.slice(0, 10)}` : "No offer seen yet."}</p>
          <div class="action-bar compact-row">
            <button class="action-button ${source.enabled ? "secondary" : "primary"}" data-action="toggle" data-index="${index}">
              ${source.enabled ? "Disable source" : "Enable source"}
            </button>
            <button class="action-button accent" data-action="discover" data-index="${index}">
              Discover this source
            </button>
          </div>
        </article>
      `
    )
    .join("");

  list.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const source = sources[Number(button.dataset.index)];
      if (button.dataset.action === "toggle") {
        runAction(
          { action: "set_enabled", sourceId: source.id, enabled: !source.enabled },
          `${source.enabled ? "Disable" : "Enable"} ${source.company}`
        ).catch((error) => console.error(error));
      } else if (button.dataset.action === "discover") {
        runAction(
          { action: "discover_source", sourceId: source.id },
          `Discover offers from ${source.company}`
        ).catch((error) => console.error(error));
      }
    });
  });
};

init().catch((error) => console.error(error));
