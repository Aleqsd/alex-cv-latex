import { fetchStore, humanize } from "/dashboard/shared.js";

const renderChips = (target, items) => {
  target.innerHTML = items.length
    ? items.map((item) => `<span class="chip">${humanize(item)}</span>`).join("")
    : `<span class="chip">None</span>`;
};

const init = async () => {
  const store = await fetchStore();
  const profile = store.profile;

  document.getElementById("profile-title").textContent = profile.fullName;
  document.getElementById("profile-meta").textContent =
    `${profile.location} | ${profile.remotePreference} | ${profile.email}`;

  renderChips(document.getElementById("profile-roles"), profile.preferredRoleFamilies || []);
  renderChips(
    document.getElementById("profile-preferences"),
    [...(profile.preferredWorkModes || []), ...(profile.preferredCompanyStages || [])]
  );
  renderChips(
    document.getElementById("profile-biases"),
    [
      ...((profile.strategicBiases?.favor || []).map((item) => `Favor: ${item}`)),
      ...((profile.strategicBiases?.avoid || []).map((item) => `Avoid: ${item}`)),
    ]
  );
  renderChips(document.getElementById("profile-variants"), profile.variantPriority || []);

  const skillLabels = {
    languages: "Languages",
    frameworks: "Frameworks",
    cloud_platform: "Cloud / Platform",
    ai_tooling: "AI / Developer Tooling",
    practices: "Practices",
  };

  document.getElementById("profile-skills").innerHTML = Object.entries(skillLabels)
    .map(([key, label]) => {
      const values = profile.skills?.[key] || [];
      return `
        <article class="skill-panel">
          <p class="panel-label">${label}</p>
          <div class="chip-wrap">
            ${values.map((value) => `<span class="chip">${value}</span>`).join("")}
          </div>
        </article>
      `;
    })
    .join("");

  document.getElementById("profile-achievements").innerHTML = (profile.achievements || [])
    .map(
      (achievement) => `
        <article class="achievement-card">
          <p class="achievement-value">${achievement.value}</p>
          <p class="achievement-label">${achievement.label}</p>
        </article>
      `
    )
    .join("");

  document.getElementById("profile-experience").innerHTML = (profile.experience || [])
    .map(
      (item) => `
        <article class="experience-card">
          <div class="experience-top">
            <div>
              <strong>${item.company}</strong>
              <p class="asset-meta">${item.title}</p>
            </div>
            <span class="chip">${item.dates}</span>
          </div>
          <div class="chip-wrap">
            ${(item.themes || []).map((theme) => `<span class="chip">${humanize(theme)}</span>`).join("")}
          </div>
        </article>
      `
    )
    .join("");
};

init().catch((error) => console.error(error));
