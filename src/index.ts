#!/usr/bin/env node
/**
 * NINJAMCP — CryptoNinja 設定資料 MCP サーバー
 *
 * CryptoNinja のキャラクター設定・世界観をツールとして提供する
 * Model Context Protocol サーバー（stdio トランスポート）。
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

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

const charactersData = JSON.parse(
  readFileSync(join(ROOT, "data", "characters.json"), "utf8"),
) as { image_base_url: string; characters: Character[] };

const worldview = JSON.parse(
  readFileSync(join(ROOT, "data", "worldview.json"), "utf8"),
) as Record<string, unknown>;

const { image_base_url: IMAGE_BASE, characters } = charactersData;

const CLANS = ["伊賀", "甲賀", "風魔", "雑賀", "天界", "根の国"] as const;

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
  // ID 検索: "#012" / "012" / "12"
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

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
  };
}

const server = new McpServer({ name: "NINJAMCP", version: "1.0.0" });

server.registerTool(
  "list_characters",
  {
    description:
      "CryptoNinjaの全キャラクター一覧を返す。clanを指定するとそのクラン所属のみに絞り込む。",
    inputSchema: {
      clan: z
        .enum(CLANS)
        .optional()
        .describe("絞り込むクラン名（伊賀・甲賀・風魔・雑賀・天界・根の国）"),
    },
  },
  async ({ clan }) => {
    const list = clan ? characters.filter((c) => c.clan === clan) : characters;
    return json({ count: list.length, characters: list.map(summary) });
  },
);

server.registerTool(
  "get_character",
  {
    description:
      "キャラクター名（日本語名・英名）またはID（#012等）を指定して、そのキャラの完全な設定（プロフィール・忍術・武器・誕生日・関係性・備考）を返す。",
    inputSchema: {
      query: z.string().describe("キャラ名またはID。例: '咲耶' 'Shion' '#031' '12'"),
    },
  },
  async ({ query }) => {
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
  },
);

server.registerTool(
  "get_character_image",
  {
    description:
      "キャラクター名またはIDを指定して、そのキャラの公式イラスト画像を返す。styleで2Dイラスト版か3Dモデル版かを選べる。",
    inputSchema: {
      query: z.string().describe("キャラ名またはID。例: '咲耶' 'Shion' '#031'"),
      style: z
        .enum(["2d", "3d"])
        .optional()
        .describe("画像スタイル。省略時は 2d（イラスト版）"),
    },
  },
  async ({ query, style }) => {
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
    const data = Buffer.from(await res.arrayBuffer()).toString("base64");
    return {
      content: [
        {
          type: "text" as const,
          text: `${c.id} ${c.name}（${c.name_en}）の${style === "3d" ? "3Dモデル" : "イラスト"}画像`,
        },
        { type: "image" as const, data, mimeType: "image/jpeg" },
      ],
    };
  },
);

server.registerTool(
  "get_worldview",
  {
    description:
      "CryptoNinjaの世界観を返す。シーズン時系列・4クランと天界/根の国の相関・各クランの特徴・未確定設定メモ（創作の余白）・二次創作ガイドラインの案内を含む。",
    inputSchema: {
      section: z
        .enum([
          "overview",
          "seasons",
          "clans",
          "relations_map",
          "unconfirmed_notes",
          "guidelines_note",
          "all",
        ])
        .optional()
        .describe("取得するセクション。省略時は all（全部）"),
    },
  },
  async ({ section }) => {
    if (!section || section === "all") return json(worldview);
    return json({ [section]: worldview[section], source: worldview.source });
  },
);

server.registerTool(
  "search_lore",
  {
    description:
      "キーワードでキャラ設定・世界観テキストを横断全文検索する。忍術名・武器・関係性・設定の断片から該当キャラや設定箇所を探すときに使う。",
    inputSchema: {
      query: z.string().describe("検索キーワード。例: '双子' '刀' '天狗'"),
    },
  },
  async ({ query }) => {
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
        return {
          ...summary(c),
          matched_fields: Object.fromEntries(matched),
        };
      })
      .filter((h) => h !== null);

    const worldviewHits: { section: string; text: string }[] = [];
    for (const [key, value] of Object.entries(worldview)) {
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
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("NINJAMCP server running on stdio");
