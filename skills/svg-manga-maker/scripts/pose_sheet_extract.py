#!/usr/bin/env python3
"""ポーズシート汎用抽出(罫線・番号あり対応版)
usage: python3 pose_sheet_extract.py <sheet.png> <シート番号> [outdir]
対応: 罫線(インク率プロファイル除去) / 番号が上または下 / 低解像度アップスケール
処理後は masker.py を通して characters/<slug>/poses/ へ"""
import sys,os,re,json
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,sheet_idx=sys.argv[1],int(sys.argv[2])
mani=json.load(open("sheets/poses_manifest.json"))
ids=mani["sheets"][sheet_idx-1]["cell_ids"]
outdir=sys.argv[3] if len(sys.argv)>3 else f"work/s{sheet_idx:02d}"; os.makedirs(outdir,exist_ok=True)
pil=Image.open(png).convert("L")
SC=max(1,3600//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
# 罫線除去: 長い水平/垂直ラン(幅の45%以上)をモルフォロジで検出して消す
# 高速罫線除去: インク率の高い行/列を消す
rprof=ink.mean(axis=1); cprof=ink.mean(axis=0)
bad_r=np.where(rprof>0.35)[0]; bad_c=np.where(cprof>0.35)[0]
for r0 in bad_r: ink[max(0,r0-2):r0+3,:]=False
for c0 in bad_c: ink[:,max(0,c0-2):c0+3]=False
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
rows,cols=10,5
ch,cw=H/rows,W/cols
cells={}
dropped=0
for i,(s,o) in enumerate(zip(sizes,objs),1):
    if s<250: continue
    cy=(o[0].start+o[0].stop)/2; cx=(o[1].start+o[1].stop)/2
    bh=o[0].stop-o[0].start; bw=o[1].stop-o[1].start
    r=min(int(cy//ch),rows-1); co=min(int(cx//cw),cols-1)
    ly=(cy-r*ch)/ch; lx=(cx-co*cw)/cw
    # 番号除去: 小型かつ (上部22%かつ左半分) or (下部20%付近の中央帯)
    small=bh<ch*0.14 and bw<cw*0.4
    if small and ((ly<0.24 and lx<0.55) or (ly>0.78)):
        dropped+=1; continue
    cells.setdefault(r*cols+co,[]).append({"id":i,"bbox":o})
made=0
for idx in range(50):
    mem=cells.get(idx,[])
    if not mem: print("empty:",ids[idx]); continue
    y0=min(c["bbox"][0].start for c in mem); y1=max(c["bbox"][0].stop for c in mem)
    x0=min(c["bbox"][1].start for c in mem); x1=max(c["bbox"][1].stop for c in mem)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in mem])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),30,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{ids[idx]}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=12,corner_threshold=60)
    s2=open(out).read(); s2=re.sub(r'(\d+\.\d{2})\d+',r'\1',s2)
    w2=float(re.search(r'width="([\d.]+)',s2).group(1)); h2=float(re.search(r'height="([\d.]+)',s2).group(1))
    s2=s2.replace(f'width="{w2:g}"',f'viewBox="0 0 {w2:g} {h2:g}" width="{w2:g}"',1)
    open(out,"w").write(s2); made+=1
print(f"sheet{sheet_idx}: {made}/50 cells, 番号除去{dropped}")
