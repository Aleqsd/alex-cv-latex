import { fetchStore, humanize, postAction } from "/dashboard/shared.js";

const init = async () => {
  const store = await fetchStore();
  const overview = store.overview;
  const queueOffers = store.offers.filter((offer) => !offer.isDuplicate);

  document.getElementById("pipeline").innerHTML = overview.pipeline
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

  const kanbanStages = [
    ["discovered", "Discovered"],
    ["scored", "Scored"],
    ["shortlisted", "Shortlisted"],
    ["applied", "Applied"],
    ["follow_up_due", "Follow-up Due"],
    ["interviewing", "Interviewing"],
  ];
  document.getElementById("kanban-board").innerHTML = kanbanStages
    .map(([status, label]) => {
      const items = queueOffers
        .filter((offer) => offer.status === status)
        .sort((a, b) => (b.scores.final || 0) - (a.scores.final || 0))
        .slice(0, 8);
      return `
        <article class="kanban-column">
          <div class="preview-head">
            <strong>${label}</strong>
            <span class="chip">${items.length}</span>
          </div>
          <div class="kanban-list">
            ${
              items.length
                ? items
                    .map(
                      (offer) => `
                        <article class="kanban-card">
                          <strong>${offer.company}</strong>
                          <p class="asset-meta">${offer.role}</p>
                          <p class="asset-meta">score ${offer.scores.final} | ${offer.nextAction?.label || "Monitor offer"}</p>
                          <p><a class="inline-link" href="/dashboard/offer.html?id=${offer.id}">Open detail</a></p>
                        </article>
                      `
                    )
                    .join("")
                : `<div class="empty-state">No offers in this stage.</div>`
            }
          </div>
        </article>
      `;
    })
    .join("");

  const actionList = document.getElementById("action-list");
  const queue = store.executionQueue || [];
  actionList.innerHTML = (queue.length ? queue : store.offers.slice(0, 3).map((offer) => ({
    company: offer.company,
    role: offer.role,
    status: offer.status,
    score: offer.scores.final,
    action: offer.nextAction,
    id: offer.id,
  })))
    .map(
      (item) => `
        <article class="decision-card">
          <strong>${item.company} - ${item.role}</strong>
          <p class="decision-meta">${humanize(item.status)} | score ${item.score} | ${humanize(item.action?.kind || "monitor")}</p>
          <p>${item.action?.reason || "No next action computed yet."}</p>
          <p><strong>Command:</strong> <code>${item.action?.command || "No CLI step required."}</code></p>
          <p><a class="inline-link" href="/dashboard/offer.html?id=${item.id}">Open detail</a></p>
        </article>
      `
    )
    .join("");

  const roleBreakdown = document.getElementById("role-breakdown");
  const breakdown = Object.entries(store.roleFamilyBreakdown);
  roleBreakdown.innerHTML = (breakdown.length ? breakdown : [["no_offers", 0]])
    .map(
      ([role, count]) => `
        <div class="breakdown-row">
          <span>${humanize(role)}</span>
          <strong>${count}</strong>
        </div>
      `
    )
    .join("");

  const batchActions = document.getElementById("batch-actions");
  const batchOutput = document.getElementById("pipeline-action-output");
  const shortlistCandidates = store.executionQueue?.filter((item) => item.action?.kind === "shortlist_offer") || [];
  const batchCards = [
    {
      title: "Discover latest offers",
      body: "Pulls current jobs from enabled sources, normalizes them, and scores them for review.",
      command: "python scripts/discover_jobs.py",
      payload: { action: "discover_jobs" },
    },
    {
      title: "Promote stale applications to follow-up",
      body: "Scans applied jobs and marks them as follow_up_due once the follow-up window has elapsed.",
      command: "python scripts/mark_followups_due.py --days 7",
      payload: { action: "mark_followups_due", days: 7 },
    },
    {
      title: "Discover a limited batch",
      body: "Runs discovery with a cap so you can inspect a smaller set of new offers first.",
      command: "python scripts/discover_jobs.py --limit 25",
      payload: { action: "discover_top", limit: 25 },
    },
  ];
  if (shortlistCandidates.length) {
    batchCards.unshift({
      title: "Shortlist queue snapshot",
      body: `${shortlistCandidates.length} offer(s) are currently high-fit enough to consider shortlisting.`,
      command: "python scripts/discover_jobs.py --limit 10",
      payload: { action: "discover_top", limit: 10 },
    });
  }
  batchActions.innerHTML = batchCards
    .map(
      (item, index) => `
        <article class="decision-card">
          <strong>${item.title}</strong>
          <p>${item.body}</p>
          <p><code>${item.command}</code></p>
          <button class="action-button secondary" data-batch-index="${index}">Run now</button>
        </article>
      `
    )
    .join("");

  const runBatch = async (action) => {
    batchOutput.classList.remove("hidden", "error");
    batchOutput.textContent = `Running: ${action.title}...`;
    batchActions.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    try {
      const result = await postAction("/api/pipeline-action", action.payload);
      const stdout = result.stdout ? `\n\n${result.stdout}` : "";
      batchOutput.textContent = `${action.title} completed successfully.${stdout}`;
      window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
      batchOutput.classList.add("error");
      batchOutput.textContent = String(error.message || error);
      batchActions.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
    }
  };

  batchActions.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.batchIndex);
      runBatch(batchCards[index]).catch((error) => console.error(error));
    });
  });

  const checklist = document.getElementById("pipeline-checklist");
  const checklistItems = [
    "Run discovery regularly to keep fresh offers entering the repository.",
    "Use the Discovery and Offers pages to review new jobs, rescore them, and shortlist the strongest matches.",
    "Open the source job page from the offer detail when you need a manual decision on keep, reject, or apply.",
    "After manual submission, run the `update_status.py --status applied` command shown in the queue.",
    "Run `mark_followups_due.py` regularly so older applications surface back into the queue.",
    "Use `follow_up_due` and `recruiter_contact` statuses to keep the outbound process moving.",
  ];
  checklist.innerHTML = checklistItems.map((item) => `<li>${item}</li>`).join("");
};

init().catch((error) => console.error(error));
