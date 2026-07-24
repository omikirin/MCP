#!/usr/bin/env python3
"""高精細(Brain級)シート抽出 usage: hires_sheet.py <png> <sheet_idx1-9> <outdir> [skip_ids,comma]"""
import sys,os,re,json
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,idx,outdir=sys.argv[1],int(sys.argv[2]),sys.argv[3]
skip=set(sys.argv[4].split(",")) if len(sys.argv)>4 else set()
ids=json.load(open("sheets/poses_manifest.json"))["sheets"][idx-1]["cell_ids"]
pil=Image.open(png).convert("L")
SC=max(1,8000//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
rprof=ink.mean(axis=1); cprof=ink.mean(axis=0)
for r0 in np.where(rprof>0.35)[0]: ink[max(0,r0-2):r0+3,:]=False
for c0 in np.where(cprof>0.35)[0]: ink[:,max(0,c0-2):c0+3]=False
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
rows,cols=10,5; ch,cw=H/rows,W/cols
cells={}
for i,(s,o) in enumerate(zip(sizes,objs),1):
    if s<600: continue
    cy=(o[0].start+o[0].stop)/2; cx=(o[1].start+o[1].stop)/2
    bh=o[0].stop-o[0].start; bw=o[1].stop-o[1].start
    r=min(int(cy//ch),rows-1); co=min(int(cx//cw),cols-1)
    ly,lx=(cy-r*ch)/ch,(cx-co*cw)/cw
    small=bh<ch*0.14 and bw<cw*0.4
    if small and ((ly<0.24 and lx<0.55) or ly>0.78): continue
    cells.setdefault(r*cols+co,[]).append({"id":i,"bbox":o})
os.makedirs(outdir,exist_ok=True); made=0
for k in range(50):
    cid=ids[k]
    if cid in skip: continue
    mem=cells.get(k,[])
    if not mem: print("empty:",cid); continue
    y0=min(c["bbox"][0].start for c in mem); y1=max(c["bbox"][0].stop for c in mem)
    x0=min(c["bbox"][1].start for c in mem); x1=max(c["bbox"][1].stop for c in mem)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in mem])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),40,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{cid}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=14,corner_threshold=55,length_threshold=3.5)
    s2=open(out).read(); s2=re.sub(r'(\d+\.\d{2})\d+',r'\1',s2)
    w2=float(re.search(r'width="([\d.]+)',s2).group(1)); h2=float(re.search(r'height="([\d.]+)',s2).group(1))
    s2=s2.replace(f'width="{w2:g}"',f'viewBox="0 0 {w2:g} {h2:g}" width="{w2:g}"',1)
    open(out,"w").write(s2); made+=1
print(f"sheet{idx}: {made} cells")
