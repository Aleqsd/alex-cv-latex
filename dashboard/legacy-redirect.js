const redirects = {
  "focus.html": "/dashboard/offers.html",
  "discovery.html": "/dashboard/offers.html",
  "shortlist.html": "/dashboard/offers.html",
  "duplicates.html": "/dashboard/offers.html",
  "ready.html": "/dashboard/offers.html",
  "applications.html": "/dashboard/offers.html",
  "sources.html": "/dashboard/pipeline.html",
};

const fileName = window.location.pathname.split("/").pop() || "";
const target = redirects[fileName] || "/dashboard/";
const targetLabel = target.endsWith("/pipeline.html") ? "Pipeline" : target.endsWith("/offers.html") ? "Offers" : "Overview";

document.addEventListener("DOMContentLoaded", () => {
  const link = document.getElementById("redirect-target");
  if (link) {
    link.href = target;
    link.textContent = targetLabel;
  }
  window.setTimeout(() => {
    window.location.replace(target);
  }, 250);
});
