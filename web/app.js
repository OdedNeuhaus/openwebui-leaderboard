const OPENWEBUI_URL =
  window.APP_CONFIG?.OPENWEBUI_URL || "https://your-openwebui-url.example.com";
const BRAND_LOGO_URL = window.APP_CONFIG?.BRAND_LOGO_URL || "";

const mockLeaderboardData = [
  {
    name: "Finance Ops",
    messages: 1482,
    feedbacks: 93,
    streak: 12,
    activeToday: true,
    color: "linear-gradient(135deg, #5cf2c5, #c0ffe9)",
  },
  {
    name: "Customer Success",
    messages: 1338,
    feedbacks: 116,
    streak: 9,
    activeToday: true,
    color: "linear-gradient(135deg, #f8bc45, #ffe2a1)",
  },
  {
    name: "Product Squad",
    messages: 1256,
    feedbacks: 81,
    streak: 11,
    activeToday: true,
    color: "linear-gradient(135deg, #67b7ff, #b8dbff)",
  },
  {
    name: "HR Enablement",
    messages: 1044,
    feedbacks: 72,
    streak: 7,
    activeToday: false,
    color: "linear-gradient(135deg, #ff8e72, #ffc3b5)",
  },
  {
    name: "Security Desk",
    messages: 918,
    feedbacks: 58,
    streak: 13,
    activeToday: true,
    color: "linear-gradient(135deg, #a08cff, #d8d0ff)",
  },
  {
    name: "Legal",
    messages: 792,
    feedbacks: 37,
    streak: 5,
    activeToday: true,
    color: "linear-gradient(135deg, #7ef0c0, #d3ffed)",
  },
];

let leaderboardData = [];

function formatNumber(value) {
  return new Intl.NumberFormat("he-IL").format(value);
}

function initials(name) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2);
}

function rankByMetric(metric) {
  return leaderboardData
    .map((entry) => ({ ...entry, value: entry[metric] }))
    .sort((a, b) => b.value - a.value || b.messages - a.messages);
}

function fitPodiumScores() {
  const scores = document.querySelectorAll(".podium-score");

  scores.forEach((scoreElement) => {
    const card = scoreElement.closest(".podium-card");
    if (!card) {
      return;
    }

    const isFirst = card.classList.contains("rank-1");
    const maxSize = isFirst ? 66 : 58;
    const minSize = isFirst ? 34 : 28;
    let fontSize = maxSize;

    scoreElement.style.fontSize = `${fontSize}px`;

    while (scoreElement.scrollWidth > scoreElement.clientWidth && fontSize > minSize) {
      fontSize -= 1;
      scoreElement.style.fontSize = `${fontSize}px`;
    }
  });
}

function rankDecoration(rank) {
  if (rank === 1) {
    return "🏆";
  }

  if (rank === 2) {
    return "🥈";
  }

  if (rank === 3) {
    return "🥉";
  }

  return "";
}

function createPodiumCard(player, rank, metricLabel) {
  return `
    <article class="podium-card rank-${rank}">
      <div class="podium-rank">#${rank}<span class="podium-icon">${rankDecoration(rank)}</span></div>
      <div class="avatar" style="background:${player.color}">${initials(player.name)}</div>
      <p class="player-name name-text" dir="auto">${player.name}</p>
      <div class="podium-score">${formatNumber(player.value)}</div>
      <span class="metric-pill">${metricLabel}</span>
    </article>
  `;
}

function renderPodium(targetId, data, metricLabel) {
  const topThree = data.slice(0, 3);
  const order = [1, 0, 2];

  document.getElementById(targetId).innerHTML = order
    .map((slotIndex) => {
      const player = topThree[slotIndex];
      if (!player) {
        return "";
      }

      return createPodiumCard(player, slotIndex + 1, metricLabel);
    })
    .join("");
}

function renderTable(targetId, data, label) {
  document.getElementById(targetId).innerHTML = `
    <div class="table-header">
      <span>${label}</span>
      <span>משתמש</span>
      <span>מיקום</span>
    </div>
    ${data
      .map(
        (player, index) => `
          <article class="table-row">
            <div class="table-value">${formatNumber(player.value)}</div>
            <div class="table-player">
              <strong class="name-text" dir="auto">${player.name}</strong>
            </div>
            <div class="table-rank">#${index + 1}</div>
          </article>
        `
      )
      .join("")}
  `;
}

function renderFooter(data) {
  const leader = rankByMetric("messages")[0];
  const activePercent = Math.round((data.filter((item) => item.activeToday).length / data.length) * 100);

  document.getElementById("spotlight-name").textContent = leader.name;
  document.getElementById("activation-value").textContent = `${activePercent}%`;
  document.getElementById("spotlight-badge").textContent = "כולם רודפים אחרי המקום הראשון";
}

function renderSummaries() {
  const topUsage = rankByMetric("messages")[0];
  const topFeedback = rankByMetric("feedbacks")[0];

  document.getElementById(
    "usage-summary"
  ).textContent = `${topUsage.name} מובילים עם ${formatNumber(topUsage.messages)} הודעות`;
  document.getElementById(
    "feedback-summary"
  ).textContent = `${topFeedback.name} מובילים עם ${formatNumber(topFeedback.feedbacks)} משובים`;
}

function renderAll() {
  const usageData = rankByMetric("messages");
  const feedbackData = rankByMetric("feedbacks");

  renderPodium("usage-podium", usageData, "הודעות");
  renderTable("usage-table", usageData, "הודעות");
  renderPodium("feedback-podium", feedbackData, "משובים");
  renderTable("feedback-table", feedbackData, "משובים");
  renderSummaries();
  renderFooter(leaderboardData);
  fitPodiumScores();
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function simulateActivity() {
  leaderboardData.forEach((entry) => {
    entry.messages += randomInt(18, 140);
    entry.feedbacks += randomInt(0, 8);
    entry.streak = Math.max(1, entry.streak + randomInt(-1, 2));
    entry.activeToday = Math.random() > 0.18;
  });

  renderAll();
}

async function loadLeaderboardData() {
  const response = await fetch("./leaderboard-data.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load leaderboard-data.json (${response.status})`);
  }

  const payload = await response.json();
  if (!Array.isArray(payload)) {
    throw new Error("leaderboard-data.json must contain an array");
  }

  return payload;
}

function applyBrandLogo() {
  const logoImage = document.getElementById("brand-logo-image");
  const logoMark = document.getElementById("brand-logo-mark");

  if (!logoImage || !logoMark || !BRAND_LOGO_URL) {
    return;
  }

  logoImage.addEventListener("load", () => {
    logoImage.classList.remove("is-hidden");
    logoMark.classList.add("is-hidden");
  });

  logoImage.addEventListener("error", () => {
    logoImage.classList.add("is-hidden");
    logoMark.classList.remove("is-hidden");
  });

  logoImage.src = BRAND_LOGO_URL;
}

document.getElementById("openwebui-button").href = OPENWEBUI_URL;
applyBrandLogo();
window.addEventListener("resize", fitPodiumScores);

loadLeaderboardData()
  .then((data) => {
    leaderboardData = data;
    renderAll();
  })
  .catch(() => {
    leaderboardData = mockLeaderboardData.map((entry) => ({ ...entry }));
    renderAll();
  });
