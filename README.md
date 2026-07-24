# NINJAMCP

CryptoNinja のキャラクター設定・世界観を AI に提供する **MCP（Model Context Protocol）サーバー** です。

Claude Desktop / Claude Code などの MCP クライアントに接続すると、AI が CryptoNinja 全42キャラの公式設定や世界観を正確に参照しながら、二次創作の相談・ストーリー作成・設定確認などを手伝えるようになります。

## 提供ツール

| ツール | 説明 |
|---|---|
| `list_characters` | 全キャラクター一覧（クラン絞り込み対応：伊賀・甲賀・風魔・雑賀・天界・根の国） |
| `get_character` | 名前（日本語/英語）または ID（`#012` 等）でキャラの完全な設定を取得 |
| `get_character_image` | キャラの公式イラスト画像を取得（2D / 3D 切り替え可） |
| `get_worldview` | 世界観（シーズン時系列・クラン相関・未確定設定メモなど）を取得 |
| `search_lore` | キーワードで全設定テキストを横断全文検索 |

## セットアップ

```bash
npm install
npm run build
```

## MCP クライアントへの登録

### Claude Code

```bash
claude mcp add NINJAMCP -- node /path/to/MCP/dist/index.js
```

### Claude Desktop（claude_desktop_config.json）

```json
{
  "mcpServers": {
    "NINJAMCP": {
      "command": "node",
      "args": ["/path/to/MCP/dist/index.js"]
    }
  }
}
```

## 開発

```bash
npm run dev   # tsx で src/index.ts を直接実行
```

データは `data/characters.json`（キャラ設定）と `data/worldview.json`（世界観）にあり、編集すれば再ビルドなしで反映されます。

## データ出典

- [【保存版】CryptoNinja 世界観とキャラクター設定まとめ（だんく氏）](https://note.com/danku_mj/n/n8be2e96f1fbe)

CryptoNinja は Ninja DAO / イケハヤ氏によるNFTプロジェクトです。二次創作・商用利用の範囲は公式ガイドラインを確認してください。
