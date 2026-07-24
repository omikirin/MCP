#!/usr/bin/env python3
"""ポーズシート処理パイプライン(確立版)
usage: python3 process_sheet.py <sheet.png|svg> <sheet_index> [expected_count]
  1) PNG: 二値化→vtracerフル解像度トレース / SVG: 線幅正規化
  2) cluster_slicer: 連結クラスタ→読み順ID割当→タイト切り出し
  3) masker: 白シルエット下敷き焼き込み
  4) library/ へ統合、検品用オーバービューPNG生成、レポート出力
"""
import sys,os,subprocess,json,glob,re

src,idx=sys.argv[1],int(sys.argv[2])
expected=sys.argv[3] if len(sys.argv)>3 else None
work=f"work_sheet{idx:02d}"
os.makedirs(work,exist_ok=True); os.makedirs("library",exist_ok=True)

# 1) 入力正規化
if src.lower().endswith(".png"):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS=None
    import numpy as np, vtracer
    pil=Image.open(src).convert("L")
    if pil.width<3000:
        sc=3600//pil.width+1
        pil=pil.resize((pil.width*sc,pil.height*sc),Image.LANCZOS)
    im=np.array(pil)
    dark=(im<128).mean()
    assert 0.01<dark<0.5, f"入力異常: dark={dark:.2%}(黒潰れ/空白の疑い)"
    out=np.where(im<160,0,255).astype("uint8")
    Image.fromarray(out).save(f"{work}/bin.png")
    vtracer.convert_image_to_svg_py(f"{work}/bin.png",f"{work}/sheet.svg",
        colormode="binary",mode="spline",filter_speckle=10,corner_threshold=60)
    sheet=f"{work}/sheet.svg"
else:
    sheet=src

# 2) 切り分け
env=dict(os.environ,MERGE_GAP="0",MIN_SIZE="200",PAD="30")
if expected: env["TARGET"]=expected
r=subprocess.run(["python3","cluster_slicer.py",sheet,"sheets/poses_manifest.json",str(idx),f"{work}/cells"],
    env=env,capture_output=True,text=True)
print(r.stdout,r.stderr)

# 3) マスク焼き込み
subprocess.run(["python3","masker.py",f"{work}/cells",f"{work}/masked"],check=True)

# 4) ライブラリ統合+検品シート
import shutil,math
new=sorted(glob.glob(f"{work}/masked/*.svg"))
added=0
for f in new:
    dst="library/"+os.path.basename(f)
    if not os.path.exists(dst): shutil.copy(f,dst); added+=1
print(f"library新規追加: {added}(既存優先で重複スキップ)")
import cairosvg
from PIL import Image as I, ImageDraw
th=[]
for f in new:
    cairosvg.svg2png(url=f,write_to="/tmp/t.png",output_height=150,background_color="white")
    th.append((os.path.basename(f)[:-4],I.open("/tmp/t.png").convert("RGB")))
cols=9;rows=math.ceil(len(th)/cols);cw=130;chh=180
ov=I.new("RGB",(cols*cw,rows*chh),(255,255,255));d=ImageDraw.Draw(ov)
for i,(n,im2) in enumerate(th):
    rr,cc=divmod(i,cols); im2.thumbnail((cw-8,chh-26))
    ov.paste(im2,(cc*cw+4,rr*chh+2)); d.text((cc*cw+4,rr*chh+chh-20),n,(0,0,0))
ov.save(f"{work}/overview.png")
lib=len(glob.glob("library/*.svg"))
print(f"[sheet{idx:02d}] 取得{len(new)}セル / ライブラリ累計{lib}/450")
print(f"検品: {work}/overview.png")
