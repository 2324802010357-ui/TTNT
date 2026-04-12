const ROWS = 21;
const COLS = 31;
const CELL_SIZE = 24;
const EXIT_COUNT = 3;
const START_POSITION = [1, 1];
const MAX_GENERATION_ATTEMPTS = 20;
const VISITED_CELL_DELAY_MS = 12;
const PATH_CELL_DELAY_MS = 30;

const canvas = document.getElementById("mazeCanvas");
const ctx = canvas.getContext("2d");
const generateBtn = document.getElementById("generateBtn");
const solveBtn = document.getElementById("solveBtn");
const algorithmSelect = document.getElementById("algorithmSelect");
const statusText = document.getElementById("statusText");
const statsText = document.getElementById("statsText");

/** @type {number[][]} */
let maze = [];
/** @type {[number, number]} */
let start = [...START_POSITION];
/** @type {Array<[number, number]>} */
let exits = [];
let isAnimating = false;

function inBounds(r, c) {
  return r >= 0 && r < ROWS && c >= 0 && c < COLS;
}

function key(r, c) {
  return `${r},${c}`;
}

function neighbors4(r, c) {
  return [
    [r - 1, c],
    [r + 1, c],
    [r, c - 1],
    [r, c + 1],
  ].filter(([nr, nc]) => inBounds(nr, nc));
}

function shuffle(array) {
  for (let i = array.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}

function createGrid(rows, cols, fillValue = 1) {
  return Array.from({ length: rows }, () => Array(cols).fill(fillValue));
}

function generateMazeBase() {
  const grid = createGrid(ROWS, COLS, 1);
  const stack = [[...START_POSITION]];
  grid[START_POSITION[0]][START_POSITION[1]] = 0;

  while (stack.length > 0) {
    const [r, c] = stack[stack.length - 1];
    const candidates = [
      [r - 2, c],
      [r + 2, c],
      [r, c - 2],
      [r, c + 2],
    ].filter(([nr, nc]) => nr > 0 && nr < ROWS - 1 && nc > 0 && nc < COLS - 1 && grid[nr][nc] === 1);

    if (candidates.length === 0) {
      stack.pop();
      continue;
    }

    shuffle(candidates);
    const [nr, nc] = candidates[0];
    const wallRow = (r + nr) / 2;
    const wallCol = (c + nc) / 2;
    grid[wallRow][wallCol] = 0;
    grid[nr][nc] = 0;
    stack.push([nr, nc]);
  }

  return grid;
}

function bfsDistances(grid, source) {
  const dist = createGrid(ROWS, COLS, -1);
  const q = [source];
  let queueIndex = 0;
  dist[source[0]][source[1]] = 0;

  while (queueIndex < q.length) {
    const [r, c] = q[queueIndex++];
    for (const [nr, nc] of neighbors4(r, c)) {
      if (grid[nr][nc] !== 0 || dist[nr][nc] !== -1) continue;
      dist[nr][nc] = dist[r][c] + 1;
      q.push([nr, nc]);
    }
  }

  return dist;
}

function borderCandidates(grid) {
  const candidates = [];

  for (let c = 1; c < COLS - 1; c += 1) {
    if (grid[1][c] === 0) candidates.push([0, c, 1, c]);
    if (grid[ROWS - 2][c] === 0) candidates.push([ROWS - 1, c, ROWS - 2, c]);
  }
  for (let r = 1; r < ROWS - 1; r += 1) {
    if (grid[r][1] === 0) candidates.push([r, 0, r, 1]);
    if (grid[r][COLS - 2] === 0) candidates.push([r, COLS - 1, r, COLS - 2]);
  }

  return candidates;
}

function placeDistinctExits(grid, source, desired = EXIT_COUNT) {
  const dist = bfsDistances(grid, source);
  const candidates = borderCandidates(grid)
    .map(([er, ec, ir, ic]) => ({
      exit: [er, ec],
      inner: [ir, ic],
      distance: dist[ir][ic] >= 0 ? dist[ir][ic] + 1 : -1,
    }))
    .filter((item) => item.distance > 0);

  shuffle(candidates);
  const usedDistances = new Set();
  const selected = [];

  for (const item of candidates) {
    if (selected.length >= desired) break;
    if (usedDistances.has(item.distance)) continue;
    usedDistances.add(item.distance);
    selected.push(item);
  }

  if (selected.length < desired) {
    const usedExit = new Set(selected.map((s) => key(s.exit[0], s.exit[1])));
    for (const item of candidates) {
      if (selected.length >= desired) break;
      if (usedExit.has(key(item.exit[0], item.exit[1]))) continue;
      selected.push(item);
      usedExit.add(key(item.exit[0], item.exit[1]));
    }
  }

  if (selected.length === 0) return [];

  for (const item of selected) {
    const [er, ec] = item.exit;
    grid[er][ec] = 0;
  }

  return selected.map((s) => s.exit);
}

function generateMazeWithExits() {
  for (let attempt = 0; attempt < MAX_GENERATION_ATTEMPTS; attempt += 1) {
    const grid = generateMazeBase();
    const source = [...START_POSITION];
    const generatedExits = placeDistinctExits(grid, source, EXIT_COUNT);
    if (generatedExits.length >= 2) {
      return { grid, source, generatedExits };
    }
  }

  const fallbackGrid = generateMazeBase();
  const fallbackExits = placeDistinctExits(fallbackGrid, [...START_POSITION], 2);
  return { grid: fallbackGrid, source: [...START_POSITION], generatedExits: fallbackExits };
}

function reconstructPath(parent, end) {
  const path = [];
  let current = end;
  while (current) {
    path.push(current);
    current = parent.get(key(current[0], current[1])) || null;
  }
  path.reverse();
  return path;
}

function solveBFS(grid, source, goalList) {
  const goalSet = new Set(goalList.map(([r, c]) => key(r, c)));
  const q = [source];
  let head = 0;
  const visitedSet = new Set([key(source[0], source[1])]);
  const parent = new Map();
  const visitedOrder = [];

  while (head < q.length) {
    const [r, c] = q[head++];
    visitedOrder.push([r, c]);
    if (goalSet.has(key(r, c))) {
      const path = reconstructPath(parent, [r, c]);
      return { visitedOrder, path, exit: [r, c] };
    }

    for (const [nr, nc] of neighbors4(r, c)) {
      if (grid[nr][nc] !== 0) continue;
      const neighborKey = key(nr, nc);
      if (visitedSet.has(neighborKey)) continue;
      visitedSet.add(neighborKey);
      parent.set(neighborKey, [r, c]);
      q.push([nr, nc]);
    }
  }

  return { visitedOrder, path: [], exit: null };
}

function minGoalHeuristic(r, c, goals) {
  let min = Infinity;
  for (const [gr, gc] of goals) {
    const d = Math.abs(r - gr) + Math.abs(c - gc);
    if (d < min) min = d;
  }
  return min;
}

function solveAStar(grid, source, goalList) {
  const goalSet = new Set(goalList.map(([r, c]) => key(r, c)));
  const open = [{ node: source, f: minGoalHeuristic(source[0], source[1], goalList) }];
  const gScore = new Map([[key(source[0], source[1]), 0]]);
  const parent = new Map();
  const closed = new Set();
  const visitedOrder = [];

  while (open.length > 0) {
    open.sort((a, b) => a.f - b.f);
    const current = open.shift().node;
    const [r, c] = current;
    const currentKey = key(r, c);
    if (closed.has(currentKey)) continue;
    closed.add(currentKey);
    visitedOrder.push([r, c]);

    if (goalSet.has(currentKey)) {
      return { visitedOrder, path: reconstructPath(parent, [r, c]), exit: [r, c] };
    }

    const currentG = gScore.get(currentKey);
    for (const [nr, nc] of neighbors4(r, c)) {
      if (grid[nr][nc] !== 0) continue;
      const neighborKey = key(nr, nc);
      if (closed.has(neighborKey)) continue;
      const tentativeG = currentG + 1;
      if (tentativeG >= (gScore.get(neighborKey) ?? Infinity)) continue;
      gScore.set(neighborKey, tentativeG);
      parent.set(neighborKey, [r, c]);
      const h = minGoalHeuristic(nr, nc, goalList);
      open.push({ node: [nr, nc], f: tentativeG + h });
    }
  }

  return { visitedOrder, path: [], exit: null };
}

function drawCell(r, c, color) {
  ctx.fillStyle = color;
  ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
}

function drawMaze(overlays = {}) {
  const visited = overlays.visited || new Set();
  const path = overlays.path || new Set();
  const source = overlays.source || null;
  const goal = overlays.goal || null;

  for (let r = 0; r < ROWS; r += 1) {
    for (let c = 0; c < COLS; c += 1) {
      const k = key(r, c);
      if (maze[r][c] === 1) {
        drawCell(r, c, "#0f172a");
      } else if (path.has(k)) {
        drawCell(r, c, "#f97316");
      } else if (visited.has(k)) {
        drawCell(r, c, "#22d3ee");
      } else {
        drawCell(r, c, "#f8fafc");
      }
    }
  }

  for (const [er, ec] of exits) {
    drawCell(er, ec, "#22c55e");
  }

  if (source) {
    drawCell(source[0], source[1], "#2563eb");
  }
  if (goal) {
    drawCell(goal[0], goal[1], "#ef4444");
  }

  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 0.5;
  for (let r = 0; r <= ROWS; r += 1) {
    ctx.beginPath();
    ctx.moveTo(0, r * CELL_SIZE);
    ctx.lineTo(COLS * CELL_SIZE, r * CELL_SIZE);
    ctx.stroke();
  }
  for (let c = 0; c <= COLS; c += 1) {
    ctx.beginPath();
    ctx.moveTo(c * CELL_SIZE, 0);
    ctx.lineTo(c * CELL_SIZE, ROWS * CELL_SIZE);
    ctx.stroke();
  }
}

async function animateResult(visitedOrder, pathNodes, exitNode) {
  isAnimating = true;
  generateBtn.disabled = true;
  solveBtn.disabled = true;

  const visitedSet = new Set();
  const pathSet = new Set();

  for (const [r, c] of visitedOrder) {
    visitedSet.add(key(r, c));
    drawMaze({ visited: visitedSet, path: pathSet, source: start, goal: exitNode });
    await new Promise((resolve) => setTimeout(resolve, VISITED_CELL_DELAY_MS));
  }

  for (const [r, c] of pathNodes) {
    pathSet.add(key(r, c));
    drawMaze({ visited: visitedSet, path: pathSet, source: start, goal: exitNode });
    await new Promise((resolve) => setTimeout(resolve, PATH_CELL_DELAY_MS));
  }

  isAnimating = false;
  generateBtn.disabled = false;
  solveBtn.disabled = false;
}

function resetMaze() {
  const { grid, source, generatedExits } = generateMazeWithExits();
  maze = grid;
  start = source;
  exits = generatedExits;
  statusText.textContent = "Đã tạo mê cung mới.";
  statsText.textContent = "Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -";
  drawMaze({ source: start });
}

async function solveMaze() {
  if (isAnimating) return;
  if (!exits.length) {
    statusText.textContent = "Không có lối ra hợp lệ.";
    return;
  }

  const algorithm = algorithmSelect.value;
  statusText.textContent = `Đang giải mê cung bằng ${algorithm.toUpperCase()}...`;
  const startTime = performance.now();
  const result =
    algorithm === "astar" ? solveAStar(maze, start, exits) : solveBFS(maze, start, exits);
  const elapsed = (performance.now() - startTime).toFixed(2);

  if (!result.path.length || !result.exit) {
    statusText.textContent = "Không tìm thấy đường đi.";
    statsText.textContent = `Bước đi: -, Đã duyệt: ${result.visitedOrder.length}, Thời gian: ${elapsed} ms, Lối ra: -`;
    drawMaze({ source: start });
    return;
  }

  await animateResult(result.visitedOrder, result.path, result.exit);

  const stepCount = Math.max(result.path.length - 1, 0);
  statusText.textContent = `Hoàn thành bằng ${algorithm.toUpperCase()}.`;
  statsText.textContent = `Bước đi: ${stepCount}, Đã duyệt: ${result.visitedOrder.length}, Thời gian: ${elapsed} ms, Lối ra: (${result.exit[0]}, ${result.exit[1]})`;
}

generateBtn.addEventListener("click", resetMaze);
solveBtn.addEventListener("click", solveMaze);

canvas.width = COLS * CELL_SIZE;
canvas.height = ROWS * CELL_SIZE;
resetMaze();
