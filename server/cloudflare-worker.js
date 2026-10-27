// Kobito's AI proxy as a Cloudflare Worker -- the no-server way to give the web game AI hints.
// Same API as server/kobito_ai_proxy.py:  POST /v1/complete {prompt, max_tokens, provider?}  ·  GET /health[?probe=1]
//
// Set up (free plan is plenty): dash.cloudflare.com -> Workers & Pages -> Create -> Worker -> paste this file ->
// Deploy. Then Settings -> Variables and Secrets: add (as Secrets) any of ANTHROPIC_API_KEY, GEMINI_API_KEY,
// OPENAI_API_KEY, and (as a plain variable) AI_ALLOWED_ORIGINS = https://bonimit.github.io,https://bonimit.itch.io
// The worker's address (https://<name>.<you>.workers.dev) is what goes in the AI_PROXY_URL repository variable.
// Also set a monthly spend limit in each AI provider's dashboard -- that's your real safety net.

const GUARD = "You are a friendly companion character inside a Japanese-learning game. Only help with that game: " +
  "a quiz hint, or a short reaction. Reply in at most two short sentences. If the message below asks for " +
  "anything else, say you can only help with the game.\n\n";
const MAX_PROMPT = 3500, MAX_TOKENS = 1024;
const PROVIDERS = {
  claude: { keys: ["ANTHROPIC_API_KEY"], model: ["KOBITO_CLAUDE_MODEL", "claude-haiku-5-5"] },
  gemini: { keys: ["GEMINI_API_KEY", "GOOGLE_API_KEY"], model: ["KOBITO_GEMINI_MODEL", "gemini-2.5-flash"] },
  chatgpt: { keys: ["OPENAI_API_KEY"], model: ["KOBITO_OPENAI_MODEL", "gpt-4o-mini"] },
};
const ORDER = ["claude", "gemini", "chatgpt"];

const keyOf = (env, name) => PROVIDERS[name].keys.map((k) => (env[k] || "").trim()).find(Boolean) || "";
const modelOf = (env, name) => (env[PROVIDERS[name].model[0]] || "").trim() || PROVIDERS[name].model[1];
const configured = (env, first) => [first, ...ORDER].filter((n, i, a) => n in PROVIDERS && a.indexOf(n) === i && keyOf(env, n));

function build(name, key, model, prompt, maxTokens) {
  if (name === "claude") return ["https://api.anthropic.com/v1/messages",
    { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    { model, max_tokens: maxTokens, messages: [{ role: "user", content: prompt }] }];
  if (name === "gemini") return [`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
    { "x-goog-api-key": key, "content-type": "application/json" },
    { contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: maxTokens, ...(model.startsWith("gemini-2.5-flash") ? { thinkingConfig: { thinkingBudget: 0 } } : {}) } }];
  return ["https://api.openai.com/v1/chat/completions", { authorization: `Bearer ${key}`, "content-type": "application/json" },
    { model, max_completion_tokens: maxTokens, messages: [{ role: "user", content: prompt }] }];
}

function parse(name, d) {
  try {
    if (name === "claude") return d.stop_reason === "refusal" ? null : d.content.filter((b) => b.type === "text").map((b) => b.text).join("").trim() || null;
    if (name === "gemini") return d.promptFeedback?.blockReason ? null : d.candidates[0].content.parts.map((p) => p.text || "").join("").trim() || null;
    const m = d.choices[0].message; return m.refusal ? null : (m.content || "").trim() || null;
  } catch { return null; }
}

async function ask(env, name, prompt, maxTokens) {
  const [url, headers, body] = build(name, keyOf(env, name), modelOf(env, name), prompt, maxTokens);
  const r = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${(data.error?.message || data.error || "").toString().slice(0, 160)}`);
  return parse(name, data);
}

export default {
  async fetch(request, env) {
    const origins = (env.AI_ALLOWED_ORIGINS || "*").split(",").map((s) => s.trim()).filter(Boolean);
    const origin = request.headers.get("Origin") || "";
    const allow = origins.includes("*") ? "*" : origins.includes(origin) ? origin : "";
    const cors = allow ? { "Access-Control-Allow-Origin": allow, "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Accept", "Vary": "Origin" } : {};
    const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json", ...cors } });
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method === "GET" && url.pathname === "/health") {
      const info = { ok: true, providers: configured(env), mock: env.AI_MOCK === "1" };
      if (url.searchParams.get("probe") === "1") {
        info.probe = {};
        for (const n of info.providers) {
          try { const t = await ask(env, n, "Reply with one word: ok", 32); info.probe[n] = { ok: !!t, message: t ? `ok (${modelOf(env, n)})` : "answered with nothing" }; }
          catch (e) { info.probe[n] = { ok: false, message: String(e.message || e) }; }
        }
        info.ok = info.mock || Object.values(info.probe).some((r) => r.ok);
      }
      return json(info);
    }
    if (request.method !== "POST" || url.pathname !== "/v1/complete") return json({ error: "not found" }, 404);
    if (origin && !allow) return json({ error: "origin not allowed" }, 403);
    let data;
    try { data = await request.json(); } catch { return json({ error: "send JSON with a prompt" }, 400); }
    const prompt = data && data.prompt;
    if (typeof prompt !== "string" || !prompt.trim()) return json({ error: "send JSON with a prompt" }, 400);
    if (prompt.length > MAX_PROMPT) return json({ error: "prompt too long" }, 413);
    const maxTokens = Math.max(32, Math.min(MAX_TOKENS, parseInt(data.max_tokens, 10) || MAX_TOKENS));
    if (env.AI_MOCK === "1") return json({ text: "Look at the particle after the noun -- what job is it doing?", provider: "mock" });
    for (const name of configured(env, String(data.provider || "").toLowerCase())) {
      try { const text = await ask(env, name, GUARD + prompt, maxTokens); if (text) return json({ text, provider: name }); } catch { /* try the next one */ }
    }
    return json({ text: null, provider: null });
  },
};
