"""縦書きテキスト→SVGパス変換(フォント非依存埋め込み)"""
from fontTools.ttLib import TTFont, TTCollection
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
import functools

_tc=TTCollection("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc")
FONT=None
for f in _tc.fonts:
    name=f["name"].getDebugName(1) or ""
    if "JP" in name: FONT=f; break
FONT=FONT or _tc.fonts[0]
UPM=FONT["head"].unitsPerEm
CMAP=FONT.getBestCmap()
GS=FONT.getGlyphSet()
ROT90=set("ー〜…‥「」『』()()[]-―=~")  # 縦組みで90度回転する字
SMALL=set("っゃゅょぁぃぅぇぉッャュョァィゥェォ")

@functools.lru_cache(maxsize=512)
def glyph_path(ch,rot):
    gname=CMAP.get(ord(ch))
    if not gname: return None,0
    g=GS[gname]
    pen=SVGPathPen(GS)
    if rot:
        tp=TransformPen(pen,Transform().rotate(-3.14159/2).translate(-UPM*0.5,UPM*0.28).translate(UPM*0.5,0).translate(-UPM*0.5,0))
        # 简易: 中心回転
        pen2=SVGPathPen(GS)
        tp=TransformPen(pen2,Transform().translate(UPM*0.5,-UPM*0.28).rotate(-3.14159/2).translate(-UPM*0.5,UPM*0.28))
        g.draw(tp); return pen2.getCommands(),g.width
    g.draw(pen)
    return pen.getCommands(),g.width

def vtext_paths(text,x_right,y_top,fs,line_h=None,col_gap=None):
    """縦書き。x_right=1列目のx中心。戻り値: (svg断片, 使用列数)"""
    lh=line_h or fs*1.12; cg=col_gap or fs*1.28
    cols=text.split("\n")
    out=[]
    for ci,col in enumerate(cols):
        cx=x_right-ci*cg
        y=y_top
        for ch in col:
            d,aw=glyph_path(ch,ch in ROT90)
            if d:
                sc=fs/UPM
                ox=cx-fs/2
                if ch in SMALL: ox+=fs*0.1
                out.append(f'<g transform="translate({ox:.1f},{y+fs*0.88:.1f}) scale({sc:.4f},{-sc:.4f})"><path d="{d}" fill="black"/></g>')
            y+=lh*(0.82 if ch in SMALL else 1.0)
    return "".join(out),len(cols)

def htext_paths(text,x,y,fs,fill="black"):
    """横書き(ラベル用)"""
    out=[];cx=x
    for ch in text:
        d,aw=glyph_path(ch,False)
        if d:
            sc=fs/UPM
            out.append(f'<g transform="translate({cx:.1f},{y:.1f}) scale({sc:.4f},{-sc:.4f})"><path d="{d}" fill="{fill}"/></g>')
        cx+=(aw or UPM)*fs/UPM
    return "".join(out)
