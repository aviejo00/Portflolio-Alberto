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
const combinationTable = document.querySelector("#combinationTable");
const combinationMessage = document.querySelector("#combinationMessage");
const suggestCombinationsButton = document.querySelector("#suggestCombinationsButton");
const clearCombinationsButton = document.querySelector("#clearCombinationsButton");
const SESSION_KEY = "outfitPlannerSession";

const universalColors = new Set(["black", "white"]);
const colorAliases = {
  grey: "gray",
  violet: "purple",
  "dark-blue": "navy",
  "dark blue": "navy",
  "dark-violet": "purple",
  "dark violet": "purple",
};

// Compact pairing rules based on the Bright Side color-combination guide.
const colorCompatibility = {
  beige: ["blue", "brown", "green", "black", "red", "white"],
  blue: ["white", "beige", "red", "yellow", "brown", "gray", "orange", "green"],
  brown: ["beige", "blue", "cream", "pink", "green", "yellow", "cyan"],
  cream: ["brown", "green", "turquoise", "red"],
  cyan: ["red", "gray", "brown", "orange", "pink", "white", "yellow"],
  gray: ["red", "pink", "blue", "purple", "yellow", "black", "white"],
  green: ["yellow", "orange", "brown", "gray", "cream", "black", "white", "blue"],
  lilac: ["orange", "pink", "purple", "olive", "gray", "yellow", "white"],
  mint: ["pink", "red", "brown", "purple", "turquoise"],
  navy: ["cyan", "yellow", "brown", "gray", "orange", "green", "red", "white"],
  olive: ["orange", "brown", "lilac", "pink"],
  orange: ["cyan", "blue", "lilac", "purple", "white", "black", "green"],
  pink: ["brown", "white", "mint", "olive", "gray", "turquoise", "blue"],
  purple: ["yellow", "gray", "turquoise", "mint", "orange", "brown"],
  red: ["yellow", "white", "green", "blue", "black", "beige", "cyan", "gray"],
  turquoise: ["pink", "red", "yellow", "brown", "cream", "purple"],
  yellow: ["blue", "lilac", "cyan", "purple", "gray", "black", "red", "green"],
};

let nextGarmentNumber = 1;
let session = null;
let manualCompatibility = {};

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

function normalizeColor(color) {
  const normalized = String(color || "").trim().toLowerCase();
  return colorAliases[normalized] || normalized;
}

function colorsCompatible(color1, color2) {
  const c1 = normalizeColor(color1);
  const c2 = normalizeColor(color2);

  if (!c1 || !c2) {
    return true;
  }

  if (c1 === c2 || universalColors.has(c1) || universalColors.has(c2)) {
    return true;
  }

  return (colorCompatibility[c1] || []).includes(c2) ||
    (colorCompatibility[c2] || []).includes(c1);
}

function createEmptyCompatibility(garments) {
  return garments.reduce((graph, garment) => {
    graph[garment.id] = [];
    return graph;
  }, {});
}

function addCompatibilityPair(graph, firstId, secondId) {
  if (!graph[firstId]) {
    graph[firstId] = [];
  }
  if (!graph[secondId]) {
    graph[secondId] = [];
  }
  if (!graph[firstId].includes(secondId)) {
    graph[firstId].push(secondId);
  }
  if (!graph[secondId].includes(firstId)) {
    graph[secondId].push(firstId);
  }
}

function hasCompatibilityEdges(graph) {
  return Object.values(graph || {}).some((ids) => ids.length > 0);
}

function isPairCompatible(graph, firstId, secondId) {
  return Boolean(graph[firstId]?.includes(secondId) || graph[secondId]?.includes(firstId));
}

function normalizeCompatibilityGraph(graph, garments) {
  const validIds = new Set(garments.map((garment) => garment.id));
  const normalized = createEmptyCompatibility(garments);

  Object.entries(graph || {}).forEach(([firstId, secondIds]) => {
    if (!validIds.has(firstId) || !Array.isArray(secondIds)) {
      return;
    }

    secondIds.forEach((secondId) => {
      if (validIds.has(secondId) && secondId !== firstId) {
        addCompatibilityPair(normalized, firstId, secondId);
      }
    });
  });

  return normalized;
}

function buildSuggestedCompatibility(garments) {
  const graph = createEmptyCompatibility(garments);

  garments.forEach((garment, index) => {
    garments.slice(index + 1).forEach((other) => {
      if (colorsCompatible(garment.color, other.color)) {
        addCompatibilityPair(graph, garment.id, other.id);
      }
    });
  });

  return graph;
}

function readManualCompatibility() {
  const garments = readGarments();
  const graph = createEmptyCompatibility(garments);

  combinationTable.querySelectorAll(".combination-checkbox:checked").forEach((checkbox) => {
    addCompatibilityPair(graph, checkbox.dataset.first, checkbox.dataset.second);
  });

  return graph;
}

function renderCombinationMatrix(graph = manualCompatibility) {
  const garments = readGarments();
  manualCompatibility = normalizeCompatibilityGraph(graph, garments);
  combinationTable.innerHTML = "";

  if (garments.length < 2) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No combinations yet.";
    combinationTable.append(empty);
    combinationMessage.textContent = "";
    return;
  }

  garments.forEach((garment, index) => {
    garments.slice(index + 1).forEach((other) => {
      const row = document.createElement("label");
      row.className = "combination-row";

      const checkbox = document.createElement("input");
      checkbox.className = "combination-checkbox";
      checkbox.type = "checkbox";
      checkbox.dataset.first = garment.id;
      checkbox.dataset.second = other.id;
      checkbox.checked = isPairCompatible(manualCompatibility, garment.id, other.id);
      checkbox.addEventListener("change", () => {
        manualCompatibility = readManualCompatibility();
        combinationMessage.textContent = hasCompatibilityEdges(manualCompatibility)
          ? "Manual combinations active."
          : "Color suggestions will be used.";
      });

      const label = document.createElement("span");
      label.textContent = `${prettyName(garment.id)} + ${prettyName(other.id)}`;

      row.append(checkbox, label);
      combinationTable.append(row);
    });
  });

  combinationMessage.textContent = hasCompatibilityEdges(manualCompatibility)
    ? "Manual combinations active."
    : "Color suggestions will be used.";
}

function renderGarmentRow(garment) {
  const row = garmentTemplate.content.firstElementChild.cloneNode(true);
  const idInput = row.querySelector(".garment-id");
  const typeInput = row.querySelector(".garment-type");
  const colorInput = row.querySelector(".garment-color");
  const warmthInput = row.querySelector(".garment-warmth");
  const waterproofInput = row.querySelector(".garment-waterproof");

  idInput.value = garment.id;
  typeInput.value = garment.type;
  colorInput.value = garment.color || "";
  warmthInput.value = garment.warmth;
  waterproofInput.checked = garment.waterproof;

  idInput.addEventListener("change", () => renderCombinationMatrix(manualCompatibility));
  colorInput.addEventListener("change", () => renderCombinationMatrix(manualCompatibility));
  row.querySelector(".remove-garment").addEventListener("click", () => {
    manualCompatibility = readManualCompatibility();
    row.remove();
    renderCombinationMatrix(manualCompatibility);
  });

  garmentTable.append(row);
}

function renderGarments(garments, compatibility = {}) {
  garmentTable.innerHTML = "";
  nextGarmentNumber = garments.length + 1;
  garments.forEach(renderGarmentRow);
  manualCompatibility = normalizeCompatibilityGraph(compatibility, readGarments());
  renderCombinationMatrix(manualCompatibility);
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
        color: row.querySelector(".garment-color").value || null,
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
    renderGarments(data.garments || [], data.compatibility || {});
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
    renderGarments(data.garments || [], data.compatibility || {});
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
    renderGarments(data.garments || [], data.compatibility || {});
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

  manualCompatibility = readManualCompatibility();

  try {
    const data = await apiPost("/garments/save", {
      ...session,
      garments: readGarments(),
      compatibility: manualCompatibility,
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

function applySuggestedCombinations() {
  const garments = readGarments();
  manualCompatibility = buildSuggestedCompatibility(garments);
  renderCombinationMatrix(manualCompatibility);
  combinationMessage.textContent = "Suggested combinations applied.";
}

function clearCombinations() {
  manualCompatibility = createEmptyCompatibility(readGarments());
  renderCombinationMatrix(manualCompatibility);
  combinationMessage.textContent = "Color suggestions will be used.";
}

function buildCompatibility(garments) {
  manualCompatibility = readManualCompatibility();

  if (hasCompatibilityEdges(manualCompatibility)) {
    return manualCompatibility;
  }

  return buildSuggestedCompatibility(garments);
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
renderCombinationMatrix();

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
    color: null,
    warmth: 0.25,
    waterproof: false,
  });
  nextGarmentNumber += 1;
  renderCombinationMatrix(manualCompatibility);
});

registerButton.addEventListener("click", registerProfile);
loginButton.addEventListener("click", loginProfile);
saveGarmentsButton.addEventListener("click", saveGarments);
logoutButton.addEventListener("click", logoutProfile);
suggestCombinationsButton.addEventListener("click", applySuggestedCombinations);
clearCombinationsButton.addEventListener("click", clearCombinations);
recommendButton.addEventListener("click", recommendOutfit);
