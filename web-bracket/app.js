const ORDER = {
  r1: [1, 8, 5, 4, 6, 3, 7, 2],
  r2: [1, 2, 3, 4],
  r3: [1, 2],
};

const state = {
  data: null,
  tab: "mens",
  mobileRegion: {
    mens: "W",
    womens: "W",
  },
  winners: {
    mens: {},
    womens: {},
  },
};

const REGION_DISPLAY_NAMES = {
  W: "EAST",
  X: "SOUTH",
  Y: "MIDWEST",
  Z: "WEST",
};

const MOBILE_REGION_ORDER = ["W", "Z", "X", "Y"];
const MOBILE_FINALS_KEY = "FINALS";

function seedNum(seed) {
  const m = seed.match(/\d+/);
  return m ? Number(m[0]) : 0;
}

function prob(teamAId, teamBId, tournament) {
  const a = Number(teamAId);
  const b = Number(teamBId);
  const low = Math.min(a, b);
  const high = Math.max(a, b);
  const key = `${low}_${high}`;
  const base = tournament.probabilities[key] ?? 0.5;
  return a === low ? base : 1 - base;
}

function teamLabel(team, opp, tournament) {
  if (!team) return "TBD";
  const pct = opp ? `${(prob(team.id, opp.id, tournament) * 100).toFixed(1)}%` : "--%";
  return `(${seedNum(team.seed)}) ${team.name} ${pct}`;
}

function getTeamFromRef(ref, tournament, winners) {
  if (tournament.seedTeams[ref]) return tournament.seedTeams[ref];
  if (tournament.slotMap[ref]) return winners[ref] || null;
  return null;
}

function getMatchup(slot, tournament, winners) {
  const info = tournament.slotMap[slot];
  const t1 = getTeamFromRef(info.strong, tournament, winners);
  const t2 = getTeamFromRef(info.weak, tournament, winners);
  return [t1, t2];
}

function clearDescendants(slot, tournament, winners) {
  const stack = [...(tournament.children[slot] || [])];
  while (stack.length) {
    const cur = stack.pop();
    delete winners[cur];
    const kids = tournament.children[cur] || [];
    for (const kid of kids) stack.push(kid);
  }
}

function pickWinner(slot, team) {
  const tournament = state.data.tournaments[state.tab];
  const winners = state.winners[state.tab];
  winners[slot] = team;
  clearDescendants(slot, tournament, winners);
  render();
}

function slotsForRegion(region) {
  return {
    r1: ORDER.r1.map((n) => `R1${region}${n}`),
    r2: ORDER.r2.map((n) => `R2${region}${n}`),
    r3: ORDER.r3.map((n) => `R3${region}${n}`),
    r4: [`R4${region}1`],
  };
}

function layoutPoints(direction, width, cardW) {
  const leftToRight = direction === "ltr";
  const x = leftToRight
    ? [0.5, 25.5, 50.5, 75.5]
    : [75.5, 50.5, 25.5, 0.5];

  const y1 = [0, 86, 172, 258, 344, 430, 516, 602];
  const y2 = [43, 215, 387, 559];
  const y3 = [129, 473];
  const y4 = [301];

  return {
    x: x.map((pct) => (pct / 100) * width),
    y1,
    y2,
    y3,
    y4,
  };
}

function createCard(slot, t1, t2, selectedId, tournament, x, y, cardW) {
  const card = document.createElement("div");
  card.className = "card";
  card.style.left = `${x}px`;
  card.style.top = `${y}px`;
  card.style.width = `${cardW}px`;

  const b1 = document.createElement("button");
  b1.className = `pick-btn ${selectedId === (t1 && t1.id) ? "selected" : ""}`;
  b1.textContent = teamLabel(t1, t2, tournament);
  b1.title = b1.textContent;
  b1.disabled = !t1;
  b1.onclick = () => pickWinner(slot, t1);

  const b2 = document.createElement("button");
  b2.className = `pick-btn ${selectedId === (t2 && t2.id) ? "selected" : ""}`;
  b2.textContent = teamLabel(t2, t1, tournament);
  b2.title = b2.textContent;
  b2.disabled = !t2;
  b2.onclick = () => pickWinner(slot, t2);

  card.appendChild(b1);
  card.appendChild(b2);
  return card;
}

function drawConnector(svg, fromX, fromY, toX, toY, direction) {
  const midX = direction === "ltr" ? fromX + 18 : fromX - 18;
  const l1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
  l1.setAttribute("x1", fromX);
  l1.setAttribute("y1", fromY);
  l1.setAttribute("x2", midX);
  l1.setAttribute("y2", fromY);

  const l2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
  l2.setAttribute("x1", midX);
  l2.setAttribute("y1", fromY);
  l2.setAttribute("x2", midX);
  l2.setAttribute("y2", toY);

  const l3 = document.createElementNS("http://www.w3.org/2000/svg", "line");
  l3.setAttribute("x1", midX);
  l3.setAttribute("y1", toY);
  l3.setAttribute("x2", toX);
  l3.setAttribute("y2", toY);

  svg.appendChild(l1);
  svg.appendChild(l2);
  svg.appendChild(l3);
}

function cardAnchors(x, y, cardW) {
  return {
    left: x,
    right: x + cardW,
    midY: y + 29,
  };
}

function renderRegion(region, direction, tournament) {
  const winners = state.winners[state.tab];
  const regionWrap = document.createElement("section");
  regionWrap.className = "region";

  const title = document.createElement("h3");
  title.className = "region-title";
  title.textContent = REGION_DISPLAY_NAMES[region] || region;
  regionWrap.appendChild(title);

  const board = document.createElement("div");
  board.className = "region-board";
  regionWrap.appendChild(board);

  const slots = slotsForRegion(region);

  requestAnimationFrame(() => {
    const boardW = board.clientWidth;
    const cardW = boardW * 0.24;
    const p = layoutPoints(direction, boardW, cardW);

    board.innerHTML = "";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("region-svg");
    board.appendChild(svg);

    const anchors = {};

    slots.r1.forEach((slot, i) => {
      const [t1, t2] = getMatchup(slot, tournament, winners);
      const selected = winners[slot] ? winners[slot].id : null;
      const card = createCard(slot, t1, t2, selected, tournament, p.x[0], p.y1[i], cardW);
      board.appendChild(card);
      anchors[slot] = cardAnchors(p.x[0], p.y1[i], cardW);
    });

    slots.r2.forEach((slot, i) => {
      const [t1, t2] = getMatchup(slot, tournament, winners);
      const selected = winners[slot] ? winners[slot].id : null;
      const card = createCard(slot, t1, t2, selected, tournament, p.x[1], p.y2[i], cardW);
      board.appendChild(card);
      anchors[slot] = cardAnchors(p.x[1], p.y2[i], cardW);
    });

    slots.r3.forEach((slot, i) => {
      const [t1, t2] = getMatchup(slot, tournament, winners);
      const selected = winners[slot] ? winners[slot].id : null;
      const card = createCard(slot, t1, t2, selected, tournament, p.x[2], p.y3[i], cardW);
      board.appendChild(card);
      anchors[slot] = cardAnchors(p.x[2], p.y3[i], cardW);
    });

    const slot = slots.r4[0];
    const [t1, t2] = getMatchup(slot, tournament, winners);
    const selected = winners[slot] ? winners[slot].id : null;
    const card = createCard(slot, t1, t2, selected, tournament, p.x[3], p.y4[0], cardW);
    board.appendChild(card);
    anchors[slot] = cardAnchors(p.x[3], p.y4[0], cardW);

    for (const s of [...slots.r2, ...slots.r3, ...slots.r4]) {
      const info = tournament.slotMap[s];
      const target = anchors[s];
      const p1 = anchors[info.strong];
      const p2 = anchors[info.weak];
      if (p1 && p2 && target) {
        const from1X = direction === "ltr" ? p1.right : p1.left;
        const from2X = direction === "ltr" ? p2.right : p2.left;
        const toX = direction === "ltr" ? target.left : target.right;
        drawConnector(svg, from1X, p1.midY, toX, target.midY, direction);
        drawConnector(svg, from2X, p2.midY, toX, target.midY, direction);
      }
    }
  });

  return regionWrap;
}

function renderCenter(tournament) {
  const winners = state.winners[state.tab];
  const center = document.createElement("section");
  center.className = "center-col";

  const inner = document.createElement("div");
  inner.className = "center-inner";
  center.appendChild(inner);

  const addConnector = () => {
    const conn = document.createElement("div");
    conn.className = "center-connector";
    inner.appendChild(conn);
  };

  const addSlot = (slot, title) => {
    const wrap = document.createElement("div");
    wrap.className = "center-slot";

    const h = document.createElement("div");
    h.className = "center-title";
    h.textContent = slot === "R6CH" ? `${title} 🏆` : title;

    const [t1, t2] = getMatchup(slot, tournament, winners);
    const selected = winners[slot] ? winners[slot].id : null;

    const b1 = document.createElement("button");
    b1.className = `pick-btn ${selected === (t1 && t1.id) ? "selected" : ""}`;
    b1.textContent = teamLabel(t1, t2, tournament);
    b1.title = b1.textContent;
    b1.disabled = !t1;
    b1.onclick = () => pickWinner(slot, t1);

    const b2 = document.createElement("button");
    b2.className = `pick-btn ${selected === (t2 && t2.id) ? "selected" : ""}`;
    b2.textContent = teamLabel(t2, t1, tournament);
    b2.title = b2.textContent;
    b2.disabled = !t2;
    b2.onclick = () => pickWinner(slot, t2);

    wrap.appendChild(h);
    wrap.appendChild(b1);
    wrap.appendChild(b2);
    inner.appendChild(wrap);
  };

  addSlot("R5WX", "FINAL FOUR");
  addConnector();
  addSlot("R6CH", "CHAMPIONSHIP");
  addConnector();
  addSlot("R5YZ", "FINAL FOUR");

  const champ = winners.R6CH;
  if (champ) {
    const c = document.createElement("div");
    c.className = "champion";
    c.textContent = `Champion: (${seedNum(champ.seed)}) ${champ.name}`;
    inner.appendChild(c);
  }

  return center;
}

function isMobileLayout() {
  return window.innerWidth <= 768;
}

function regionDirection(region) {
  return region === "W" || region === "X" ? "ltr" : "rtl";
}

function renderMobileRegionControls() {
  const wrap = document.createElement("section");
  wrap.className = "mobile-region-controls";

  [...MOBILE_REGION_ORDER, MOBILE_FINALS_KEY].forEach((region) => {
    const btn = document.createElement("button");
    btn.className = `mobile-region-btn ${state.mobileRegion[state.tab] === region ? "active" : ""}`;
    btn.textContent = region === MOBILE_FINALS_KEY ? "FINAL FOUR" : REGION_DISPLAY_NAMES[region];
    btn.onclick = () => {
      state.mobileRegion[state.tab] = region;
      render();
    };
    wrap.appendChild(btn);
  });

  return wrap;
}

function render() {
  const app = document.getElementById("app");
  app.innerHTML = "";

  const tournament = state.data.tournaments[state.tab];
  const mobile = isMobileLayout();

  if (mobile) {
    const mobileLayout = document.createElement("div");
    mobileLayout.className = "mobile-layout";

    mobileLayout.appendChild(renderMobileRegionControls());

    if (state.mobileRegion[state.tab] === MOBILE_FINALS_KEY) {
      mobileLayout.appendChild(renderCenter(tournament));
    } else {
      mobileLayout.appendChild(
        renderRegion(state.mobileRegion[state.tab], regionDirection(state.mobileRegion[state.tab]), tournament),
      );
    }

    app.appendChild(mobileLayout);
    return;
  }

  const layout = document.createElement("div");
  layout.className = "tournament-layout";

  const left = document.createElement("div");
  left.className = "region-stack";
  left.appendChild(renderRegion("W", "ltr", tournament));
  left.appendChild(renderRegion("X", "ltr", tournament));

  const center = renderCenter(tournament);

  const right = document.createElement("div");
  right.className = "region-stack";
  right.appendChild(renderRegion("Z", "rtl", tournament));
  right.appendChild(renderRegion("Y", "rtl", tournament));

  layout.appendChild(left);
  layout.appendChild(center);
  layout.appendChild(right);

  app.appendChild(layout);
}

function setupControls() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.tab = btn.dataset.tab;
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      render();
    });
  });

  document.getElementById("clearPicks").addEventListener("click", () => {
    state.winners[state.tab] = {};
    render();
  });
}

async function init() {
  const res = await fetch("./bracket_data_2026.json");
  state.data = await res.json();
  setupControls();
  render();
}

window.addEventListener("resize", () => render());
init();
