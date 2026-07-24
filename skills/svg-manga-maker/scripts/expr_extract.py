#!/usr/bin/env python3
"""表情ビートシート抽出(9行x5列=45セル)
usage: python3 expr_extract.py <sheet.png> <outdir>
番号除去ルール: 各セルの最大成分(顔)の上端より完全に上にある成分はサイズ不問で全撤去
(顔パーツは必ず顔クラスタに連結しているため誤爆しない)。処理後 masker.py を通す"""
import sys,os,re,shutil
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,outdir=sys.argv[1],sys.argv[2]
ids=[f"EXP{i:03d}" for i in range(1,46)]
pil=Image.open(png).convert("L")
SC=max(1,3600//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
ch,cw=H/9,W/5
cells={}
for i,(s,o) in enumerate(zip(sizes,objs),1):
    if s<200: continue
    cy=(o[0].start+o[0].stop)/2; cx=(o[1].start+o[1].stop)/2
    r=min(int(cy//ch),8); co=min(int(cx//cw),4)
    cells.setdefault(r*5+co,[]).append({"id":i,"size":s,"bbox":o})
shutil.rmtree(outdir,ignore_errors=True); os.makedirs(outdir)
for idx in range(45):
    mem=cells.get(idx,[])
    if not mem: print("empty:",ids[idx]); continue
    main=max(mem,key=lambda c:c["size"])
    top=main["bbox"][0].start
    keep=[c for c in mem if c is main or c["bbox"][0].stop>top]
    y0=min(c["bbox"][0].start for c in keep); y1=max(c["bbox"][0].stop for c in keep)
    x0=min(c["bbox"][1].start for c in keep); x1=max(c["bbox"][1].stop for c in keep)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in keep])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),30,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{ids[idx]}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=10,corner_threshold=60)
    s2=open(out).read(); s2=re.sub(r"(\d+\.\d{2})\d+",r"\1",s2)
    w2=float(re.search(r"width=\"([\d.]+)",s2).group(1)); h2=float(re.search(r"height=\"([\d.]+)",s2).group(1))
    s2=s2.replace(f"width=\"{w2:g}\"",f"viewBox=\"0 0 {w2:g} {h2:g}\" width=\"{w2:g}\"",1)
    open(out,"w").write(s2)
print("45 cells")
