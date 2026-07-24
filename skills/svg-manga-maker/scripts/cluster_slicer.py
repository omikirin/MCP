#!/usr/bin/env python3
"""連結グループ方式スライサー: パスの近接クラスタ→セル帰属→タイト切り出し
usage: python3 cluster_slicer.py <sheet.svg> <manifest.json> <sheet_index> [outdir]
env: STROKE_W(線幅,2.6) MERGE_GAP(連結判定の許容距離px,6) PAD(切出余白px,8)
"""
import json,sys,os,re
svg_path,mani,idx=sys.argv[1],sys.argv[2],int(sys.argv[3])
outdir=sys.argv[4] if len(sys.argv)>4 else "vectors_svg"
SW=float(os.environ.get("STROKE_W","2.6"))
GAP=float(os.environ.get("MERGE_GAP","6"))
PAD=float(os.environ.get("PAD","8"))
os.makedirs(outdir,exist_ok=True)
m=json.load(open(mani)); cols,rows=m["cols"],m["rows"]
ids=m["sheets"][idx-1]["cell_ids"]
src=open(svg_path).read()
src=re.sub(r'stroke-width="[\d.]+"',f'stroke-width="{SW}"',src)
mvb=re.search(r'viewBox="([\d.\s-]+)"',src)
if mvb: X0,Y0,W,H=map(float,mvb.group(1).split())
else:
    X0,Y0=0.0,0.0
    W=float(re.search(r'width="([\d.]+)',src).group(1))
    H=float(re.search(r'height="([\d.]+)',src).group(1))
gm=re.search(r'(<g[^>]*>)',src); gopen=gm.group(1) if gm else ""
paths=re.findall(r'<path[^>]*/>|<path[^>]*>.*?</path>',src,flags=re.S)
# Mコマンド区切りでサブパスに分解(vtracer等の複合パス対応)
_exploded=[];_origin=[];_dpart=[];_tmpl=[]
for pi,p in enumerate(paths):
    dm=re.search(r'd="([^"]*)"',p)
    attrs=p[:dm.start(1)-3]+'d="{D}"'+p[dm.end(1)+1:]
    _tmpl.append(attrs)
    subs=[x for x in re.split(r'(?=M)',dm.group(1)) if x.strip()]
    for sd in subs:
        _exploded.append(attrs.replace("{D}",sd.strip()))
        _origin.append(pi); _dpart.append(sd.strip())
paths=_exploded
def bbox(p):
    nums=[float(n) for n in re.findall(r'-?\d+\.?\d*',re.search(r'd="([^"]*)"',p).group(1))]
    xs,ys=nums[0::2],nums[1::2]
    tx,ty=0.0,0.0
    tm=re.search(r'translate\(([-\d.]+)[,\s]+([-\d.]+)\)',p)
    if tm: tx,ty=float(tm.group(1)),float(tm.group(2))
    return [min(xs)+tx,min(ys)+ty,max(xs)+tx,max(ys)+ty]
BB=[bbox(p) for p in paths]
# キャンバスの25%超を覆う背景パスを除外
keepi=[i for i,b in enumerate(BB) if (b[2]-b[0])*(b[3]-b[1])<0.25*W*H]
paths=[paths[i] for i in keepi]; BB=[BB[i] for i in keepi]
# union-find
par=list(range(len(paths)))
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
def touch(a,b):
    return not(a[2]+GAP<b[0] or b[2]+GAP<a[0] or a[3]+GAP<b[1] or b[3]+GAP<a[1])
order=sorted(range(len(paths)),key=lambda i:BB[i][0])
for ii in range(len(order)):
    i=order[ii]
    for jj in range(ii+1,len(order)):
        j=order[jj]
        if BB[j][0]>BB[i][2]+GAP: break
        if touch(BB[i],BB[j]):
            ra,rb=find(i),find(j)
            if ra!=rb: par[rb]=ra
clusters={}
for i in range(len(paths)):
    clusters.setdefault(find(i),[]).append(i)
CL=[{"m":v} for v in clusters.values()]
def cbb(c):
    xs=[BB[i][0] for i in c["m"]]+[BB[i][2] for i in c["m"]]
    ys=[BB[i][1] for i in c["m"]]+[BB[i][3] for i in c["m"]]
    return min(xs),min(ys),max(xs),max(ys)
def dist(a,b):
    ax0,ay0,ax1,ay1=cbb(a); bx0,by0,bx1,by1=cbb(b)
    dx=max(bx0-ax1,ax0-bx1,0); dy=max(by0-ay1,ay0-by1,0)
    return (dx*dx+dy*dy)**0.5
TARGET=int(os.environ.get("TARGET",len(ids)))
ids=ids[:TARGET]
if os.environ.get("GRID_FIT"):
    # 行×列のkmeansで各クラスタをセル帰属(密集シート向け)
    from scipy.cluster.vq import kmeans2
    import numpy as np
    cent=np.array([[(cbb(c)[0]+cbb(c)[2])/2,(cbb(c)[1]+cbb(c)[3])/2] for c in CL])
    # 大きいクラスタのみで軸推定(断片は軸を歪める)
    areas=np.array([(cbb(c)[2]-cbb(c)[0])*(cbb(c)[3]-cbb(c)[1]) for c in CL])
    big=areas>np.median(areas)*0.3
    ry,_=kmeans2(cent[big][:,1],rows,minit='++',seed=1)
    rx,_=kmeans2(cent[big][:,0],cols,minit='++',seed=1)
    ry.sort(); rx.sort()
    cell_groups={}
    for c,(cx,cy) in zip(CL,cent):
        r=int(np.argmin(abs(ry-cy))); co=int(np.argmin(abs(rx-cx)))
        cell_groups.setdefault(r*cols+co,[]).extend(c["m"])
    ordered=None
else:
    # 近接順に併合して目標数まで減らす
    while len(CL)>TARGET:
        best=None
        for i in range(len(CL)):
            for j in range(i+1,len(CL)):
                d=dist(CL[i],CL[j])
                if best is None or d<best[0]: best=(d,i,j)
        d,i,j=best
        CL[i]["m"]+=CL[j]["m"]; CL.pop(j)
    CL.sort(key=lambda c:(cbb(c)[1]+cbb(c)[3])/2)
    ordered=[]
    for r in range(rows):
        band=CL[r*cols:(r+1)*cols]
        band.sort(key=lambda c:cbb(c)[0])
        ordered+=band
if ordered is not None:
    cell_groups={i:c["m"] for i,c in enumerate(ordered)}
report=[]
MIN_SIZE=float(os.environ.get("MIN_SIZE","40"))
for i,cid in enumerate(ids):
    mem=cell_groups.get(i,[])
    if not mem:
        report.append(f"MISSING {cid}"); continue
    xs=[BB[k][0] for k in mem]+[BB[k][2] for k in mem]
    ys=[BB[k][1] for k in mem]+[BB[k][3] for k in mem]
    if max(xs)-min(xs)<MIN_SIZE and max(ys)-min(ys)<MIN_SIZE:
        report.append(f"MISSING {cid} (断片のみ・要再発注)"); continue
    xs=[BB[k][0] for k in mem]+[BB[k][2] for k in mem]
    ys=[BB[k][1] for k in mem]+[BB[k][3] for k in mem]
    x,y=min(xs)-PAD,min(ys)-PAD
    w,h=max(xs)-min(xs)+2*PAD,max(ys)-min(ys)+2*PAD
    groups={}
    for k in sorted(mem): groups.setdefault(_origin[k],[]).append(_dpart[k])
    body="\n".join(_tmpl[pi].replace("{D}"," ".join(ds)) for pi,ds in groups.items())
    body=re.sub(r'(\d+\.\d{2})\d+',r'\1',body)  # 座標を小数2桁に丸め(-40%程度)
    out=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}" '
         f'width="{w:.0f}" height="{h:.0f}">\n{gopen}{body}{"</g>" if gopen else ""}</svg>')
    open(os.path.join(outdir,f"{cid}.svg"),"w").write(out)
print(f"{len(clusters)} clusters -> {len([i for i in range(len(ids)) if i in cell_groups])}/{len(ids)} cells")
for r in report: print(" ",r)
