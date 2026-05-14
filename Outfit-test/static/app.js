const dateInput = document.querySelector("#dateInput");
const minTempInput = document.querySelector("#minTempInput");
const maxTempInput = document.querySelector("#maxTempInput");
const rainInput = document.querySelector("#rainInput");
const garmentTable = document.querySelector("#garmentTable");
const garmentTemplate = document.querySelector("#garmentRowTemplate");
const resultPanel = document.querySelector("#resultPanel");
const recommendButton = document.querySelector("#recommendButton");
const addGarmentButton = document.querySelector("#addGarmentButton");
const usernameInput = document.querySelector("#usernameInput");
const passwordInput = document.querySelector("#passwordInput");
const profileStatus = document.querySelector("#profileStatus");
const profileMessage = document.querySelector("#profileMessage");
const registerButton = document.querySelector("#registerButton");
const loginButton = document.querySelector("#loginButton");
const saveGarmentsButton = document.querySelector("#saveGarmentsButton");
const logoutButton = document.querySelector("#logoutButton");
const SESSION_KEY = "outfitPlannerSession";
let nextGarmentNumber = 1;
let session = null;

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function prettyName(id) {
  return id.replaceAll("_", " ");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderGarmentRow(garment) {
  const row = garmentTemplate.content.firstElementChild.cloneNode(true);

  row.querySelector(".garment-id").value = garment.id;
  row.querySelector(".garment-type").value = garment.type;
  row.querySelector(".garment-warmth").value = garment.warmth;
  row.querySelector(".garment-waterproof").checked = garment.waterproof;
  row.querySelector(".remove-garment").addEventListener("click", () => row.remove());

  garmentTable.append(row);
}

function renderGarments(garments) {
  garmentTable.innerHTML = "";
  nextGarmentNumber = garments.length + 1;
  garments.forEach(renderGarmentRow);
}

function readGarments() {
  const rows = [...garmentTable.querySelectorAll(".garment-row")];
  const seen = new Set();

  return rows
    .map((row) => {
      const id = row.querySelector(".garment-id").value.trim();
      if (!id || seen.has(id)) {
        return null;
      }
      seen.add(id);

      return {
        id,
        type: row.querySelector(".garment-type").value,
        warmth: Number(row.querySelector(".garment-warmth").value),
        waterproof: row.querySelector(".garment-waterproof").checked,
      };
    })
    .filter(Boolean);
}

async function apiPost(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || data.error || "Request failed.");
  }

  return data;
}

function setProfileMessage(message, isError = false) {
  profileMessage.textContent = message;
  profileMessage.classList.toggle("error", isError);
}

function setSession(nextSession) {
  session = nextSession;

  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(SESSION_KEY);
  }

  updateProfileState();
}

function updateProfileState() {
  const loggedIn = Boolean(session);
  profileStatus.textContent = loggedIn ? session.username : "Guest";
  if (loggedIn) {
    usernameInput.value = session.username;
  }
  saveGarmentsButton.disabled = !loggedIn;
  logoutButton.disabled = !loggedIn;
}

function readCredentials() {
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    throw new Error("Username and password are required.");
  }

  return { username, password };
}

async function loadSavedGarments() {
  if (!session) {
    return;
  }

  try {
    const data = await apiPost("/garments/load", session);
    renderGarments(data.garments || []);
    setProfileMessage("Profile loaded.");
  } catch (error) {
    setSession(null);
    renderGarments([]);
    setProfileMessage(error.message, true);
  }
}

async function registerProfile() {
  try {
    const data = await apiPost("/register", readCredentials());
    passwordInput.value = "";
    setSession({ username: data.username, token: data.token });
    renderGarments(data.garments || []);
    setProfileMessage("Profile registered.");
  } catch (error) {
    setProfileMessage(error.message, true);
  }
}

async function loginProfile() {
  try {
    const data = await apiPost("/login", readCredentials());
    passwordInput.value = "";
    setSession({ username: data.username, token: data.token });
    renderGarments(data.garments || []);
    setProfileMessage("Profile loaded.");
  } catch (error) {
    setProfileMessage(error.message, true);
  }
}

async function saveGarments() {
  if (!session) {
    setProfileMessage("Log in before saving garments.", true);
    return;
  }

  try {
    const data = await apiPost("/garments/save", {
      ...session,
      garments: readGarments(),
    });
    setProfileMessage(`${data.saved} garments saved.`);
  } catch (error) {
    setProfileMessage(error.message, true);
  }
}

function logoutProfile() {
  setSession(null);
  passwordInput.value = "";
  renderGarments([]);
  resultPanel.innerHTML = '<p class="muted">No recommendation yet.</p>';
  setProfileMessage("Logged out.");
}

function buildCompatibility(garments) {
  return garments.reduce((graph, garment) => {
    graph[garment.id] = garments
      .filter((other) => other.id !== garment.id)
      .map((other) => other.id);
    return graph;
  }, {});
}

function renderLoading() {
  resultPanel.innerHTML = '<p class="muted">Choosing...</p>';
}

function renderError(message, blockedGarments = []) {
  resultPanel.innerHTML = `
    <p class="status-error">${escapeHtml(message)}</p>
    ${renderBlocked(blockedGarments)}
  `;
}

function renderBlocked(blockedGarments) {
  if (!blockedGarments.length) {
    return "";
  }

  return `
    <p class="score-line">Blocked this weekday</p>
    <ul class="blocked-list">
      ${blockedGarments.map((id) => `<li>${escapeHtml(prettyName(id))}</li>`).join("")}
    </ul>
  `;
}

function renderResult(data) {
  const outfit = data.outfit || [];
  resultPanel.innerHTML = `
    <h3 class="result-title">Recommended outfit</h3>
    <ul class="outfit-list">
      ${outfit.map((id) => `<li>${escapeHtml(prettyName(id))}</li>`).join("")}
    </ul>
    <p class="score-line">${escapeHtml(data.day)} ${escapeHtml(data.date)} - score ${Number(data.score).toFixed(2)}</p>
    ${renderBlocked(data.blocked_garments || [])}
  `;
}

async function recommendOutfit() {
  const garments = readGarments();

  if (!garments.some((g) => g.type === "top") ||
      !garments.some((g) => g.type === "bottom") ||
      !garments.some((g) => g.type === "shoes")) {
    renderError("Add at least one top, bottom, and shoes.");
    return;
  }

  renderLoading();

  const payload = {
    garments,
    compatibility: buildCompatibility(garments),
    weather: {
      date: dateInput.value,
      min_temp: Number(minTempInput.value),
      max_temp: Number(maxTempInput.value),
      rain: rainInput.checked,
    },
  };

  try {
    const response = await fetch("/recommend-outfit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (data.error) {
      renderError(data.error, data.blocked_garments || []);
      return;
    }

    renderResult(data);
  } catch (error) {
    renderError("The recommendation service is not responding.");
  }
}

dateInput.value = todayValue();
updateProfileState();

try {
  const savedSession = JSON.parse(localStorage.getItem(SESSION_KEY));
  if (savedSession && savedSession.username && savedSession.token) {
    setSession(savedSession);
    loadSavedGarments();
  }
} catch (error) {
  localStorage.removeItem(SESSION_KEY);
}

addGarmentButton.addEventListener("click", () => {
  renderGarmentRow({
    id: `item_${nextGarmentNumber}`,
    type: "top",
    warmth: 0.25,
    waterproof: false,
  });
  nextGarmentNumber += 1;
});

registerButton.addEventListener("click", registerProfile);
loginButton.addEventListener("click", loginProfile);
saveGarmentsButton.addEventListener("click", saveGarments);
logoutButton.addEventListener("click", logoutProfile);
recommendButton.addEventListener("click", recommendOutfit);
