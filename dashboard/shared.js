const DISPLAY_LABELS = {
  ai_tooling: "AI / Developer Tooling",
  apis: "APIs",
  aws: "AWS",
  ashby: "Ashby",
  browser: "Browser",
  backend_engineer: "Backend Engineer",
  backend_services: "Backend Services",
  ci_cd: "CI/CD",
  cloud_platform: "Cloud Platform",
  cross_functional_execution: "Cross-functional Execution",
  developer_tooling: "Developer Tooling",
  devops: "DevOps",
  founding_engineer: "Founding Engineer",
  full_stack: "Full-stack",
  gcp: "GCP",
  platform_devops_engineer: "Platform / DevOps Engineer",
  product_delivery: "Product Delivery",
  shortlist_offer: "Shortlist Offer",
  review_offer: "Review Offer",
  manual_review: "Manual Review",
  archive_or_ignore: "Archive or Ignore",
  send_follow_up: "Send Follow-up",
  interview_prep: "Interview Prep",
  watch_for_reply: "Watch For Reply",
  shortlisted: "Shortlisted",
  qa_enablement: "QA Enablement",
  release_engineering: "Release Engineering",
  scale_up: "Scale Up",
  scale_ups: "Scale Ups",
  series_a: "Series A",
  software_engineer: "Software Engineer",
  startups: "Startups",
  test_automation: "Test Automation",
  recruiter_contact: "Recruiter Contact",
  follow_up_due: "Follow-up Due",
  no_offers: "No Offers",
  manual: "Manual",
  direct: "Direct",
  review_needed: "Review Needed",
  static: "Static",
  teamtailor: "Teamtailor",
  workable: "Workable",
  greenhouse: "Greenhouse",
  lever: "Lever",
  "0_to_1": "0-to-1",
  "0-to-1 Buildout": "0-to-1 Buildout",
};

export const humanize = (value = "") => {
  const normalized = String(value).trim();
  if (!normalized) return "";
  if (DISPLAY_LABELS[normalized]) return DISPLAY_LABELS[normalized];
  return normalized
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

export const fetchStore = async () => {
  const response = await fetch("/dashboard/data/store.json", { cache: "no-store" });
  return response.json();
};

export const postAction = async (path, payload) => {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Request failed with status ${response.status}`);
  }
  return data;
};

export const fetchTextAsset = async (path) => {
  const response = await fetch(`/${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Unable to load ${path}`);
  }
  return response.text();
};

export const getRealOfferUrl = (offer = {}) =>
  offer.sourceUrl || offer.applicationUrl || offer.pageSignals?.source_page_url || offer.pageSignals?.final_url || "";

export const getApplyPageUrl = (offer = {}) =>
  offer.applicationUrl || offer.pageSignals?.final_url || offer.sourceUrl || "";

export const canMarkApplied = (offer = {}) =>
  !["applied", "follow_up_due", "recruiter_contact", "interviewing", "rejected", "archived"].includes(offer.status);

export const buildMarkAppliedPayload = (offer = {}, note = "Submitted manually") => ({
  action: "set_status",
  jobId: offer.id,
  status: "applied",
  note,
});

export const copyText = async (text) => {
  if (!navigator.clipboard?.writeText) {
    throw new Error("Clipboard API is unavailable in this browser.");
  }
  await navigator.clipboard.writeText(String(text || ""));
};

export const copyAssetText = async (path) => {
  const text = await fetchTextAsset(path);
  await copyText(text);
  return text;
};

export const escapeHtml = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

export const renderMarkdownPreview = (text = "") => {
  if (!text.trim()) {
    return `<div class="empty-state">No preview available.</div>`;
  }
  return `<pre class="artifact-preview">${escapeHtml(text)}</pre>`;
};

export const scoreTone = (value) => {
  if (value >= 85) return "Excellent alignment";
  if (value >= 75) return "Strong target";
  if (value >= 60) return "Selective fit";
  return "Needs scrutiny";
};

export const renderScoreCards = (target, scores) => {
  const items = [
    ["ATS Fit", scores.ats],
    ["Human Fit", scores.human],
    ["Strategic Fit", scores.strategic],
    ["Final Priority", scores.final],
  ];

  target.innerHTML = items
    .map(
      ([label, value]) => `
        <article class="score-card">
          <div class="label">${label}</div>
          <div class="value">${value}</div>
          <div class="delta">${scoreTone(value)}</div>
        </article>
      `
    )
    .join("");
};

export const renderAssetStatus = (name, detail, status, label, href = "") => `
  <article class="asset-card">
    <span class="asset-status ${status}"></span>
    <div>
      <strong>${href ? `<a class="inline-link" href="/${href}">${name}</a>` : name}</strong>
      <p class="asset-meta">${detail}</p>
    </div>
    <span class="chip">${label}</span>
  </article>
`;
