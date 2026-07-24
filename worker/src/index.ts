/**
 * NINJAMCP — CryptoNinja 設定資料 リモートMCPサーバー（Cloudflare Workers版）
 *
 * MCP Streamable HTTP トランスポート（ステートレス）を依存ライブラリなしで実装。
 * エンドポイント: POST /mcp
 */
import charactersData from "../../data/characters.json";
import worldview from "../../data/worldview.json";

interface Character {
  id: string;
  name: string;
  name_en: string;
  clan: string;
  ninjutsu: string | null;
  weapon: string | null;
  birthday: string | null;
  profile: string | null;
  relations: string | null;
  notes: string | null;
}

const { image_base_url: IMAGE_BASE, characters } = charactersData as {
  image_base_url: string;
  characters: Character[];
};

const SERVER_INFO = { name: "NINJAMCP", version: "1.0.0" };
const SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"];

// ---------- ドメインロジック（stdio版 src/index.ts と同一） ----------

function num(id: string): string {
  return id.replace("#", "");
}

function imageUrls(c: Character) {
  return {
    image_url: `${IMAGE_BASE}/${num(c.id)}.jpg`,
    image_url_3d: `${IMAGE_BASE}/3d/${num(c.id)}.jpg`,
  };
}

function summary(c: Character) {
  const { id, name, name_en, clan, ninjutsu, weapon } = c;
  return { id, name, name_en, clan, ninjutsu, weapon, ...imageUrls(c) };
}

function findCharacters(query: string): Character[] {
  const q = query.trim().toLowerCase();
  const idMatch = q.match(/^#?(\d{1,3})$/);
  if (idMatch) {
    const id = `#${idMatch[1].padStart(3, "0")}`;
    return characters.filter((c) => c.id === id);
  }
  const exact = characters.filter(
    (c) => c.name.toLowerCase() === q || c.name_en.toLowerCase() === q,
  );
  if (exact.length > 0) return exact;
  return characters.filter(
    (c) => c.name.toLowerCase().includes(q) || c.name_en.toLowerCase().includes(q),
  );
}

type ToolResult = { content: unknown[]; isError?: boolean };

function json(data: unknown): ToolResult {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
}

async function callTool(name: string, args: Record<string, unknown>): Promise<ToolResult> {
  switch (name) {
    case "list_characters": {
      const clan = args.clan as string | undefined;
      const list = clan ? characters.filter((c) => c.clan === clan) : characters;
      return json({ count: list.length, characters: list.map(summary) });
    }
    case "get_character": {
      const query = String(args.query ?? "");
      const found = findCharacters(query);
      if (found.length === 0) {
        return json({
          count: 0,
          characters: [],
          message: `「${query}」に該当するキャラクターが見つかりませんでした。`,
        });
      }
      return json({
        count: found.length,
        characters: found.map((c) => ({ ...c, ...imageUrls(c) })),
      });
    }
    case "get_character_image": {
      const query = String(args.query ?? "");
      const style = args.style === "3d" ? "3d" : "2d";
      const found = findCharacters(query);
      if (found.length === 0) {
        return json({ message: `「${query}」に該当するキャラクターが見つかりませんでした。` });
      }
      const c = found[0];
      const urls = imageUrls(c);
      const url = style === "3d" ? urls.image_url_3d : urls.image_url;
      const res = await fetch(url);
      if (!res.ok) {
        return json({ message: `画像の取得に失敗しました（${res.status}）`, url });
      }
      const buf = new Uint8Array(await res.arrayBuffer());
      let binary = "";
      const CHUNK = 0x8000;
      for (let i = 0; i < buf.length; i += CHUNK) {
        binary += String.fromCharCode(...buf.subarray(i, i + CHUNK));
      }
      return {
        content: [
          {
            type: "text",
            text: `${c.id} ${c.name}（${c.name_en}）の${style === "3d" ? "3Dモデル" : "イラスト"}画像`,
          },
          { type: "image", data: btoa(binary), mimeType: "image/jpeg" },
        ],
      };
    }
    case "get_worldview": {
      const section = (args.section as string | undefined) ?? "all";
      const wv = worldview as Record<string, unknown>;
      if (section === "all") return json(wv);
      return json({ [section]: wv[section], source: wv.source });
    }
    case "search_lore": {
      const query = String(args.query ?? "");
      const q = query.trim().toLowerCase();
      const characterHits = characters
        .map((c) => {
          const fields: [string, string | null][] = [
            ["name", c.name],
            ["name_en", c.name_en],
            ["clan", c.clan],
            ["ninjutsu", c.ninjutsu],
            ["weapon", c.weapon],
            ["birthday", c.birthday],
            ["profile", c.profile],
            ["relations", c.relations],
            ["notes", c.notes],
          ];
          const matched = fields.filter(([, v]) => v?.toLowerCase().includes(q));
          if (matched.length === 0) return null;
          return { ...summary(c), matched_fields: Object.fromEntries(matched) };
        })
        .filter((h) => h !== null);

      const worldviewHits: { section: string; text: string }[] = [];
      for (const [key, value] of Object.entries(worldview as Record<string, unknown>)) {
        const text = typeof value === "string" ? value : JSON.stringify(value);
        if (text.toLowerCase().includes(q)) {
          worldviewHits.push({
            section: key,
            text: text.length > 500 ? `${text.slice(0, 500)}…` : text,
          });
        }
      }

      return json({
        query,
        character_hits: characterHits,
        worldview_hits: worldviewHits,
        total: characterHits.length + worldviewHits.length,
      });
    }
    default:
      throw new JsonRpcError(-32602, `Unknown tool: ${name}`);
  }
}

// ---------- ツール定義（tools/list） ----------

const TOOLS = [
  {
    name: "list_characters",
    description:
      "CryptoNinjaの全キャラクター一覧を返す。clanを指定するとそのクラン所属のみに絞り込む。",
    inputSchema: {
      type: "object",
      properties: {
        clan: {
          type: "string",
          enum: ["伊賀", "甲賀", "風魔", "雑賀", "天界", "根の国"],
          description: "絞り込むクラン名（伊賀・甲賀・風魔・雑賀・天界・根の国）",
        },
      },
    },
  },
  {
    name: "get_character",
    description:
      "キャラクター名（日本語名・英名）またはID（#012等）を指定して、そのキャラの完全な設定（プロフィール・忍術・武器・誕生日・関係性・備考）を返す。",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "キャラ名またはID。例: '咲耶' 'Shion' '#031' '12'" },
      },
      required: ["query"],
    },
  },
  {
    name: "get_character_image",
    description:
      "キャラクター名またはIDを指定して、そのキャラの公式イラスト画像を返す。styleで2Dイラスト版か3Dモデル版かを選べる。",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "キャラ名またはID。例: '咲耶' 'Shion' '#031'" },
        style: {
          type: "string",
          enum: ["2d", "3d"],
          description: "画像スタイル。省略時は 2d（イラスト版）",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "get_worldview",
    description:
      "CryptoNinjaの世界観を返す。シーズン時系列・4クランと天界/根の国の相関・各クランの特徴・未確定設定メモ（創作の余白）・二次創作ガイドラインの案内を含む。",
    inputSchema: {
      type: "object",
      properties: {
        section: {
          type: "string",
          enum: [
            "overview",
            "seasons",
            "clans",
            "relations_map",
            "unconfirmed_notes",
            "guidelines_note",
            "all",
          ],
          description: "取得するセクション。省略時は all（全部）",
        },
      },
    },
  },
  {
    name: "search_lore",
    description:
      "キーワードでキャラ設定・世界観テキストを横断全文検索する。忍術名・武器・関係性・設定の断片から該当キャラや設定箇所を探すときに使う。",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "検索キーワード。例: '双子' '刀' '天狗'" },
      },
      required: ["query"],
    },
  },
];

// ---------- JSON-RPC / Streamable HTTP ----------

class JsonRpcError extends Error {
  constructor(
    public code: number,
    message: string,
  ) {
    super(message);
  }
}

interface JsonRpcRequest {
  jsonrpc: "2.0";
  id?: number | string | null;
  method: string;
  params?: Record<string, unknown>;
}

async function handleRpc(req: JsonRpcRequest): Promise<unknown> {
  const params = req.params ?? {};
  switch (req.method) {
    case "initialize": {
      const requested = String(params.protocolVersion ?? "");
      const protocolVersion = SUPPORTED_VERSIONS.includes(requested)
        ? requested
        : SUPPORTED_VERSIONS[0];
      return {
        protocolVersion,
        capabilities: { tools: {} },
        serverInfo: SERVER_INFO,
        instructions:
          "CryptoNinjaのキャラクター設定・世界観を提供するサーバーです。キャラについて聞かれたら get_character、設定の断片から探すときは search_lore を使ってください。",
      };
    }
    case "ping":
      return {};
    case "tools/list":
      return { tools: TOOLS };
    case "tools/call": {
      const name = String(params.name ?? "");
      const args = (params.arguments ?? {}) as Record<string, unknown>;
      try {
        return await callTool(name, args);
      } catch (e) {
        if (e instanceof JsonRpcError) throw e;
        return {
          content: [{ type: "text", text: `エラー: ${e instanceof Error ? e.message : e}` }],
          isError: true,
        };
      }
    }
    case "resources/list":
      return { resources: [] };
    case "prompts/list":
      return { prompts: [] };
    default:
      throw new JsonRpcError(-32601, `Method not found: ${req.method}`);
  }
}

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id, MCP-Protocol-Version, Authorization",
  "Access-Control-Expose-Headers": "Mcp-Session-Id",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

async function handleMcp(request: Request): Promise<Response> {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }
  if (request.method === "GET") {
    // ステートレス実装のため SSE ストリームは提供しない
    return jsonResponse(
      { jsonrpc: "2.0", error: { code: -32000, message: "SSE not supported; use POST" }, id: null },
      405,
    );
  }
  if (request.method === "DELETE") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }
  if (request.method !== "POST") {
    return jsonResponse(
      { jsonrpc: "2.0", error: { code: -32000, message: "Method Not Allowed" }, id: null },
      405,
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(
      { jsonrpc: "2.0", error: { code: -32700, message: "Parse error" }, id: null },
      400,
    );
  }

  const messages = Array.isArray(body) ? body : [body];
  const responses: unknown[] = [];

  for (const msg of messages as JsonRpcRequest[]) {
    if (!msg || msg.jsonrpc !== "2.0" || typeof msg.method !== "string") {
      responses.push({
        jsonrpc: "2.0",
        error: { code: -32600, message: "Invalid Request" },
        id: (msg as JsonRpcRequest)?.id ?? null,
      });
      continue;
    }
    const isNotification = msg.id === undefined || msg.id === null;
    if (isNotification) continue; // notifications/initialized など
    try {
      const result = await handleRpc(msg);
      responses.push({ jsonrpc: "2.0", id: msg.id, result });
    } catch (e) {
      const code = e instanceof JsonRpcError ? e.code : -32603;
      const message = e instanceof Error ? e.message : "Internal error";
      responses.push({ jsonrpc: "2.0", id: msg.id, error: { code, message } });
    }
  }

  if (responses.length === 0) {
    return new Response(null, { status: 202, headers: CORS_HEADERS });
  }
  return jsonResponse(Array.isArray(body) ? responses : responses[0]);
}

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/mcp" || url.pathname === "/mcp/") {
      return handleMcp(request);
    }
    if (url.pathname === "/") {
      return jsonResponse({
        name: SERVER_INFO.name,
        version: SERVER_INFO.version,
        description: "CryptoNinja 設定資料 MCP サーバー",
        mcp_endpoint: "/mcp",
        tools: TOOLS.map((t) => t.name),
      });
    }
    return jsonResponse({ error: "Not Found" }, 404);
  },
};
