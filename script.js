const ROWS = 31;
const COLS = 51;
const CELL_SIZE = 18;
const EXIT_COUNT = 4;
const START_POSITION = [1, 1];
const MAX_GENERATION_ATTEMPTS = 20;
const VISITED_CELL_DELAY_MS = 12;
const PATH_CELL_DELAY_MS = 30;

// Complexity features - Many Walls Maze (Nhiều tường)
const ROOM_COUNT = 0;
const ROOM_MIN_SIZE = 5;
const ROOM_MAX_SIZE = 12;
const LOOP_CARVE_RATE = 0.15;
const MIN_START_BRANCHES = 3;
const ENEMY_COUNT = 3;
const ENEMY_MIN_DISTANCE = 8;
const BRAID_RATE = 0.10;

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
/** @type {Array<[number, number]>} */
let enemies = [];
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

function carveRooms(grid) {
  for (let attempt = 0; attempt < ROOM_COUNT * 3; attempt += 1) {
    const rh = ROOM_MIN_SIZE + Math.floor(Math.random() * (ROOM_MAX_SIZE - ROOM_MIN_SIZE + 1));
    const rw = ROOM_MIN_SIZE + Math.floor(Math.random() * (ROOM_MAX_SIZE - ROOM_MIN_SIZE + 1));
    const r = 2 + Math.floor(Math.random() * Math.max(1, (ROWS - rh - 4) / 2)) * 2;
    const c = 2 + Math.floor(Math.random() * Math.max(1, (COLS - rw - 4) / 2)) * 2;
    
    if (r + rh >= ROWS - 1 || c + rw >= COLS - 1) continue;
    if (r === START_POSITION[0] && c === START_POSITION[1]) continue;
    
    let hasExit = false;
    for (let rr = r; rr < r + rh && rr < ROWS; rr += 1) {
      for (let cc = c; cc < c + rw && cc < COLS; cc += 1) {
        if (rr === r || rr === r + rh - 1 || cc === c || cc === c + rw - 1) {
          const hasAdjacentPassage = neighbors4(rr, cc).some(([nr, nc]) => {
            return inBounds(nr, nc) && grid[nr][nc] === 0 && (nr < r || nr >= r + rh || nc < c || nc >= c + rw);
          });
          if (hasAdjacentPassage) {
            hasExit = true;
            break;
          }
        }
      }
      if (hasExit) break;
    }
    
    if (!hasExit) continue;
    
    for (let rr = r; rr < r + rh && rr < ROWS; rr += 1) {
      for (let cc = c; cc < c + rw && cc < COLS; cc += 1) {
        grid[rr][cc] = 0;
      }
    }
  }
}

function carveLoops(grid) {
  const wallCells = [];
  for (let r = 1; r < ROWS - 1; r += 1) {
    for (let c = 1; c < COLS - 1; c += 1) {
      if (grid[r][c] !== 1) continue;
      const ns = neighbors4(r, c).filter(([nr, nc]) => grid[nr][nc] === 0);
      if (ns.length >= 2) {
        const vert = ns.filter(([nr]) => nr !== r);
        const horiz = ns.filter(([, nc]) => nc !== c);
        if ((vert.length === 2 && horiz.length === 0) || (horiz.length === 2 && vert.length === 0)) {
          wallCells.push([r, c]);
        }
      }
    }
  }
  
  shuffle(wallCells);
  const target = Math.ceil(wallCells.length * LOOP_CARVE_RATE);
  for (let i = 0; i < Math.min(target, wallCells.length); i += 1) {
    const [r, c] = wallCells[i];
    grid[r][c] = 0;
  }
}

function ensureStartBranches(grid, source) {
  const ns = neighbors4(source[0], source[1]).filter(([nr, nc]) => grid[nr][nc] === 0);
  if (ns.length < MIN_START_BRANCHES) {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const [sr, sc] = START_POSITION;
      const dirs = [[sr - 1, sc], [sr + 1, sc], [sr, sc - 1], [sr, sc + 1]];
      shuffle(dirs);
      for (const [nr, nc] of dirs) {
        if (!inBounds(nr, nc) || grid[nr][nc] === 0) continue;
        const openNeighbors = neighbors4(nr, nc).filter(([nnr, nnc]) => grid[nnr][nnc] === 0);
        if (openNeighbors.length > 0) {
          grid[nr][nc] = 0;
          return;
        }
      }
    }
  }
}

function placeEnemies(grid, source, existingExits) {
  const dist = bfsDistances(grid, source);
  const usedKeys = new Set();
  
  for (const [r, c] of [source, ...existingExits]) {
    usedKeys.add(key(r, c));
  }
  
  const candidates = [];
  for (let r = 1; r < ROWS - 1; r += 1) {
    for (let c = 1; c < COLS - 1; c += 1) {
      const k = key(r, c);
      if (usedKeys.has(k) || grid[r][c] !== 0) continue;
      const d = dist[r][c];
      if (d >= ENEMY_MIN_DISTANCE) {
        candidates.push({ pos: [r, c], dist: d });
      }
    }
  }
  
  candidates.sort((a, b) => b.dist - a.dist);
  const selected = [];
  for (const c of candidates) {
    if (selected.length >= ENEMY_COUNT) break;
    selected.push(c.pos);
    usedKeys.add(key(c.pos[0], c.pos[1]));
  }
  
  return selected;
}

function braidMaze(grid) {
  const deadEnds = [];
  for (let r = 1; r < ROWS - 1; r += 1) {
    for (let c = 1; c < COLS - 1; c += 1) {
      if (grid[r][c] !== 0) continue;
      const ns = neighbors4(r, c).filter(([nr, nc]) => grid[nr][nc] === 0);
      if (ns.length === 1) {
        deadEnds.push([r, c]);
      }
    }
  }
  
  shuffle(deadEnds);
  const target = Math.ceil(deadEnds.length * BRAID_RATE);
  for (let i = 0; i < Math.min(target, deadEnds.length); i += 1) {
    const [r, c] = deadEnds[i];
    const wallNeighbors = [];
    for (const [nr, nc] of [[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]]) {
      if (!inBounds(nr, nc) || grid[nr][nc] !== 1) continue;
      const wallNeighbors2 = neighbors4(nr, nc).filter(([nnr, nnc]) => grid[nnr][nnc] === 0);
      if (wallNeighbors2.length > 0) {
        wallNeighbors.push([nr, nc]);
      }
    }
    if (wallNeighbors.length > 0) {
      const [wr, wc] = wallNeighbors[Math.floor(Math.random() * wallNeighbors.length)];
      grid[wr][wc] = 0;
    }
  }
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
    if (ROOM_COUNT > 0) carveRooms(grid);
    carveLoops(grid);
    braidMaze(grid);
    const source = [...START_POSITION];
    const generatedExits = placeDistinctExits(grid, source, EXIT_COUNT);
    ensureStartBranches(grid, source);
    const generatedEnemies = placeEnemies(grid, source, generatedExits);
    if (generatedExits.length >= 2) {
      return { grid, source, generatedExits, generatedEnemies };
    }
  }

  const fallbackGrid = generateMazeBase();
  if (ROOM_COUNT > 0) carveRooms(fallbackGrid);
  carveLoops(fallbackGrid);
  braidMaze(fallbackGrid);
  const fallbackExits = placeDistinctExits(fallbackGrid, [...START_POSITION], 2);
  ensureStartBranches(fallbackGrid, [...START_POSITION]);
  const fallbackEnemies = placeEnemies(fallbackGrid, [...START_POSITION], fallbackExits);
  return { grid: fallbackGrid, source: [...START_POSITION], generatedExits: fallbackExits, generatedEnemies: fallbackEnemies };
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

  for (const [er, ec] of enemies) {
    drawCell(er, ec, "#a855f7");
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
  const { grid, source, generatedExits, generatedEnemies } = generateMazeWithExits();
  maze = grid;
  start = source;
  exits = generatedExits;
  enemies = generatedEnemies;
  statusText.textContent = "Đã tạo mê cung mới.";
  statsText.textContent = "Bước đi: -, Đã duyệt: -, Thời gian: -, Lối ra: -";
  drawMaze({ source: start });
}

async function solveMaze() {
  if (isAnimating) return;
  
  const targets = [...exits, ...enemies];
  if (!targets.length) {
    statusText.textContent = "Không có mục tiêu hợp lệ.";
    return;
  }

  const algorithm = algorithmSelect.value;
  statusText.textContent = `Đang giải mê cung bằng ${algorithm.toUpperCase()}...`;
  const startTime = performance.now();
  const result =
    algorithm === "astar" ? solveAStar(maze, start, targets) : solveBFS(maze, start, targets);
  const elapsed = (performance.now() - startTime).toFixed(2);

  if (!result.path.length || !result.exit) {
    statusText.textContent = "Không tìm thấy đường đi.";
    statsText.textContent = `Bước đi: -, Đã duyệt: ${result.visitedOrder.length}, Thời gian: ${elapsed} ms, Mục tiêu: -`;
    drawMaze({ source: start });
    return;
  }

  await animateResult(result.visitedOrder, result.path, result.exit);

  const stepCount = Math.max(result.path.length - 1, 0);
  const isExit = exits.some(([r, c]) => r === result.exit[0] && c === result.exit[1]);
  const goalType = isExit ? "Lối ra" : "Địch";
  statusText.textContent = `Hoàn thành bằng ${algorithm.toUpperCase()}.`;
  statsText.textContent = `Bước đi: ${stepCount}, Đã duyệt: ${result.visitedOrder.length}, Thời gian: ${elapsed} ms, ${goalType}: (${result.exit[0]}, ${result.exit[1]})`;
}

generateBtn.addEventListener("click", resetMaze);
solveBtn.addEventListener("click", solveMaze);

canvas.width = COLS * CELL_SIZE;
canvas.height = ROWS * CELL_SIZE;
resetMaze();
