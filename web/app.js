/**
 * LinkedIn Profile Viewer — static UI for the FastAPI backend.
 *
 * API base resolution (first match wins):
 *   1. ?api= query param (also saved to localStorage)
 *   2. localStorage key "linkedin_profile_api_base"
 *   3. DEFAULT_API_BASE below
 *
 * Local: open index.html?api=http://localhost:8000
 */

const DEFAULT_API_BASE = "https://linkedin-profile-api-bsa2.onrender.com";
const STORAGE_KEY = "linkedin_profile_api_base";

const MONTHS = [
  "",
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const ERROR_MESSAGES = {
  invalid_url: "That doesn’t look like a valid LinkedIn profile URL.",
  unauthorized: "Session cookies expired. Update LI_AT / JSESSIONID on the API server.",
  forbidden: "LinkedIn denied access for this request.",
  not_found: "No LinkedIn profile found for that URL.",
  rate_limit_exceeded: "Rate limit hit. Wait a moment and try again.",
  upstream_error: "Upstream LinkedIn request failed. Try again shortly.",
};

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("api");
  if (fromQuery) {
    const cleaned = fromQuery.replace(/\/$/, "");
    try {
      localStorage.setItem(STORAGE_KEY, cleaned);
    } catch {
      /* ignore quota / private mode */
    }
    return cleaned;
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored.replace(/\/$/, "");
  } catch {
    /* ignore */
  }
  return DEFAULT_API_BASE.replace(/\/$/, "");
}

const API_BASE = resolveApiBase();

const els = {
  form: document.getElementById("search-form"),
  input: document.getElementById("url-input"),
  submitBtn: document.getElementById("submit-btn"),
  btnLabel: document.getElementById("btn-label"),
  btnSpinner: document.getElementById("btn-spinner"),
  apiHint: document.getElementById("api-hint"),
  errorBanner: document.getElementById("error-banner"),
  result: document.getElementById("result"),
  cover: document.getElementById("cover"),
  avatar: document.getElementById("avatar"),
  fullName: document.getElementById("full-name"),
  headline: document.getElementById("headline"),
  location: document.getElementById("location"),
  profileLink: document.getElementById("profile-link"),
  sectionAbout: document.getElementById("section-about"),
  summary: document.getElementById("summary"),
  summaryToggle: document.getElementById("summary-toggle"),
  sectionExperience: document.getElementById("section-experience"),
  positions: document.getElementById("positions"),
  sectionEducation: document.getElementById("section-education"),
  educations: document.getElementById("educations"),
  sectionSkills: document.getElementById("section-skills"),
  skills: document.getElementById("skills"),
  sectionCerts: document.getElementById("section-certs"),
  certifications: document.getElementById("certifications"),
  sectionLanguages: document.getElementById("section-languages"),
  languages: document.getElementById("languages"),
  sectionMedia: document.getElementById("section-media"),
  treasury: document.getElementById("treasury"),
  fetchedAt: document.getElementById("fetched-at"),
};

els.apiHint.textContent = `API: ${API_BASE}`;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatMonthYear(month, year) {
  if (!year) return null;
  if (month && month >= 1 && month <= 12) return `${MONTHS[month]} ${year}`;
  return String(year);
}

function formatDateRange(range) {
  if (!range) return "";
  const start = formatMonthYear(range.start_month, range.start_year);
  if (!start) return "";
  if (range.is_current) return `${start} – Present`;
  const end = formatMonthYear(range.end_month, range.end_year);
  return end ? `${start} – ${end}` : start;
}

function initials(first, last) {
  const a = (first || "").trim().charAt(0);
  const b = (last || "").trim().charAt(0);
  const out = `${a}${b}`.toUpperCase();
  return out || "?";
}

function setLoading(loading) {
  els.submitBtn.disabled = loading;
  els.btnLabel.textContent = loading ? "Fetching…" : "Fetch profile";
  els.btnSpinner.classList.toggle("hidden", !loading);
}

function showError(message) {
  els.errorBanner.textContent = message;
  els.errorBanner.classList.remove("hidden");
}

function hideError() {
  els.errorBanner.classList.add("hidden");
  els.errorBanner.textContent = "";
}

function friendlyError(status, body) {
  if (body && body.error && ERROR_MESSAGES[body.error]) {
    return ERROR_MESSAGES[body.error];
  }
  if (body && body.detail) return body.detail;
  if (status === 400) return ERROR_MESSAGES.invalid_url;
  if (status === 401 || status === 403) return ERROR_MESSAGES.unauthorized;
  if (status === 404) return ERROR_MESSAGES.not_found;
  if (status === 429) return ERROR_MESSAGES.rate_limit_exceeded;
  if (status >= 500) return ERROR_MESSAGES.upstream_error;
  return `Request failed (${status}).`;
}

function toggleSection(el, show) {
  el.classList.toggle("hidden", !show);
}

function renderHeader(profile) {
  const name = [profile.first_name, profile.last_name].filter(Boolean).join(" ") || "Unknown";
  els.fullName.textContent = name;
  els.headline.textContent = profile.headline || "";

  if (profile.cover_picture_url) {
    els.cover.style.backgroundImage = `url("${profile.cover_picture_url}")`;
  } else {
    els.cover.style.backgroundImage = "";
  }

  els.avatar.innerHTML = "";
  if (profile.profile_picture_url) {
    const img = document.createElement("img");
    img.src = profile.profile_picture_url;
    img.alt = name;
    img.className = "h-full w-full object-cover";
    img.onerror = () => {
      els.avatar.textContent = initials(profile.first_name, profile.last_name);
    };
    els.avatar.appendChild(img);
  } else {
    els.avatar.textContent = initials(profile.first_name, profile.last_name);
  }

  const loc = profile.location && profile.location.display;
  if (loc) {
    els.location.textContent = loc;
    els.location.classList.remove("hidden");
  } else {
    els.location.classList.add("hidden");
  }

  if (profile.profile_url) {
    els.profileLink.href = profile.profile_url;
    els.profileLink.classList.remove("hidden");
  } else {
    els.profileLink.classList.add("hidden");
  }
}

function renderAbout(summary) {
  if (!summary || !summary.trim()) {
    toggleSection(els.sectionAbout, false);
    return;
  }

  els.summary.textContent = summary;
  els.summary.classList.add("summary-collapsed");
  toggleSection(els.sectionAbout, true);

  // Defer clamp check until layout
  requestAnimationFrame(() => {
    const needsToggle = els.summary.scrollHeight > els.summary.clientHeight + 4;
    els.summaryToggle.classList.toggle("hidden", !needsToggle);
    els.summaryToggle.textContent = "Show more";
    els.summaryToggle.onclick = () => {
      const collapsed = els.summary.classList.toggle("summary-collapsed");
      els.summaryToggle.textContent = collapsed ? "Show more" : "Show less";
    };
  });
}

function renderPositions(positions) {
  if (!positions || !positions.length) {
    toggleSection(els.sectionExperience, false);
    return;
  }

  els.positions.innerHTML = positions
    .map((p) => {
      const title = escapeHtml(p.title || "Role");
      const company = escapeHtml(p.company_name || "");
      const dates = escapeHtml(formatDateRange(p.date_range));
      const location = escapeHtml(p.location || "");
      const employment = escapeHtml(p.employment_type || "");
      const meta = [dates, location, employment].filter(Boolean).join(" · ");
      const desc = p.description
        ? `<p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">${escapeHtml(p.description)}</p>`
        : "";
      return `
        <article class="border-b border-slate-100 pb-5 last:border-0 last:pb-0">
          <h4 class="font-semibold text-slate-900">${title}</h4>
          ${company ? `<p class="text-sm text-slate-700">${company}</p>` : ""}
          ${meta ? `<p class="mt-0.5 text-xs text-slate-500">${meta}</p>` : ""}
          ${desc}
        </article>
      `;
    })
    .join("");

  toggleSection(els.sectionExperience, true);
}

function renderEducations(educations) {
  if (!educations || !educations.length) {
    toggleSection(els.sectionEducation, false);
    return;
  }

  els.educations.innerHTML = educations
    .map((e) => {
      const school = escapeHtml(e.school_name || "School");
      const degreeBits = [e.degree_name, e.field_of_study].filter(Boolean).join(", ");
      const dates = escapeHtml(formatDateRange(e.date_range));
      const grade = e.grade ? `Grade: ${escapeHtml(e.grade)}` : "";
      const meta = [dates, grade].filter(Boolean).join(" · ");
      const activities = e.activities
        ? `<p class="mt-1 text-sm text-slate-600">${escapeHtml(e.activities)}</p>`
        : "";
      const desc = e.description
        ? `<p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">${escapeHtml(e.description)}</p>`
        : "";
      return `
        <article class="border-b border-slate-100 pb-5 last:border-0 last:pb-0">
          <h4 class="font-semibold text-slate-900">${school}</h4>
          ${degreeBits ? `<p class="text-sm text-slate-700">${escapeHtml(degreeBits)}</p>` : ""}
          ${meta ? `<p class="mt-0.5 text-xs text-slate-500">${meta}</p>` : ""}
          ${activities}
          ${desc}
        </article>
      `;
    })
    .join("");

  toggleSection(els.sectionEducation, true);
}

function renderSkills(skills, skillsTotal) {
  if (!skills || !skills.length) {
    toggleSection(els.sectionSkills, false);
    return;
  }

  const chips = skills
    .map(
      (s) =>
        `<span class="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">${escapeHtml(s.name)}</span>`,
    )
    .join("");

  let more = "";
  if (typeof skillsTotal === "number" && skillsTotal > skills.length) {
    const remaining = skillsTotal - skills.length;
    more = `<span class="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-600">+${remaining} more</span>`;
  }

  els.skills.innerHTML = chips + more;
  toggleSection(els.sectionSkills, true);
}

function renderCertifications(certs) {
  if (!certs || !certs.length) {
    toggleSection(els.sectionCerts, false);
    return;
  }

  els.certifications.innerHTML = certs
    .map((c) => {
      const name = escapeHtml(c.name || "Certification");
      const title = c.url
        ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer" class="font-semibold text-brand-500 hover:underline">${name}</a>`
        : `<span class="font-semibold text-slate-900">${name}</span>`;
      const authority = c.authority
        ? `<p class="text-sm text-slate-700">${escapeHtml(c.authority)}</p>`
        : "";
      const issued = c.issue_date
        ? `<p class="mt-0.5 text-xs text-slate-500">Issued ${escapeHtml(c.issue_date)}</p>`
        : "";
      return `
        <article class="border-b border-slate-100 pb-4 last:border-0 last:pb-0">
          ${title}
          ${authority}
          ${issued}
        </article>
      `;
    })
    .join("");

  toggleSection(els.sectionCerts, true);
}

function renderLanguages(languages) {
  if (!languages || !languages.length) {
    toggleSection(els.sectionLanguages, false);
    return;
  }

  els.languages.innerHTML = languages
    .map((l) => {
      const name = escapeHtml(l.name || "Language");
      const proficiency = l.proficiency
        ? `<span class="text-slate-500"> — ${escapeHtml(l.proficiency)}</span>`
        : "";
      return `<p class="text-sm text-slate-800">${name}${proficiency}</p>`;
    })
    .join("");

  toggleSection(els.sectionLanguages, true);
}

function renderTreasury(items) {
  if (!items || !items.length) {
    toggleSection(els.sectionMedia, false);
    return;
  }

  els.treasury.innerHTML = items
    .map((t) => {
      const title = escapeHtml(t.title || t.url || "Media");
      const link = t.url
        ? `<a href="${escapeHtml(t.url)}" target="_blank" rel="noopener noreferrer" class="font-medium text-brand-500 hover:underline">${title}</a>`
        : `<span class="font-medium text-slate-900">${title}</span>`;
      const kind = t.kind
        ? `<span class="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-600">${escapeHtml(t.kind)}</span>`
        : "";
      const provider = t.provider
        ? `<span class="text-xs text-slate-500">${escapeHtml(t.provider)}</span>`
        : "";
      return `
        <div class="flex flex-wrap items-center gap-2 text-sm">
          ${link}
          ${kind}
          ${provider}
        </div>
      `;
    })
    .join("");

  toggleSection(els.sectionMedia, true);
}

function renderProfile(profile) {
  renderHeader(profile);
  renderAbout(profile.summary);
  renderPositions(profile.positions);
  renderEducations(profile.educations);
  renderSkills(profile.skills, profile.skills_total);
  renderCertifications(profile.certifications);
  renderLanguages(profile.languages);
  renderTreasury(profile.treasury_media);

  if (profile.fetched_at) {
    const d = new Date(profile.fetched_at);
    els.fetchedAt.textContent = `Fetched ${d.toLocaleString()}`;
  } else {
    els.fetchedAt.textContent = "";
  }

  els.result.classList.remove("hidden");
}

async function fetchProfile(url) {
  hideError();
  els.result.classList.add("hidden");
  setLoading(true);

  try {
    const endpoint = `${API_BASE}/api/profile?url=${encodeURIComponent(url)}`;
    const res = await fetch(endpoint);
    let body = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }

    if (!res.ok) {
      showError(friendlyError(res.status, body));
      return;
    }

    renderProfile(body);
  } catch {
    showError(
      `Could not reach the API at ${API_BASE}. Is the server running? Pass ?api=http://localhost:8000 to override.`,
    );
  } finally {
    setLoading(false);
  }
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const url = els.input.value.trim();
  if (!url) {
    showError("Paste a LinkedIn profile URL or vanity slug first.");
    return;
  }
  fetchProfile(url);
});
