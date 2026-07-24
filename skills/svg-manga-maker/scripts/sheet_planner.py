#!/usr/bin/env python3
"""辞書JSON → GPT作画発注シート生成
usage: python3 sheet_planner.py poses|sfx|bg
出力: sheets/<kind>_sheet_NN.txt (GPTに貼るプロンプト) と sheets/manifest.json
"""
import json,sys,os,math

COLS,ROWS=5,10  # 50セル/枚
CELL=340       # 想定px(2048px正方画像を想定した目安)

def load(kind):
    if kind=="poses":
        d=json.load(open("poses.json"))["poses"]
        # アングル違いは同一シートに並べると指示が楽
        return [(p["id"],f'{p["category"]}「{p["name_ja"]}」を{p["angle_ja"]}アングルから。感情:{p["emotion"]}。'
                 +("バストアップ" if p["default_shot"]=="bust" else "寄り(部分アップ)" if p["default_shot"]=="close" else "全身")
                 +("。人物2名" if p["persons"]==2 else "")) for p in d]
    if kind=="sfx":
        d=json.load(open("onomatopoeia.json"))["onomatopoeia"]
        return [(f'SFX{i:03d}_{x["text"]}',f'描き文字「{x["text"]}」({x["meaning"]})。書体イメージ:{x["style"]}。文字のみ、飾り効果込み')
                for i,x in enumerate(d,1)]
    if kind=="bg":
        d=json.load(open("backgrounds.json"))["backgrounds"]
        return [(x["id"],f'背景「{x["name_ja"]}」。必須要素:{"、".join(x["key_elements"])}。人物なし')
                for x in d]
    raise SystemExit("poses|sfx|bg")

kind=sys.argv[1]
items=load(kind)
os.makedirs("sheets",exist_ok=True)
per=COLS*ROWS
n_sheets=math.ceil(len(items)/per)
manifest={"kind":kind,"cols":COLS,"rows":ROWS,"reading":"左上から右へ、行ごと","sheets":[]}
for s in range(n_sheets):
    chunk=items[s*per:(s+1)*per]
    lines=[f"{r*COLS+c+1:02d}. [{chunk[r*COLS+c][0]}] {chunk[r*COLS+c][1]}"
           for r in range((len(chunk)+COLS-1)//COLS) for c in range(COLS) if r*COLS+c<len(chunk)]
    prompt=f"""以下の指示で1枚の画像を作成してください。

【全体ルール】
- {COLS}列×{ROWS}行の配置(格子線は不要)
- ★各カットの間に十分な余白を空ける。絵同士が接触・重なり・はみ出しをしないこと(最重要)
- 机や小道具込みのカットも、隣のカットに一切かからないようカット内に収める
- すべて黒一色の線画(ペン入れ状態)。塗り・トーン・影なし、背景は白
- 同一の頭身・同一のカットサイズで統一(1カット内でキャラを大きく)
- 各カットの左上に通し番号を小さく記載(絵から離して)
- 出力は白背景・高解像度(600DPI相当)

【各カットの内容】
""" + "\n".join(lines)
    fn=f"sheets/{kind}_sheet_{s+1:02d}.txt"
    open(fn,"w").write(prompt)
    manifest["sheets"].append({"file":fn.replace('.txt','.png'),
        "prompt_file":fn,"cell_ids":[c[0] for c in chunk]})
mf=f"sheets/{kind}_manifest.json"
json.dump(manifest,open(mf,"w"),ensure_ascii=False,indent=1)
print(f"{n_sheets} sheets, manifest -> {mf}")
