#!/usr/bin/env python3
"""ネームJSON → 1ページSVGレンダラ v1
usage: python3 render.py name.json out.svg
"""
import json,sys,re,html,os
from vtext import vtext_paths,htext_paths

LAY={l["id"]:l for l in json.load(open("layouts.json"))["layouts"]}
SFX={f'SFX{i:03d}':x for i,x in enumerate(json.load(open("onomatopoeia.json"))["onomatopoeia"],1)}
SFX_BY_TEXT={x["text"]:x for x in SFX.values()}
BG={b["id"]:b for b in json.load(open("backgrounds.json"))["backgrounds"]}

def cell_svg(pose_id):
    try: src=open(f"vectors_svg/{pose_id}.svg").read()
    except FileNotFoundError: return None
    vb=re.search(r'viewBox="([^"]+)"',src).group(1)
    inner=re.sub(r'^.*?<svg[^>]*>','',src,flags=re.S)
    inner=re.sub(r'</svg>\s*$','',inner,flags=re.S)
    return vb,inner

def effect_bg(x,y,w,h,name):
    cx,cy=x+w/2,y+h/2
    if "集中線" in name or "フラッシュ" in name:
        import math
        L=[]
        for i in range(72):
            a=i*math.pi/36
            r1=max(w,h)*0.18 if "集中線" in name else max(w,h)*0.30
            r2=max(w,h)
            wd=2.5 if i%2 else 1.2
            L.append(f'<line x1="{cx+r1*math.cos(a):.1f}" y1="{cy+r1*math.sin(a):.1f}" x2="{cx+r2*math.cos(a):.1f}" y2="{cy+r2*math.sin(a):.1f}" stroke="black" stroke-width="{wd}"/>')
        return "".join(L)
    if "スピード" in name:
        return "".join(f'<line x1="{x}" y1="{y+h*(i/22):.1f}" x2="{x+w}" y2="{y+h*(i/22):.1f}" stroke="black" stroke-width="{1+ (i%3)*0.6}" opacity="0.75"/>' for i in range(1,22))
    if "縦線" in name:
        return "".join(f'<line x1="{x+w*(i/26):.1f}" y1="{y}" x2="{x+w*(i/26):.1f}" y2="{y+h*0.5:.1f}" stroke="black" stroke-width="1"/>' for i in range(1,26))
    return ""

import math as _m
def _shape_path(kind,cx,cy,rx,ry):
    if kind=="角丸":
        return f'<rect x="{cx-rx:.0f}" y="{cy-ry:.0f}" width="{2*rx:.0f}" height="{2*ry:.0f}" rx="{min(rx,ry)*0.3:.0f}" fill="white" stroke="black" stroke-width="2.5"/>'
    if kind=="ひそひそ":
        return f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="white" stroke="black" stroke-width="2" stroke-dasharray="7 6"/>'
    if kind in ("叫び","トゲ"):
        n=14 if kind=="叫び" else 22
        amp=0.28 if kind=="叫び" else 0.2
        pts=[]
        import random; rnd=random.Random(hash(kind)+int(cx))
        for i in range(n*2):
            a=i*_m.pi/n
            r=1+ (amp*(1+rnd.random()*0.4) if i%2 else 0)
            pts.append(f"{cx+rx*r*_m.cos(a):.0f},{cy+ry*r*_m.sin(a):.0f}")
        return f'<polygon points="{" ".join(pts)}" fill="white" stroke="black" stroke-width="2.6"/>'
    if kind=="雲":
        n=12; d=[]
        for i in range(n):
            a0=i*2*_m.pi/n; a1=(i+1)*2*_m.pi/n; am=(a0+a1)/2
            x0,y0=cx+rx*_m.cos(a0),cy+ry*_m.sin(a0)
            x1,y1=cx+rx*_m.cos(a1),cy+ry*_m.sin(a1)
            xm,ym=cx+rx*1.24*_m.cos(am),cy+ry*1.24*_m.sin(am)
            d.append(f"{'M' if i==0 else ''}{x0:.0f} {y0:.0f} Q {xm:.0f} {ym:.0f} {x1:.0f} {y1:.0f}")
        return f'<path d="{" ".join(d)} Z" fill="white" stroke="black" stroke-width="2.4"/>'
    if kind=="震え":
        n=36; pts=[]
        for i in range(n):
            a=i*2*_m.pi/n
            r=1+0.05*_m.sin(a*7)
            pts.append(f"{cx+rx*r*_m.cos(a):.0f},{cy+ry*r*_m.sin(a):.0f}")
        return f'<polygon points="{" ".join(pts)}" fill="white" stroke="black" stroke-width="2.2"/>'
    return f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="white" stroke="black" stroke-width="2.5"/>'

def balloon(x,y,w,h,spec,pos):
    if isinstance(spec,str): text,shape=spec,None
    else: text,shape=spec.get("t",""),spec.get("shape")
    if shape=="雲": shape="標準"
    if shape is None:
        shape="叫び" if ("!" in text or "!" in text) else "標準"
    # コマ基準のスケーリング
    fs=max(24,min(40,h*0.075))
    def layout(fs):
        maxch=max(3,int((h*0.62)/(fs*1.12)))
        if "\n" in text: cols=text.split("\n")
        else: cols=[text[i:i+maxch] for i in range(0,len(text),maxch)]
        ncol=len(cols); nrow=max(len(c) for c in cols)
        tw=ncol*fs*1.30; th=nrow*fs*1.14
        rx=tw/2+fs*0.85; ry=th/2+fs*0.85
        return cols,tw,th,rx,ry
    cols,tw,th,rx,ry=layout(fs)
    # コマに収まらなければ縮小(雲の膨らみ余裕込みで最大86%)
    while (2*ry>h*0.86 or 2*rx>w*0.9) and fs>18:
        fs-=2; cols,tw,th,rx,ry=layout(fs)
    if shape in ("叫び","トゲ"): rx*=1.02; ry*=1.02
    margin=rx*0.28 if shape in ("雲","叫び","トゲ") else 8
    bx=x+w-2*rx-14-(w-2*rx-28)*pos
    bx=max(x+margin, min(bx, x+w-2*rx-margin))
    by=y+12+margin*0.6+ (h*0.06 if pos>0.4 else 0)  # 2個目は少し下げる
    by=min(by, y+h-2*ry-margin*0.6)
    by=max(by, y+8)
    cx,cy=bx+rx,by+ry
    body,_=vtext_paths("\n".join(cols),cx+tw/2-fs*0.62,cy-th/2,fs)
    return _shape_path(shape,cx,cy,rx,ry)+body

def sfx_el(x,y,w,h,spec,charbox):
    o=SFX_BY_TEXT.get(spec["text"],{"placement":"near_subject","intensity":3})
    inten=spec.get("intensity",o["intensity"])
    base_fs=18+inten*13
    def box(tx,ty,fs):
        tw,th=fs*max(2,len(spec["text"]))*0.62,fs*1.6
        return (tx-tw/2,ty-th*0.75,tx+tw/2,ty+th*0.45)
    def overlaps(b):
        if not charbox: return False
        return not(b[2]<charbox[0] or b[0]>charbox[2] or b[3]<charbox[1] or b[1]>charbox[3])
    def inside(b):
        return b[0]>=x+4 and b[2]<=x+w-4 and b[1]>=y+4 and b[3]<=y+h-4
    # 候補: 四隅・辺・上部中央(placementの好みを先頭に)
    pref={"center_back":[(0.5,0.16,-6)],"edge":[(0.14,0.3,-90),(0.86,0.3,90)]}.get(o["placement"],[])
    cands=pref+[(0.2,0.78,-12),(0.8,0.78,12),(0.16,0.24,-10),(0.84,0.24,10),
       (0.5,0.14,-6),(0.12,0.5,-90),(0.88,0.5,90),(0.5,0.9,-4)]
    fs=base_fs
    while fs>=16:
        for px,py,rot in cands:
            tx,ty=x+w*px,y+h*py
            b=box(tx,ty,fs)
            if inside(b) and not overlaps(b):
                return ("front",_sfx_text(tx,ty,rot,fs,spec["text"]))
        fs*=0.82
    # 最後の手段: 最小サイズでコマ右上(キャラ回避不能でも重ねない=省略)
    return ("front","")

def _sfx_text(tx,ty,rot,fs,text):
    try:
        src=open(f"sfx_lib/{text}.svg").read()
        vb=re.search(r'viewBox="([^"]+)"',src).group(1)
        inner=re.sub(r'^.*?<svg[^>]*>','',src,flags=re.S)
        inner=re.sub(r'</svg>\s*$','',inner,flags=re.S)
        vbv=list(map(float,vb.split()))
        ar=vbv[2]/vbv[3]
        hh=fs*2.1; ww=hh*ar
        return (f'<g transform="rotate({rot} {tx} {ty})">'
                f'<svg x="{tx-ww/2:.0f}" y="{ty-hh*0.6:.0f}" width="{ww:.0f}" height="{hh:.0f}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet">{inner}</svg></g>')
    except FileNotFoundError:
        body=htext_paths(text,tx-fs*len(text)*0.5,ty,fs)
        return f'<g transform="rotate({rot} {tx} {ty})">{body}</g>' 


EXPR=json.load(open("expressions.json"))
EXPR_SEQ={q["id"]:q for q in EXPR["sequences"]}
def expr_cell(eid):
    sm=EXPR.get("standin_map",{})
    if eid in sm and not os.path.exists(f"vectors_expr/{eid}.svg"):
        cs=cell_svg(sm[eid])
        if cs: return cs
    try:
        src=open(f"vectors_expr/{eid}.svg").read()
        vb=re.search(r'viewBox="([^"]+)"',src).group(1)
        inner=re.sub(r'^.*?<svg[^>]*>','',src,flags=re.S)
        inner=re.sub(r'</svg>\s*$','',inner,flags=re.S)
        return vb,inner
    except FileNotFoundError: return None

def render(name):
    lay=LAY[name["layout_id"]]; W,H=1000,1414
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="white"/>']
    # beat_id指定のパネルを3ステップに展開
    expanded=[]
    for p in name["panels"]:
        if "beat_id" in p:
            seq=EXPR_SEQ[p["beat_id"]]
            for si,eid in enumerate(seq["steps"]):
                q={"expr_id":eid,"beat_desc":seq["step_desc"][si],"background_id":None}
                if si==2:
                    q["serif"]=p.get("serif",[]); q["sfx"]=p.get("sfx",[])
                expanded.append(q)
        else: expanded.append(p)
    name={**name,"panels":expanded}
    for i,(rect,panel) in enumerate(zip(lay["panels"],name["panels"])):
        x,y,w,h=rect["x"],rect["y"],rect["w"],rect["h"]
        cid=f"clip{i}"
        out.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
        out.append(f'<g clip-path="url(#{cid})">')
        bg=panel.get("background_id")
        if bg and bg in BG:
            b=BG[bg]
            import os as _os
            bgf=f"vectors_bg/{bg}.svg"
            if _os.path.exists(bgf):
                bs=open(bgf).read()
                bvb=re.search(r'viewBox="([^"]+)"',bs).group(1)
                binner=re.sub(r'^.*?<svg[^>]*>','',bs,flags=re.S)
                binner=re.sub(r'</svg>\s*$','',binner,flags=re.S)
                out.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{bvb}" preserveAspectRatio="xMidYMid slice">{binner}</svg>')
            elif b["category"]=="演出": out.append(effect_bg(x,y,w,h,b["name_ja"]))
            else: out.append(f'<text x="{x+8}" y="{y+h-8}" font-size="12" fill="#999">[BG:{b["name_ja"]}]</text>')
        eid=panel.get("expr_id")
        if eid:
            ec=expr_cell(eid)
            if ec:
                vb3,inner3=ec
                ew,eh=w*0.8,h*0.86
                ex,ey=x+(w-ew)/2,y+(h-eh)/2
                out.append(f'<svg x="{ex:.0f}" y="{ey:.0f}" width="{ew:.0f}" height="{eh:.0f}" viewBox="{vb3}" preserveAspectRatio="xMidYMid meet">{inner3}</svg>')
            else:
                out.append(f'<circle cx="{x+w/2}" cy="{y+h*0.42}" r="{min(w,h)*0.26}" fill="none" stroke="#999" stroke-dasharray="6 5" stroke-width="2"/>')
                out.append(f'<text x="{x+w/2}" y="{y+h*0.8}" text-anchor="middle" font-size="15" fill="#999">[{eid} {panel.get("beat_desc","")}]</text>')
        charbox=None; pose_frag=""
        specs=panel.get("chars")
        if not specs:
            if panel.get("pose_id"): specs=[{"pose_id":panel["pose_id"],"x":panel.get("pose_x",0.5)}]
            else: specs=[]
        frags=[]
        for cs in specs:
            pid=cs.get("pose_id")
            cdir=cs.get("char")  # 例 "006_oto" 指定でキャラ切替
            path=f"characters/{cdir}/poses/{pid}.svg" if cdir else None
            cell=None
            if path and os.path.exists(path):
                src2=open(path).read()
                vbm=re.search(r'viewBox="([^"]+)"',src2).group(1)
                inn=re.sub(r'^.*?<svg[^>]*>','',src2,flags=re.S); inn=re.sub(r'</svg>\s*$','',inn,flags=re.S)
                cell=(vbm,inn)
            else:
                cell=cell_svg(pid)
            if not cell:
                frags.append(f'<text x="{x+w/2}" y="{y+h/2}" text-anchor="middle" font-size="14" fill="#c00">[{pid} 未納品]</text>')
                continue
            vb2,inner=cell
            vbv=vb2.split(); ar=float(vbv[2])/float(vbv[3])
            sc=cs.get("scale",1.0)
            ph=h*0.92*sc; pw=min(ph*ar,w*0.9)
            px=x+w*cs.get("x",0.5)-pw/2; px=max(x,min(px,x+w-pw)); py=y+h-ph
            cb=(px,py,px+pw,py+ph)
            charbox=(min(charbox[0],cb[0]),min(charbox[1],cb[1]),max(charbox[2],cb[2]),max(charbox[3],cb[3])) if charbox else cb
            frag=f'<svg x="{px:.0f}" y="{py:.0f}" width="{pw:.0f}" height="{ph:.0f}" viewBox="{vb2}" preserveAspectRatio="xMidYMax meet">{inner}</svg>'
            if cs.get("flip"):
                frag=f'<g transform="translate({2*px+pw:.0f},0) scale(-1,1)">{frag}</g>'
            frags.append(frag)
        pose_frag="".join(frags)
        backs=[];fronts=[]
        for sfx in panel.get("sfx",[]):
            layer,frag=sfx_el(x,y,w,h,sfx,charbox)
            (backs if layer=="back" else fronts).append(frag)
        out+=backs
        out.append(pose_frag)
        out+=fronts
        for j,sp in enumerate(panel.get("serif",[])):
            out.append(balloon(x,y,w,h,sp,j*0.9))
        out.append('</g>')
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="black" stroke-width="3"/>')
    out.append('</svg>')
    return "".join(out)

name=json.load(open(sys.argv[1]))
open(sys.argv[2],"w").write(render(name))
print("rendered ->",sys.argv[2])
