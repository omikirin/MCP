#!/usr/bin/env python3
"""オノマトペシート抽出: 2行x5列=10語/枚
usage: python3 sfx_extract.py <sheet.png> <辞書開始index(0始まり)> [outdir]
onomatopoeia.json をカレントに置いて実行"""
import sys,os,re,json
import numpy as np
from PIL import Image
from scipy import ndimage
import vtracer
Image.MAX_IMAGE_PIXELS=None
png,off=sys.argv[1],int(sys.argv[2])
outdir=sys.argv[3] if len(sys.argv)>3 else "sfx_lib_raw"
os.makedirs(outdir,exist_ok=True)
words=[x["text"] for x in json.load(open("onomatopoeia.json"))["onomatopoeia"]]
pil=Image.open(png).convert("L")
SC=max(1,3600//pil.width+1)
pil=pil.resize((pil.width*SC,pil.height*SC),Image.LANCZOS)
a=np.array(pil); ink=(a<160); H,W=a.shape
lab,n=ndimage.label(ink,structure=np.ones((3,3)))
sizes=ndimage.sum(ink,lab,range(1,n+1)); objs=ndimage.find_objects(lab)
comps=[{"id":i,"cx":(o[1].start+o[1].stop)/2,"cy":(o[0].start+o[0].stop)/2,"bbox":o}
       for i,(s,o) in enumerate(zip(sizes,objs),1) if s>=150]
ry=np.array([H*0.27,H*0.73]); rx=np.array([W*(c+0.5)/5 for c in range(5)])
cells={}
for c in comps:
    r=int(np.argmin(abs(ry-c["cy"]))); co=int(np.argmin(abs(rx-c["cx"])))
    cells.setdefault(r*5+co,[]).append(c)
for idx in range(10):
    wi=off+idx
    if wi>=len(words): break
    mem=cells.get(idx,[])
    if not mem: print("empty:",words[wi]); continue
    y0=min(c["bbox"][0].start for c in mem); y1=max(c["bbox"][0].stop for c in mem)
    x0=min(c["bbox"][1].start for c in mem); x1=max(c["bbox"][1].stop for c in mem)
    sel=np.isin(lab[y0:y1,x0:x1],[c["id"] for c in mem])
    crop=np.pad(np.where(sel,0,255).astype(np.uint8),20,constant_values=255)
    Image.fromarray(crop).save("/tmp/c.png")
    out=f"{outdir}/{words[wi]}.svg"
    vtracer.convert_image_to_svg_py("/tmp/c.png",out,colormode="binary",mode="spline",filter_speckle=8,corner_threshold=60)
    s2=open(out).read(); s2=re.sub(r'(\d+\.\d{2})\d+',r'\1',s2)
    w2=float(re.search(r'width="([\d.]+)',s2).group(1)); h2=float(re.search(r'height="([\d.]+)',s2).group(1))
    s2=s2.replace(f'width="{w2:g}"',f'viewBox="0 0 {w2:g} {h2:g}" width="{w2:g}"',1)
    open(out,"w").write(s2)
print("done")
