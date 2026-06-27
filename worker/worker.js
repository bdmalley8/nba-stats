/**
 * NBA Stats — shared favorites sync Worker.
 *
 * Stores one shared favorites list as `favorites.json` on the repo's `data`
 * branch, via the GitHub Contents API. The GitHub token lives ONLY here as a
 * Worker secret (GH_TOKEN) — never in the public app.
 *
 *   GET  /  -> { players: [...], teams: [...] }
 *   POST /  with { players, teams }  -> saves and returns the stored list
 *
 * Config (wrangler.jsonc vars): REPO, BRANCH, FILE_PATH, ALLOW_ORIGIN
 * Secret: GH_TOKEN  (fine-grained PAT, Contents: Read and write on the repo)
 */

const GH = "https://api.github.com";

function cors(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOW_ORIGIN || "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}
function json(body, env, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...cors(env) },
  });
}

function ghHeaders(env) {
  return {
    "Authorization": `Bearer ${env.GH_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "nba-stats-sync-worker",
  };
}

// Keep only sane string ids, deduped and capped — basic abuse guard.
function clean(arr) {
  if (!Array.isArray(arr)) return [];
  const seen = new Set();
  for (const v of arr) {
    const s = String(v).slice(0, 24);
    if (/^[A-Za-z0-9_-]+$/.test(s)) seen.add(s);
    if (seen.size >= 300) break;
  }
  return [...seen];
}

async function readFile(env) {
  const url = `${GH}/repos/${env.REPO}/contents/${env.FILE_PATH}?ref=${env.BRANCH}`;
  const r = await fetch(url, { headers: ghHeaders(env) });
  if (r.status === 404) return { data: { players: [], teams: [] }, sha: null };
  if (!r.ok) throw new Error(`read ${r.status}`);
  const meta = await r.json();
  let data = { players: [], teams: [] };
  try { data = JSON.parse(atob((meta.content || "").replace(/\n/g, ""))); } catch {}
  return { data, sha: meta.sha };
}

async function writeFile(env, data, sha) {
  const url = `${GH}/repos/${env.REPO}/contents/${env.FILE_PATH}`;
  const body = {
    message: "Update shared favorites",
    content: btoa(JSON.stringify(data, null, 2)),
    branch: env.BRANCH,
  };
  if (sha) body.sha = sha;
  const r = await fetch(url, { method: "PUT", headers: ghHeaders(env), body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`write ${r.status} ${await r.text()}`);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(env) });
    try {
      if (request.method === "GET") {
        const { data } = await readFile(env);
        return json({ players: clean(data.players), teams: clean(data.teams) }, env);
      }
      if (request.method === "POST") {
        const incoming = await request.json().catch(() => ({}));
        const data = { players: clean(incoming.players), teams: clean(incoming.teams) };
        const { sha } = await readFile(env);   // current sha for a safe update
        await writeFile(env, data, sha);
        return json(data, env);
      }
      return json({ error: "method not allowed" }, env, 405);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, env, 502);
    }
  },
};
