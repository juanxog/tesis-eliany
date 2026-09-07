"""Paso 4: genera informe.html (página web de resultados) a partir de los JSON. Sin datos identificables."""
import json, os, html, math, re, itertools
os.chdir(os.path.dirname(os.path.abspath(__file__)))
E = json.load(open("eda_resultados.json")); K = json.load(open("cluster_resultados.json")); L = json.load(open("reporte_limpieza.json")); MO = json.load(open("modelo_resultados.json")); XA = json.load(open("xai_resultados.json"))
esc = html.escape
NP, NE = 118, 173

def pfmt(p): return "<0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")
# ---------------- SVG helpers (theme-aware via CSS vars) ----------------
def both(d, m): return f'<div class="ch ch-d">{d}</div><div class="ch ch-m">{m}</div>'
def scrollable(svg): return f'<div class="scroll"><div class="scroll-in">{svg}</div></div>'
def _svg_open(w, h, title): return f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title or "")}">'


def hbar(items, color="--c1", unit="pct", w=640, label_w=210, title=None, total=None):
    items = list(items); rh, pad = 26, 6; h = rh*len(items) + pad*2
    vmax = max(i[unit] for i in items) or 1; bar_w = w - label_w - 150
    d = [_svg_open(w, h, title)]
    for r, it in enumerate(items):
        y = pad + r*rh; bw = max(2, bar_w * it[unit]/vmax); tip = f"{esc(it['cat'])}: {it['pct']}% (n={it['n']})"
        d.append(f'<g class="row" data-tip="{tip}"><rect x="0" y="{y}" width="{w}" height="{rh}" fill="transparent"/>'
                 f'<text x="{label_w-10}" y="{y+rh/2+4}" text-anchor="end" class="lbl">{esc(it["cat"])}</text>'
                 f'<rect x="{label_w}" y="{y+5}" width="{bw:.1f}" height="{rh-10}" rx="3" style="fill:var({color})"/>'
                 f'<text x="{label_w+bw+8:.1f}" y="{y+rh/2+4}" class="val">{it["pct"]}%<tspan class="muted"> · n={it["n"]}</tspan></text></g>')
    d.append('</svg>')
    # móvil: etiqueta arriba, barra debajo
    mw, mrh, mpad = 360, 38, 4; mh = mrh*len(items) + mpad*2; mbar = mw - 96
    m = [_svg_open(mw, mh, title)]
    for r, it in enumerate(items):
        y = mpad + r*mrh; bw = max(2, mbar * it[unit]/vmax); tip = f"{esc(it['cat'])}: {it['pct']}% (n={it['n']})"
        m.append(f'<g class="row" data-tip="{tip}"><rect x="0" y="{y}" width="{mw}" height="{mrh}" fill="transparent"/>'
                 f'<text x="0" y="{y+12}" class="lbl">{esc(it["cat"])}</text>'
                 f'<rect x="0" y="{y+18}" width="{bw:.1f}" height="11" rx="2" style="fill:var({color})"/>'
                 f'<text x="{bw+6:.1f}" y="{y+27}" class="val">{it["pct"]}%<tspan class="muted"> · n={it["n"]}</tspan></text></g>')
    m.append('</svg>')
    return both("\n".join(d), "\n".join(m))

def forest_m(items, key="x", xmin=0.03, xmax=60, ticks=(0.1,0.3,1,3,10,30), title=""):
    w, rh, pad = 360, 54, 6; h = rh*len(items) + pad*2 + 20
    lx, ux = math.log10(xmin), math.log10(xmax); X = lambda v: 6 + (w-12)*(math.log10(max(min(v, xmax), xmin)) - lx)/(ux-lx)
    o = [_svg_open(w, h, title)]
    for t in ticks:
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad}" y2="{h-18}" class="{"ref" if t==1 else "grid"}"/><text x="{X(t):.1f}" y="{h-4}" text-anchor="middle" class="tick">{t}</text>')
    for r, it in enumerate(items):
        y = pad + r*rh; sig = it["p"] < 0.05; col = "--c3" if sig else "--c1"
        q = f' · q={it["q_FDR"]:.3f}' if "q_FDR" in it else ""
        lab = esc(it[key]); ptxt = pfmt(it["p"]).replace("<", "&lt;")
        o.append(f'<g class="row"><rect x="0" y="{y}" width="{w}" height="{rh}" fill="transparent"/>'
                 f'<text x="0" y="{y+13}" class="lbl">{lab}</text>'
                 f'<line x1="{X(it["IC_lo"]):.1f}" x2="{X(it["IC_hi"]):.1f}" y1="{y+28}" y2="{y+28}" style="stroke:var({col})" stroke-width="2"/>'
                 f'<circle cx="{X(it["OR"]):.1f}" cy="{y+28}" r="5" style="fill:var({col});stroke:var(--surface)" stroke-width="2"/>'
                 f'<text x="{w}" y="{y+45}" text-anchor="end" class="val mono">OR {it["OR"]} ({it["IC_lo"]}–{it["IC_hi"]})<tspan class="muted"> p={ptxt}{q}</tspan></text></g>')
    o.append('</svg>'); return "\n".join(o)

def forest(items, w=720, title=""):
    items = [i for i in items if i["OR"] < 100]
    rh, pad, lw, rw = 28, 8, 200, 250
    h = rh*len(items) + pad*2 + 28
    xmin, xmax = math.log10(0.03), math.log10(60); pw = w - lw - rw
    X = lambda v: lw + pw*(math.log10(max(min(v, 60), 0.03)) - xmin)/(xmax-xmin)
    s = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">']
    for t in (0.1, 0.3, 1, 3, 10, 30):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad}" y2="{h-26}" class="grid"/><text x="{X(t):.1f}" y="{h-8}" text-anchor="middle" class="tick">{t}</text>')
    s.append(f'<line x1="{X(1):.1f}" x2="{X(1):.1f}" y1="{pad}" y2="{h-26}" class="ref"/>')
    for r, it in enumerate(items):
        y = pad + r*rh + rh/2; sig = it["p"] < 0.05
        col = "--c3" if sig else "--c1"
        q = f' · q={it["q_FDR"]:.3f}' if "q_FDR" in it else ""
        tip = f"{esc(it['x'])} → {esc(it['y'])}: OR {it['OR']} (IC95% {it['IC_lo']}–{it['IC_hi']}), p={pfmt(it['p']).replace("<","&lt;")} ({it['prueba']}){q}. Expuestas {it['pct_exp']}% vs no expuestas {it['pct_noexp']}%."
        s.append(f'<g class="row" data-tip="{tip}"><rect x="0" y="{y-rh/2}" width="{w}" height="{rh}" fill="transparent"/>'
                 f'<text x="{lw-10}" y="{y+4}" text-anchor="end" class="lbl">{esc(it["x"])}</text>'
                 f'<line x1="{X(it["IC_lo"]):.1f}" x2="{X(it["IC_hi"]):.1f}" y1="{y}" y2="{y}" style="stroke:var({col})" stroke-width="2"/>'
                 f'<circle cx="{X(it["OR"]):.1f}" cy="{y}" r="5" style="fill:var({col});stroke:var(--surface)" stroke-width="2"/>'
                 f'<text x="{w-rw+8}" y="{y+4}" class="val mono">{it["OR"]} ({it["IC_lo"]}–{it["IC_hi"]})<tspan class="muted"> p={pfmt(it["p"]).replace("<","&lt;")}{q}</tspan></text></g>')
    s.append('</svg>'); return both("\n".join(s), forest_m(items, "x", title=title))

def heatmap(labels, values, w=720):
    n = len(labels); lw = 190; cs = (w-lw-10)/n; h = lw + n*cs
    s = [f'<svg class="chart" viewBox="0 0 {w} {h:.0f}" role="img" aria-label="Matriz de V de Cramér">']
    for j, l in enumerate(labels):
        s.append(f'<text transform="translate({lw+j*cs+cs/2:.1f},{lw-6}) rotate(-60)" class="tick" text-anchor="start">{esc(l)}</text>')
    for i, l in enumerate(labels):
        y = lw + i*cs
        s.append(f'<text x="{lw-6}" y="{y+cs/2+4:.1f}" text-anchor="end" class="tick">{esc(l)}</text>')
        for j in range(n):
            v = values[i][j]; op = 0.06 if i == j else min(1, v/0.7)
            tip = f"{esc(labels[i])} × {esc(labels[j])}: V = {v}"
            txt = f'<text x="{lw+j*cs+cs/2:.1f}" y="{y+cs/2+3.5:.1f}" text-anchor="middle" class="cell {"on" if v>0.4 else ""}">{v:.2f}</text>' if (i != j and v >= 0.2) else ""
            s.append(f'<g data-tip="{tip}"><rect x="{lw+j*cs:.1f}" y="{y:.1f}" width="{cs-1:.1f}" height="{cs-1:.1f}" style="fill:var(--c1);fill-opacity:{op:.2f}"/>{txt}</g>')
    s.append('</svg>'); return scrollable("\n".join(s))

def silhouette(res): return both(_silhouette(res), _silhouette(res, 340, 200))
def _silhouette(res, w=520, h=220):
    ks = res["k"]; pad_l, pad_b, pad_t = 44, 30, 10; pw, ph = w-pad_l-12, h-pad_b-pad_t
    ymax = 0.3
    X = lambda k: pad_l + pw*(k-ks[0])/(ks[-1]-ks[0]); Y = lambda v: pad_t + ph*(1-v/ymax)
    s = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Silueta según k">']
    for t in (0, 0.1, 0.2, 0.3):
        s.append(f'<line x1="{pad_l}" x2="{w-12}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{pad_l-6}" y="{Y(t)+4:.1f}" text-anchor="end" class="tick">{t}</text>')
    for k in ks: s.append(f'<text x="{X(k):.1f}" y="{h-8}" text-anchor="middle" class="tick">k={k}</text>')
    for key, col, name in (("sil_pam", "--c1", "PAM"), ("sil_hc", "--c2", "Jerárquico")):
        pts = " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in zip(ks, res[key]) if v is not None)
        s.append(f'<polyline points="{pts}" fill="none" style="stroke:var({col})" stroke-width="2"/>')
        for k, v in zip(ks, res[key]):
            if v is not None: s.append(f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="4" style="fill:var({col});stroke:var(--surface)" stroke-width="1.5" data-tip="{name}, k={k}: silueta {v}"/>')
    s.append(f'<text x="{X(ks[0])+6:.0f}" y="{Y(res["sil_pam"][0])-8:.0f}" class="val" style="fill:var(--c1)">PAM</text><text x="{X(ks[1])+6:.0f}" y="{Y(res["sil_hc"][1])+14:.0f}" class="val" style="fill:var(--c2)">Jerárquico</text></svg>')
    return "\n".join(s)

def scatter(pts): return both(_scatter(pts), _scatter(pts, 340, 300))
def _scatter(pts, w=520, h=400):
    xs = [p["x"] for p in pts]; ys = [p["y"] for p in pts]; pad = 16
    X = lambda x: pad + (w-2*pad)*(x-min(xs))/(max(xs)-min(xs)); Y = lambda y: pad + (h-2*pad)*(1-(y-min(ys))/(max(ys)-min(ys)))
    s = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Pacientes en dos dimensiones (MDS)">']
    for p in pts:
        s.append(f'<circle cx="{X(p["x"]):.1f}" cy="{Y(p["y"]):.1f}" r="5" style="fill:var(--c{p["c"]});stroke:var(--surface)" stroke-width="1.2" data-tip="Clúster {p["c"]}"/>')
    s.append('</svg>'); return "\n".join(s)


def coef_forest(coefs, w=720, title=""):
    items = [c for c in coefs if c["variable"] != "Intercepto"]
    rh, pad, lw, rw = 28, 8, 230, 230; h = rh*len(items)+pad*2+28
    xmin, xmax = math.log10(0.1), math.log10(20); pw = w-lw-rw
    X = lambda v: lw + pw*(math.log10(max(min(v,20),0.1))-xmin)/(xmax-xmin)
    o = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">']
    for t in (0.1,0.3,1,3,10):
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad}" y2="{h-26}" class="grid"/><text x="{X(t):.1f}" y="{h-8}" text-anchor="middle" class="tick">{t}</text>')
    o.append(f'<line x1="{X(1):.1f}" x2="{X(1):.1f}" y1="{pad}" y2="{h-26}" class="ref"/>')
    for r,c in enumerate(items):
        y = pad+r*rh+rh/2; col = "--c3" if c["p"]<0.05 else "--c1"
        tip = f"{esc(c['variable'])}: OR ajustado {c['OR']} (IC95% {c['IC_lo']}–{c['IC_hi']}), p={pfmt(c['p']).replace('<','&lt;')}"
        o.append(f'<g class="row" data-tip="{tip}"><rect x="0" y="{y-rh/2}" width="{w}" height="{rh}" fill="transparent"/><text x="{lw-10}" y="{y+4}" text-anchor="end" class="lbl">{esc(c["variable"])}</text>'
                 f'<line x1="{X(c["IC_lo"]):.1f}" x2="{X(c["IC_hi"]):.1f}" y1="{y}" y2="{y}" style="stroke:var({col})" stroke-width="2"/><circle cx="{X(c["OR"]):.1f}" cy="{y}" r="5" style="fill:var({col});stroke:var(--surface)" stroke-width="2"/>'
                 f'<text x="{w-rw+8}" y="{y+4}" class="val mono">{c["OR"]} ({c["IC_lo"]}–{c["IC_hi"]})<tspan class="muted"> p={pfmt(c["p"]).replace("<","&lt;")}</tspan></text></g>')
    o.append('</svg>'); return both("\n".join(o), forest_m(items, "variable", xmin=0.1, xmax=20, ticks=(0.1,0.3,1,3,10), title=title))

def calib_chart(cal, slope, w=360, h=300):
    pad=40; mx=0.7; X=lambda v: pad+(w-pad-12)*v/mx; Y=lambda v: (h-pad)-(h-pad-12)*v/mx
    o=[f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Calibración">']
    for t in (0,0.2,0.4,0.6):
        o.append(f'<line x1="{pad}" x2="{w-12}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{pad-6}" y="{Y(t)+4:.1f}" text-anchor="end" class="tick">{int(t*100)}%</text>')
        o.append(f'<text x="{X(t):.1f}" y="{h-pad+16}" text-anchor="middle" class="tick">{int(t*100)}%</text>')
    o.append(f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(mx):.1f}" y2="{Y(mx):.1f}" class="ref"/>')
    pts=" ".join(f"{X(c['pred']):.1f},{Y(c['obs']):.1f}" for c in cal)
    o.append(f'<polyline points="{pts}" fill="none" style="stroke:var(--c1)" stroke-width="2"/>')
    for c in cal: o.append(f'<circle cx="{X(c["pred"]):.1f}" cy="{Y(c["obs"]):.1f}" r="5" style="fill:var(--c1);stroke:var(--surface)" stroke-width="2" data-tip="Riesgo predicho {c["pred"]*100:.0f}% · observado {c["obs"]*100:.0f}% · n={c["n"]}"/>')
    o.append(f'<text x="{w/2:.0f}" y="{h-4}" text-anchor="middle" class="tick">riesgo predicho</text><text transform="translate(12,{h/2:.0f}) rotate(-90)" text-anchor="middle" class="tick">abandono observado</text></svg>')
    return "\n".join(o)

def score_chart(est, w=360, h=300):
    pad=40; mx=60; n=len(est); bw=(w-pad-12)/n
    o=[f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Riesgo por puntaje">']
    for t in (0,20,40,60):
        y=(h-pad)-(h-pad-12)*t/mx; o.append(f'<line x1="{pad}" x2="{w-12}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{pad-6}" y="{y+4:.1f}" text-anchor="end" class="tick">{t}%</text>')
    for i,e in enumerate(est):
        x=pad+i*bw+4; bh=(h-pad-12)*e["riesgo_pct"]/mx; y=(h-pad)-bh
        o.append(f'<g data-tip="Puntaje {esc(e["puntaje"])}: {e["riesgo_pct"]}% de abandono (n={e["n"]})"><rect x="{x:.1f}" y="{y:.1f}" width="{bw-8:.1f}" height="{bh:.1f}" rx="3" style="fill:var(--c1)"/>'
                 f'<text x="{x+(bw-8)/2:.1f}" y="{y-6:.1f}" text-anchor="middle" class="val">{e["riesgo_pct"]:.0f}%</text><text x="{x+(bw-8)/2:.1f}" y="{h-pad+16}" text-anchor="middle" class="tick">{esc(e["puntaje"])}</text><text x="{x+(bw-8)/2:.1f}" y="{h-pad+30}" text-anchor="middle" class="tick">n={e["n"]}</text></g>')
    o.append(f'<text x="{w/2:.0f}" y="{h-2}" text-anchor="middle" class="tick">puntaje de riesgo al ingreso</text></svg>'); return "\n".join(o)


def imp_chart(items, w=720):
    rh, pad, lw = 34, 8, 230; h = rh*len(items)+pad*2+22; pw = w-lw-70
    tl = sum(i["shap_logistica"] for i in items); tb = sum(i["shap_bosque"] for i in items)
    items = sorted(items, key=lambda i: -(i["shap_logistica"]/tl + i["shap_bosque"]/tb))
    mx = max(max(i["shap_logistica"]/tl, i["shap_bosque"]/tb) for i in items)
    o=[f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Importancia global">']
    for r,i in enumerate(items):
        y=pad+r*rh; a=i["shap_logistica"]/tl; b=i["shap_bosque"]/tb
        o.append(f'<g class="row" data-tip="{esc(i["variable"])}: {a*100:.0f}% del |SHAP| en la logística, {b*100:.0f}% en el bosque; permutación ΔAUC {i["perm_logistica"]:.3f} / {i["perm_bosque"]:.3f}"><rect x="0" y="{y}" width="{w}" height="{rh}" fill="transparent"/>'
                 f'<text x="{lw-10}" y="{y+rh/2+4}" text-anchor="end" class="lbl">{esc(i["variable"])}</text>'
                 f'<rect x="{lw}" y="{y+4}" width="{pw*a/mx:.1f}" height="11" rx="2" style="fill:var(--c1)"/><text x="{lw+pw*a/mx+6:.1f}" y="{y+13}" class="val">{a*100:.0f}%</text>'
                 f'<rect x="{lw}" y="{y+18}" width="{pw*b/mx:.1f}" height="11" rx="2" style="fill:var(--c2)"/><text x="{lw+pw*b/mx+6:.1f}" y="{y+27}" class="val">{b*100:.0f}%</text></g>')
    o.append(f'<rect x="{lw}" y="{h-16}" width="10" height="10" style="fill:var(--c1)"/><text x="{lw+14}" y="{h-7}" class="tick">Regresión logística (SHAP, log-odds)</text><rect x="{lw+230}" y="{h-16}" width="10" height="10" style="fill:var(--c2)"/><text x="{lw+244}" y="{h-7}" class="tick">Bosque aleatorio (SHAP, probabilidad)</text></svg>')
    mw, mrh, mpad = 360, 46, 4; mh = mrh*len(items)+mpad*2+18; mbar = mw-60
    m=[_svg_open(mw, mh, "Importancia global")]
    for r,i in enumerate(items):
        y=mpad+r*mrh; a=i["shap_logistica"]/tl; b=i["shap_bosque"]/tb
        m.append(f'<g class="row" data-tip="{esc(i["variable"])}: {a*100:.0f}% logística · {b*100:.0f}% bosque"><rect x="0" y="{y}" width="{mw}" height="{mrh}" fill="transparent"/>'
                 f'<text x="0" y="{y+12}" class="lbl">{esc(i["variable"])}</text>'
                 f'<rect x="0" y="{y+18}" width="{mbar*a/mx:.1f}" height="8" rx="2" style="fill:var(--c1)"/><text x="{mbar*a/mx+5:.1f}" y="{y+26}" class="val">{a*100:.0f}%</text>'
                 f'<rect x="0" y="{y+29}" width="{mbar*b/mx:.1f}" height="8" rx="2" style="fill:var(--c2)"/><text x="{mbar*b/mx+5:.1f}" y="{y+37}" class="val">{b*100:.0f}%</text></g>')
    m.append(f'<rect x="0" y="{mh-14}" width="9" height="9" style="fill:var(--c1)"/><text x="13" y="{mh-6}" class="tick">Logística</text><rect x="90" y="{mh-14}" width="9" height="9" style="fill:var(--c2)"/><text x="103" y="{mh-6}" class="tick">Bosque aleatorio</text></svg>')
    return both("\n".join(o), "\n".join(m))

def beeswarm(rows, w=720):
    rh, pad, lw = 50, 10, 230; h = rh*len(rows)+pad*2+26; pw = w-lw-20
    allv=[v[1] for r in rows for v in r["valores"]]; xmin,xmax=min(allv)-0.05,max(allv)+0.05
    X=lambda v: lw+pw*(v-xmin)/(xmax-xmin)
    rows=sorted(rows,key=lambda r:-sum(abs(v[1]) for v in r["valores"]))
    o=[f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="SHAP por episodio">']
    for t in (-1,-0.5,0,0.5,1):
        if xmin<t<xmax: o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad}" y2="{h-24}" class="{"ref" if t==0 else "grid"}"/><text x="{X(t):.1f}" y="{h-8}" text-anchor="middle" class="tick">{t:+g}</text>')
    import random; rnd=random.Random(7)
    for r,row in enumerate(rows):
        y0=pad+r*rh+rh/2; es_edad=row["variable"].startswith("Edad")
        o.append(f'<text x="{lw-10}" y="{y0+4}" text-anchor="end" class="lbl">{esc(row["variable"])}</text>')
        # apilar puntos por celda para evitar solapamiento (beeswarm simple)
        bins={}
        for xv,sv in row["valores"]:
            k=round(sv*40); bins.setdefault(k,[]).append((xv,sv))
        for k,pts in bins.items():
            n=len(pts); rows_per_col=11; ncol=(n+rows_per_col-1)//rows_per_col
            if n>rows_per_col and not es_edad:
                o.append(f'<text x="{X(pts[0][1]):.1f}" y="{y0-rh/2+6:.1f}" text-anchor="middle" class="tick">n={n}</text>')
            for j,(xv,sv) in enumerate(pts):
                col_i=j//rows_per_col; row_i=j%rows_per_col; nrow=min(rows_per_col,n-col_i*rows_per_col)
                dy=(row_i-(nrow-1)/2)*3.2; dx=(col_i-(ncol-1)/2)*6.5 if not es_edad else 0
                if es_edad: col=f'color-mix(in oklab,var(--c3) {min(100,max(0,(xv-18)/50*100)):.0f}%,var(--c4))'
                else: col="var(--c3)" if xv>=0.5 else "var(--c4)"
                tip=f'{esc(row["variable"])} = {("Sí" if xv>=0.5 else "No") if not es_edad else int(xv)} → SHAP {sv:+.2f}'
                o.append(f'<circle cx="{X(sv)+dx:.1f}" cy="{y0+dy:.1f}" r="3" style="fill:{col};fill-opacity:.8" data-tip="{tip}"/>')
    o.append(f'<circle cx="{lw}" cy="{h-11}" r="4" style="fill:var(--c4)"/><text x="{lw+8}" y="{h-8}" class="tick">No / edad baja</text><circle cx="{lw+120}" cy="{h-11}" r="4" style="fill:var(--c3)"/><text x="{lw+128}" y="{h-8}" class="tick">Sí / edad alta</text><text x="{w-20}" y="{h-8}" text-anchor="end" class="tick">← baja el riesgo · sube el riesgo →   (log-odds)</text></svg>')
    return scrollable("\n".join(o))

def waterfall(ej):
    c=ej["contribuciones_logodds"]; ks=sorted(c,key=lambda k:-abs(c[k])); mx=max(abs(v) for v in c.values()) or 1
    rows="".join(f'<div class="wf"><span class="wfl">{esc(k)} <b class="muted">{esc(str(ej["caracteristicas"][k]))}</b></span><span class="wfb"><i style="--w:{abs(c[k])/mx*100:.0f}%;--side:{"pos" if c[k]>0 else "neg"}" class="{"pos" if c[k]>0 else "neg"}"></i></span><span class="wfv mono">{c[k]:+.2f}</span></div>' for k in ks)
    return f'<article class="ex"><div class="k">EPISODIO {esc(ej["etiqueta"])}</div><div class="risk"><span class="n">{ej["riesgo_logistica"]*100:.0f}%</span><span class="l">riesgo según logística · bosque {ej["riesgo_bosque"]*100:.0f}% · abandono real: <b>{ej["abandono_real"]}</b></span></div>{rows}<div class="wfnote">Base {XA["base_prob_logistica"]*100:.0f}% (log-odds {XA["base_logodds"]:+.2f}); las barras suman la diferencia respecto a la base.</div></article>'

def pd_chart(pdd): return both(_pd_chart(pdd), _pd_chart(pdd, 340, 200))
def _pd_chart(pdd, w=520, h=220):
    ages=pdd["edad"]; pad_l,pad_b,pad_t=44,30,10; pw,ph=w-pad_l-12,h-pad_b-pad_t; ymax=0.4
    X=lambda a: pad_l+pw*(a-ages[0])/(ages[-1]-ages[0]); Y=lambda v: pad_t+ph*(1-v/ymax)
    o=[f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Dependencia parcial de la edad">']
    for t in (0,0.1,0.2,0.3,0.4): o.append(f'<line x1="{pad_l}" x2="{w-12}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{pad_l-6}" y="{Y(t)+4:.1f}" text-anchor="end" class="tick">{int(t*100)}%</text>')
    for a in ages[::3]: o.append(f'<text x="{X(a):.1f}" y="{h-8}" text-anchor="middle" class="tick">{a}</text>')
    for key,col,name in (("logistica","--c1","Logística"),("bosque","--c2","Bosque")):
        pts=" ".join(f"{X(a):.1f},{Y(v):.1f}" for a,v in zip(ages,pdd[key])); o.append(f'<polyline points="{pts}" fill="none" style="stroke:var({col})" stroke-width="2"/>')
        for a,v in zip(ages,pdd[key]): o.append(f'<circle cx="{X(a):.1f}" cy="{Y(v):.1f}" r="3.5" style="fill:var({col})" data-tip="{name}, {a} años: riesgo medio {v*100:.0f}%"/>')
    o.append(f'<text x="{w-14}" y="{Y(pdd["logistica"][-1])-8:.0f}" text-anchor="end" class="val" style="fill:var(--c1)">Logística</text><text x="{w-14}" y="{Y(pdd["bosque"][-1])+16:.0f}" text-anchor="end" class="val" style="fill:var(--c2)">Bosque</text></svg>')
    return "\n".join(o)

def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tblwrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

def sig(p): return ' <span class="chip sig">p&lt;0,05</span>' if p < 0.05 else ""
def assoc_rows(items, q=False):
    return [[esc(i["x"]), esc(i["y"]), f'{i["pct_exp"]}% vs {i["pct_noexp"]}%', f'{i["OR"]} ({i["IC_lo"]}–{i["IC_hi"]})', i["prueba"], pfmt(i["p"]) + sig(i["p"])] + ([f'{i["q_FDR"]:.3f}'] if q else []) for i in items]

pc, ec = E["pac_cat"], E["epi_cat"]
def g(d, cat): return next((i for i in d if i["cat"] == cat), {"n": 0, "pct": 0})
desc = lambda items: sorted(items, key=lambda i: -i["n"])
edad, ini, dias = E["pac_num"]["edad"], E["pac_num"]["edad_inicio_consumo"], E["epi_num"]["dias_hosp"]
A, BC, D = E["biv_protocolo"]["A_policonsumo_sintomas"], E["biv_protocolo"]["BC_vulnerabilidad"], E["biv_protocolo"]["D_reingreso_episodio"]
kw = E["kw_dias_egreso"]; prof = K["perfil_pct"]; out = K["desenlaces"]; sizes = K["tamanos"]
c1n, c2n = sizes["1"], sizes["2"]
bip_ep = next(i for i in D if i["x"] == "Trastorno afectivo bipolar")
bip_pac = next(i for i in E["screen_reingreso_pac"] if i["x"] == "T. bipolar")
abx = E["screen_abandono_epi"]; multi = {(m["x"], m["y"]): m for m in E["multi"]}

# perfil table
prof_rows = []
for lbl, v in prof.items():
    a, b = v["1"], v["2"]; p = K["pruebas_p"].get(lbl, K["pruebas_p"].get(lbl.replace(" (desenlace)", "")))
    cell = lambda x: f'<td class="hm" style="--v:{x/100:.2f}">{x:.0f}%</td>'
    prof_rows.append(f'<tr><td>{esc(lbl)}</td>{cell(a)}{cell(b)}<td class="mono muted">{pfmt(p) if p is not None else "–"}</td></tr>')
for lbl, v in K["perfil_num"].items():
    prof_rows.append(f'<tr><td>{esc(lbl)}</td><td class="mono">{v["1"]}</td><td class="mono">{v["2"]}</td><td class="mono muted">{pfmt(K["pruebas_p"][lbl.split(" (")[0]]) if lbl.split(" (")[0] in K["pruebas_p"] else "–"}</td></tr>')
prof_table = f'<div class="tblwrap"><table class="prof"><thead><tr><th>Característica</th><th>Clúster 1 <span class="muted">n={c1n}</span></th><th>Clúster 2 <span class="muted">n={c2n}</span></th><th>p</th></tr></thead><tbody>{"".join(prof_rows)}</tbody></table></div>'
drog = K["droga_por_cluster"]
drog_rows = [[esc(d), f'{drog["1"][d]:.0f}%', f'{drog["2"][d]:.0f}%'] for d in sorted(drog["1"], key=lambda d: -(drog["1"][d]+drog["2"][d]))]

IDEAS = {
 "Para cerrar la tesis (antes de la sustentación)": [
  ("Bautizar los dos perfiles y llevarlos a la discusión", f"El clúster 1 (n={c1n}) es un perfil <em>afectivo-internalizante</em>: depresión, trastorno de personalidad, intentos suicidas y autolesiones, con entrada al programa CETA. El clúster 2 (n={c2n}) es un perfil <em>psicótico-externalizante</em>: psicosis y heteroagresión al ingreso, bipolaridad, antecedentes legales, pobreza y reingresos. Son la columna vertebral de la discusión."),
  ("Documentar el flujo de la muestra", "El protocolo estimó 150 pacientes; el análisis usa 118. Falta un párrafo o diagrama tipo STROBE con las 32 excluidas y sus motivos (expediente no ubicado, sin TUS documentado, menores de edad, duplicados)."),
  ("Matizar el hallazgo bipolar–reingreso", f"A nivel episodio el OR es {bip_ep['OR']} (p={bip_ep['p']}), pero a nivel paciente y con corrección FDR el valor q es {bip_pac['q_FDR']}: la asociación es sugerente, no concluyente. Conviene presentarla como hipótesis y no como resultado firme."),
  ("Declarar la no independencia de los episodios", "35 pacientes aportan 2 o más episodios. Los cruces a nivel episodio (n=173) deben citarse como análisis de sensibilidad, con el análisis a nivel paciente como principal, o al menos declararse como limitación."),
  ("Actualizar la tabla de variables", "Categorías que aparecen en los datos pero no en el instrumento aprobado: expulsión de CETA, completó CETA, privada de libertad, situación de calle, jubilada. Y variables prometidas que no se recogieron: fechas, vía y frecuencia de consumo, tomografía, seguimiento posterior."),
  ("Anonimizar y custodiar la base", "La base ya está anonimizada en esta carpeta. La llave nombre–código debe moverse al USB institucional y borrarse de todos los equipos, como exige el protocolo aprobado por bioética."),
 ],
 "Análisis adicionales que los datos sí permiten": [
  ("Regresión logística para el abandono del tratamiento", f"Alta voluntaria, SSAM y expulsión suman {g(ec['motivo_egreso'],'Alta voluntaria')['n']+g(ec['motivo_egreso'],'SSAM')['n']+g(ec['motivo_egreso'],'Expulsión de CETA')['n']} episodios. Con 4 predictores (LAI, síntomas psicóticos, trastorno de personalidad, policonsumo) se cumple la regla de 10 eventos por variable. Es el modelo con más señal de toda la base."),
  ("Explotar los códigos CIE del egreso", "El diagnóstico de egreso trae códigos secundarios (F60.3, F31, F32). Extraerlos permite cuantificar el trastorno límite de la personalidad, que hoy queda diluido en 'trastorno de la personalidad'."),
  ("Droga de elección y psicosis", f"La asociación droga × síntomas psicóticos tiene V de Cramér {multi[('droga_eleccion','sx_psicotico')]['cramer_v']} (p={pfmt(multi[('droga_eleccion','sx_psicotico')]['p'])}). Vale una tabla que muestre qué sustancias (cocaína, piedra, metanfetamina) concentran la psicosis."),
  ("Abuso sexual e inicio temprano del consumo", "Las pacientes con abuso sexual inician a los 14 años frente a 15 (Mann-Whitney p<0,001). Explorar una relación dosis-respuesta con violencia intrafamiliar y número de intentos suicidas."),
  ("Validar los clústeres con otro método", "Repetir con análisis de clases latentes o k-prototipos y reportar el índice de Rand ajustado. PAM y jerárquico ya coinciden (ARI 0,81), lo que es buena señal."),
  ("Conteo de episodios como variable de resultado", "Sin fechas no hay análisis de supervivencia, pero el número de episodios por paciente puede modelarse con regresión de Poisson o binomial negativa frente al perfil clínico."),
 ],
 "Implicaciones clínicas e institucionales": [
  ("Tamizaje universal de trauma y riesgo suicida", f"{g(pc['violencia_intrafamiliar'],'Sí')['pct']}% reporta violencia intrafamiliar, {g(pc['abuso_sexual'],'Sí')['pct']}% abuso sexual y {g(pc['intento_suicida_previo'],'Sí')['pct']}% intentos suicidas. Ninguna mujer con TUS debería egresar sin una evaluación estructurada de trauma y riesgo."),
  ("Ruta de continuidad para el perfil psicótico-externalizante", f"El clúster 2 concentra el LAI ({out['2']['lai_pct']}% de sus episodios), la medicación de urgencia y los reingresos ({out['2']['reingreso_pct']}%). Una ruta con LAI al egreso, trabajo social y enlace con el sistema judicial podría reducir la puerta giratoria."),
  ("Retención en CETA para el perfil afectivo", f"El clúster 1 accede a CETA pero {out['1']['alta_vol_pct']}% de sus episodios termina en alta voluntaria, SSAM o expulsión. Intervenciones de retención centradas en regulación emocional (terapia dialéctico-conductual, tratamiento integrado de trauma) tienen aquí su población diana."),
  ("Brecha de acceso a rehabilitación", f"Solo {g(pc['n_episodios'],'1')['n']} pacientes tuvieron un único episodio y apenas {g(ec['motivo_hosp'],'Programa CETA')['n']} episodios fueron ingresos programados a CETA en tres años. La mayoría entra en crisis y no llega al programa de rehabilitación."),
  ("Prueba de metabolitos", f"En {g(ec['metabolitos_positivos'],'No se realizó')['pct']}% de los episodios no se hizo la prueba en orina. Un estándar de tamizaje toxicológico al ingreso mejoraría la calidad del diagnóstico."),
  ("Mejorar el registro clínico", "Agregar al expediente fechas de ingreso y egreso, vía y frecuencia de consumo y el seguimiento ambulatorio posterior. Son las variables que el protocolo quería y el expediente no tenía."),
 ],
 "Publicación y trabajo futuro": [
  ("Artículo original", "Título tentativo: «Dos fenotipos clínicos en mujeres hospitalizadas por trastornos por uso de sustancias en Panamá». Candidatas: Revista Adicciones, Revista Panamericana de Salud Pública, Journal of Substance Use and Addiction Treatment."),
  ("Comparación con hombres del INSAM", "Aplicar el mismo instrumento a una muestra de hombres del mismo período permitiría el análisis de diferencias por sexo que la literatura pide (telescoping, trauma, comorbilidad)."),
  ("Cohorte prospectiva", "Seguimiento a 6 y 12 meses del egreso con fechas exactas habilitaría análisis de supervivencia hasta el reingreso y evaluación de la ruta de continuidad."),
  ("Validación externa de los perfiles", "Replicar el clustering en otro centro (Hospital Regional de Chiriquí, CETA de otras provincias) o en otros años del INSAM para ver si los dos perfiles se sostienen."),
 ],
}
ideas_html = ""
for grp, items in IDEAS.items():
    cards = "".join(f'<article class="idea"><h4>{esc(t)}</h4><p>{b}</p></article>' for t, b in items)
    ideas_html += f'<h3>{esc(grp)}</h3><div class="ideas">{cards}</div>'

cambios = "".join(f"<li>{esc(c)}</li>" for c in L["cambios"])
val = L["validaciones"]
val_rows = [["Edad mínima", val["edad_min"], "Cumple criterio ≥18"], ["Menores de 18", val["menores_18"], "–"],
            ["Edad de inicio mayor que la edad actual", val["edad_inicio_> edad"], "Revisar en expediente"],
            ["Egresos sin código F10–F19", len(val["egreso_sin_F1x"]), "Verificar TUS en diagnóstico de ingreso (criterio de inclusión)"],
            ["Intento suicida Sí/No vs número de intentos", val["inconsistencia_intentos"], "Corregir en base"],
            ["Comorbilidad Sí/No vs tipos marcados", val["inconsistencia_comorb"], "Corregir en base"],
            ["Policonsumo Sí con 1 sustancia", val["inconsistencia_policonsumo"], "Corregir en base"],
            ["LAI Sí/No vs tipo de LAI", val["inconsistencia_lai"], "Corregir en base"],
            ["Celdas vacías (pacientes)", sum(val["celdas_vacias_pac"].values()), ", ".join(val["celdas_vacias_pac"])]]
unif_rows = [[esc(k), ", ".join(f"{esc(a)} → {esc(b)}" for a, b in v)] for k, v in L["categorias_unificadas"].items()]

CSS = r"""
:root{color-scheme:light;
--paper:#f5f7f5;--surface:#ffffff;--surface2:#e9efec;--ink:#14201c;--ink2:#3e4f48;--muted:#78857f;--line:#d3dcd6;--rule:#14201c;
--accent:#0f5f4c;--accent-ink:#0b4a3b;--tint:#e2efe9;
--c1:#0a8060;--c2:#c7920f;--c3:#c4472b;--c4:#3d6fb0;--sig:#c4472b;
--display:'Newsreader',Georgia,'Times New Roman',serif;--body:'Source Serif 4',Georgia,'Times New Roman',serif;--ui:'Source Sans 3','Segoe UI',Helvetica,Arial,sans-serif;--mono:'Source Code Pro',ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#101614;--surface:#161d1a;--surface2:#1e2723;--ink:#e8ede9;--ink2:#b7c2bb;--muted:#7f8b85;--line:#2b3531;--rule:#c9d3cd;--accent:#5cc2a2;--accent-ink:#8ad8bf;--tint:#173029;--c1:#2c9a86;--c2:#b98a1c;--c3:#d95f3a;--c4:#5b8ccc;--sig:#d95f3a}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#101614;--surface:#161d1a;--surface2:#1e2723;--ink:#e8ede9;--ink2:#b7c2bb;--muted:#7f8b85;--line:#2b3531;--rule:#c9d3cd;--accent:#5cc2a2;--accent-ink:#8ad8bf;--tint:#173029;--c1:#2c9a86;--c2:#b98a1c;--c3:#d95f3a;--c4:#5b8ccc;--sig:#d95f3a}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:17.5px;line-height:1.6;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
body::before{content:"";display:block;height:5px;background:var(--accent)}
a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}
a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--c3);outline-offset:2px}
::selection{background:var(--tint)}
.wrap{max-width:980px;margin:0 auto;padding:0 28px}
/* masthead */
header.mast{padding:30px 0 34px}
.mast-top{display:flex;justify-content:space-between;gap:12px 24px;flex-wrap:wrap;font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);padding-bottom:14px;border-bottom:1px solid var(--line)}
h1{font-family:var(--display);font-weight:500;font-size:clamp(36px,5.4vw,60px);line-height:1;letter-spacing:-.018em;margin:30px 0 16px;max-width:20ch;text-wrap:balance;font-variation-settings:"opsz" 72}
.sub{font-family:var(--display);font-style:italic;font-weight:400;font-size:21px;line-height:1.4;color:var(--ink2);max-width:58ch;margin:0 0 30px;font-variation-settings:"opsz" 20}
dl.synopsis{display:grid;grid-template-columns:repeat(3,1fr);margin:0;border-top:1px solid var(--rule)}
dl.synopsis>div{padding:13px 22px 14px 0;border-bottom:1px solid var(--line);min-width:0}
dl.synopsis>div.span{grid-column:1/-1;border-bottom:1px solid var(--rule)}
dl.synopsis>div.span dd{font-family:var(--body);font-size:17px;line-height:1.45;max-width:70ch}
dt{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:5px}
dd{margin:0;font-family:var(--ui);font-size:14.5px;line-height:1.45;color:var(--ink);overflow-wrap:anywhere}
@media (max-width:760px){dl.synopsis{grid-template-columns:1fr 1fr}}
@media (max-width:480px){dl.synopsis{grid-template-columns:1fr}}
/* índice de pestañas */
nav.toc{position:sticky;top:0;z-index:5;background:color-mix(in oklab,var(--paper) 92%,transparent);backdrop-filter:blur(10px);border-top:1px solid var(--rule);border-bottom:1px solid var(--line)}
nav.toc ul{list-style:none;margin:0;padding:0;display:flex;gap:0 26px;overflow-x:auto;scrollbar-width:none}
nav.toc a{display:block;padding:13px 0 11px;font-family:var(--ui);font-weight:600;font-size:14px;letter-spacing:.02em;color:var(--ink2);text-decoration:none;white-space:nowrap;border-bottom:2px solid transparent;margin-bottom:-1px}
nav.toc a:hover{color:var(--ink)} nav.toc a.active{color:var(--accent);border-bottom-color:var(--accent)} nav.toc a:focus-visible{outline-offset:-2px}
/* secciones y texto */
section.panel{padding:44px 0 60px} section.panel[hidden]{display:none}
h2{font-family:var(--display);font-weight:500;font-size:38px;line-height:1.08;letter-spacing:-.015em;margin:0 0 12px;max-width:24ch;text-wrap:balance;font-variation-settings:"opsz" 48}
h2 .num{display:block;font-family:var(--mono);font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:12px;font-weight:500}
h3{font-family:var(--display);font-weight:500;font-size:25px;line-height:1.2;letter-spacing:-.005em;margin:44px 0 10px;text-wrap:balance;font-variation-settings:"opsz" 28}
h4{font-family:var(--ui);font-weight:600;font-size:16px;margin:0 0 6px}
p{max-width:66ch;margin:10px 0 16px} p.lede{font-size:20px;line-height:1.5;color:var(--ink2);max-width:60ch;margin:6px 0 24px}
ul.plain{max-width:66ch;padding-left:1.25em;margin:10px 0 18px} ul.plain li{margin:7px 0;padding-left:.15em} ul.plain li::marker{color:var(--accent)}
.mono{font-family:var(--mono);font-size:13px} .muted{color:var(--muted)}
code{font-family:var(--mono);font-size:.86em;background:var(--surface2);padding:1px 5px;border-radius:2px}
/* cifras clave */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:0 28px;margin:26px 0 30px;border-top:1px solid var(--rule)}
.tiles.six{grid-template-columns:repeat(3,1fr)}
.tile{padding:14px 0 16px;border-bottom:1px solid var(--line)}
.tile .n{font-family:var(--display);font-weight:500;font-size:46px;line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums;color:var(--ink);font-variation-settings:"opsz" 72}
.tile .l{font-family:var(--ui);font-size:14px;color:var(--ink2);margin-top:8px;line-height:1.35} .tile .d{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin-top:5px}
@media (max-width:640px){.tiles.six{grid-template-columns:repeat(2,1fr)}}
/* figuras y gráficas */
figure{margin:28px 0 36px;padding:0}
figcaption{display:flex;justify-content:space-between;align-items:baseline;gap:8px 16px;flex-wrap:wrap;border-top:1px solid var(--rule);padding:9px 0 12px;font-family:var(--ui);font-size:14px;color:var(--ink2)}
figcaption b{font-weight:600;color:var(--ink)}
.fignum{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:500;margin-right:10px}
.src{font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:.02em}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 36px} @media (max-width:720px){.grid2{grid-template-columns:1fr}}
svg.chart{width:100%;height:auto;display:block;font-family:var(--ui)} svg .lbl{font-size:13px;fill:var(--ink)} svg .val{font-size:12.5px;fill:var(--ink);font-variant-numeric:tabular-nums}
svg .muted{fill:var(--muted)} svg .tick{font-size:11px;fill:var(--muted)} svg .grid{stroke:var(--line);stroke-width:1} svg .ref{stroke:var(--muted);stroke-dasharray:4 3}
svg .cell{font-size:9px;fill:var(--ink)} svg .cell.on{fill:#fff} svg .mono{font-family:var(--mono);font-size:11.5px} svg g.row:hover rect:first-child{fill:var(--surface2)}
.lectura{margin:12px 0 0;padding:2px 0 2px 18px;border-left:2px solid var(--line);font-family:var(--ui);font-size:14.5px;line-height:1.5;color:var(--ink2);max-width:72ch}
.lectura p{margin:0 0 7px;max-width:none} .lectura p:last-child{margin-bottom:0} .lectura b{color:var(--ink);font-weight:600}
.tblwrap .lectura{margin:14px 0 4px}
/* tablas */
.tblwrap{overflow-x:auto;margin:16px 0 28px}
table{border-collapse:collapse;width:100%;font-family:var(--ui);font-size:14.5px;border-top:1.5px solid var(--rule);border-bottom:1px solid var(--rule)}
th{text-align:left;font-family:var(--mono);font-weight:500;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:10px 14px 8px 0;border-bottom:1px solid var(--rule);vertical-align:bottom}
td{padding:9px 14px 9px 0;border-bottom:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums;line-height:1.45} tr:last-child td{border-bottom:0}
th:last-child,td:last-child{padding-right:0} table td:first-child{min-width:150px}
tbody tr:hover td:not(.hm){background:var(--surface2)}
td.hm{background:color-mix(in oklab,var(--c1) calc(var(--v)*70%),var(--surface));font-family:var(--mono);font-size:13px;color:var(--ink)}
.chip{display:inline-block;font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px 1px;border:1px solid var(--line);border-radius:2px;color:var(--ink2);vertical-align:middle;white-space:nowrap}
.chip.sig{border-color:var(--sig);color:var(--sig)}
/* notas */
.callout{border-left:2px solid var(--accent);padding:2px 0 2px 20px;margin:24px 0;max-width:70ch} .callout p{margin:4px 0;max-width:none} .callout.warn{border-left-color:var(--c3)}
details{margin:10px 0 18px} summary{cursor:pointer;color:var(--accent);font-weight:600;font-family:var(--ui)}
/* perfiles */
.profiles{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0 12px} @media (max-width:720px){.profiles{grid-template-columns:1fr}}
.profile{padding:20px 22px 18px;border-top:3px solid var(--c1);background:color-mix(in oklab,var(--c1) 7%,var(--surface))} .profile.two{border-top-color:var(--c2);background:color-mix(in oklab,var(--c2) 9%,var(--surface))}
.profile .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;color:var(--muted)} .profile h4{font-family:var(--display);font-weight:500;font-size:25px;line-height:1.15;margin:8px 0 12px;letter-spacing:-.005em}
.profile ul{padding-left:18px;margin:0;font-family:var(--ui);font-size:15px;line-height:1.5} .profile li{margin:5px 0} .profile li::marker{color:var(--muted)}
/* ideas */
.ideas{display:grid;grid-template-columns:repeat(2,1fr);gap:0 40px;margin:8px 0 34px} @media (max-width:720px){.ideas{grid-template-columns:1fr}}
.idea{padding:16px 0 20px;border-top:1px solid var(--line)} .idea h4{font-family:var(--display);font-weight:500;font-size:21px;line-height:1.2;margin:0 0 8px;letter-spacing:-.005em} .idea p{font-size:15.5px;line-height:1.5;margin:0;color:var(--ink2);max-width:none} .idea em{font-style:normal;font-weight:600;color:var(--ink)}
/* dudas */
details.faq{margin:0;padding:18px 0 14px;border-top:1px solid var(--line)}
details.faq summary{font-family:var(--display);font-weight:500;font-size:21px;line-height:1.3;color:var(--ink);list-style:none;display:flex;gap:14px;align-items:baseline;letter-spacing:-.005em}
details.faq summary::-webkit-details-marker{display:none} details.faq summary::before{content:"+";font-family:var(--mono);font-size:18px;color:var(--accent);flex:0 0 16px} details.faq[open] summary::before{content:"−"} details.faq[open] summary{color:var(--accent-ink)}
details.faq p{max-width:70ch;margin:12px 0 4px 30px} details.faq .tblwrap{margin-left:30px}
/* explicabilidad */
.examples{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:0 30px;margin:14px 0 30px}
.ex{padding:14px 0 18px;border-top:1px solid var(--rule)} .ex .k,.calc .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;color:var(--muted)}
.risk{display:flex;align-items:baseline;gap:12px;margin:6px 0 12px} .risk .n{font-family:var(--display);font-weight:500;font-size:38px;line-height:1;letter-spacing:-.02em} .risk .l{font-family:var(--ui);font-size:13px;color:var(--ink2);line-height:1.35}
.wf{display:grid;grid-template-columns:1fr 84px 50px;gap:8px;align-items:center;font-family:var(--ui);font-size:13px;padding:3px 0} .wf .wfl b{font-weight:600;color:var(--ink2)}
.wfb{position:relative;height:9px;background:var(--surface2);overflow:hidden} .wfb i{position:absolute;top:0;height:100%;width:calc(var(--w)/2)} .wfb i.pos{left:50%;background:var(--c3)} .wfb i.neg{right:50%;background:var(--c4)}
.wfv{text-align:right;font-size:12px} .wfnote{font-family:var(--ui);font-size:12px;color:var(--muted);margin-top:8px}
.calc{display:grid;grid-template-columns:1fr 1fr;gap:26px;border:1px solid var(--line);background:var(--surface);padding:22px 24px;margin:12px 0 28px} @media (max-width:720px){.calc{grid-template-columns:1fr}}
.calc-in{display:flex;flex-direction:column;gap:11px} .calc-in label{display:flex;align-items:center;gap:10px;font-family:var(--ui);font-size:15px;cursor:pointer} .calc-in input[type=checkbox]{width:17px;height:17px;accent-color:var(--accent)} .calc-in label.range{flex-wrap:wrap} .calc-in input[type=range]{width:100%;accent-color:var(--accent)}
.calc-out .risk .n{font-size:50px;color:var(--accent)}
/* bibliografía */
ol.refs{max-width:76ch;padding-left:2.6em;font-family:var(--ui);font-size:14px;line-height:1.5;color:var(--ink2)} ol.refs li{margin:7px 0;padding-left:.2em} ol.refs li::marker{font-family:var(--mono);font-size:12px;color:var(--muted)}
ol.refs a{color:var(--accent);text-decoration:none;border-bottom:1px solid color-mix(in oklab,var(--accent) 40%,transparent)} ol.refs a:hover{border-bottom-color:var(--accent)}

/* variantes de gráfica y desplazamiento */
.ch-m{display:none} .scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.tblwrap.scrolls::before,.scroll.scrolls::before{content:"Desliza hacia el lado para ver todo →";display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;color:var(--muted);padding:0 0 8px}
nav.toc .wrap{position:relative} nav.toc .wrap::after{content:"";position:absolute;right:0;top:0;bottom:0;width:44px;background:linear-gradient(90deg,transparent,var(--paper));pointer-events:none;opacity:0}
@media (max-width:640px){
 .ch-d{display:none} .ch-m{display:block} .scroll-in{min-width:700px}
 nav.toc .wrap::after{opacity:1} nav.toc ul{gap:0 20px;padding-right:44px} nav.toc a{font-size:13.5px;padding:12px 0 10px}
 body{font-size:16.5px} .wrap{padding:0 18px}
 header.mast{padding:20px 0 24px} .mast-top{font-size:10px;letter-spacing:.1em;gap:6px 14px} h1{margin:20px 0 12px} .sub{font-size:18px;margin-bottom:20px}
 dl.synopsis>div{padding:11px 0 12px} dl.synopsis>div.span dd{font-size:16px}
 section.panel{padding:30px 0 44px} h2{font-size:31px} h3{font-size:22px;margin-top:34px} p.lede{font-size:18px}
 .tiles{grid-template-columns:repeat(2,1fr);gap:0 18px} .tiles.six{grid-template-columns:repeat(2,1fr)} .tile .n{font-size:34px} .tile .l{font-size:13px}
 figure{margin:22px 0 28px} figcaption{font-size:13.5px;padding:8px 0 10px}
 table{font-size:13.5px} td{padding:8px 10px 8px 0} th{padding-right:10px} table td:first-child{min-width:130px}
 .callout{padding-left:14px} .lectura{font-size:14px;padding-left:14px}
 .profiles{gap:16px} .profile{padding:16px 16px 14px} .profile h4{font-size:22px} .profile ul{font-size:14.5px}
 .idea h4{font-size:19px} .idea p{font-size:15px}
 details.faq summary{font-size:19px;gap:10px} details.faq p{margin-left:0} details.faq .tblwrap{margin-left:0}
 .examples{gap:0} .wf{grid-template-columns:1fr 70px 46px}
 .calc{padding:16px;gap:18px} .calc-in label{font-size:15px;min-height:28px} .calc-in input[type=checkbox]{width:20px;height:20px} .calc-out .risk .n{font-size:42px}
 ol.refs{padding-left:2.2em;font-size:13.5px}
 #tip{max-width:min(320px,calc(100vw - 24px))}
 footer{font-size:10.5px;letter-spacing:.06em}
}
/* tooltip, pie, impresión */
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--paper);font-family:var(--ui);font-size:13px;line-height:1.35;padding:7px 10px;border-radius:2px;max-width:320px;z-index:20;opacity:0;transition:opacity .12s} #tip.on{opacity:1}
@media (prefers-reduced-motion:reduce){#tip{transition:none}}
footer{border-top:1px solid var(--rule);margin-top:24px;padding:22px 0 60px;font-family:var(--mono);font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
@media print{nav.toc,#tip,body::before{display:none} section.panel[hidden]{display:block!important} figure,table,.profile,.idea{break-inside:avoid} body{font-size:11pt}}
"""
page = f"""<title>Mujeres con TUS en el INSAM</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Source+Sans+3:wght@400;600&family=Source+Code+Pro:wght@400;500&display=swap">
<style>{CSS}</style>

<header class="mast"><div class="wrap">
<div class="mast-top"><span>Ministerio de Salud · Instituto Nacional de Salud Mental · Maestría en Ciencias Clínicas, Psiquiatría</span><span>Informe de análisis · {__import__('datetime').date.today().strftime('%d·%m·%Y')}</span></div>
<h1>Mujeres hospitalizadas por trastornos por uso de sustancias</h1>
<p class="sub">Características sociodemográficas y clínicas, perfiles y desenlaces de todas las mujeres hospitalizadas por TUS en el Instituto Nacional de Salud Mental de Panamá entre octubre de 2022 y octubre de 2025. Estudio retrospectivo.</p>
<dl class="synopsis">
<div class="span"><dt>Pregunta de investigación</dt><dd>¿Cuáles son las características sociodemográficas y clínicas de las mujeres hospitalizadas por trastornos por uso de sustancias en el INSAM entre octubre de 2022 y octubre de 2025?</dd></div>
<div><dt>Diseño</dt><dd>Observacional, descriptivo, retrospectivo. Censo, sin cálculo de muestra.</dd></div>
<div><dt>Población</dt><dd>{NP} mujeres de 18 años o más · {NE} episodios · CIE-10 F10–F19</dd></div>
<div><dt>Investigadora</dt><dd>Dra. Eliany Luzcando A. · Residencia de Psiquiatría, INSAM</dd></div>
<div><dt>Asesoría</dt><dd>Dra. Juana Herrera, clínica · Ing. Juan Andrés Girón, metodológica</dd></div>
<div><dt>Ética y registro</dt><dd>CBIHN-2026020002 · RESEGIS 5054 · base anonimizada, sin datos identificables</dd></div>
<div><dt>Análisis</dt><dd>Python 3 · Gower + PAM · logística con EE robustos · SHAP</dd></div>
</dl>
</div></header>
<nav class="toc" aria-label="Secciones"><div class="wrap"><ul role="tablist">
<li><a role="tab" id="tab-resumen" href="#resumen" aria-controls="resumen" aria-selected="true" class="active">Resumen</a></li>
<li><a role="tab" id="tab-limpieza" href="#limpieza" aria-controls="limpieza" aria-selected="false">Limpieza</a></li>
<li><a role="tab" id="tab-pacientes" href="#pacientes" aria-controls="pacientes" aria-selected="false">Pacientes</a></li>
<li><a role="tab" id="tab-episodios" href="#episodios" aria-controls="episodios" aria-selected="false">Episodios</a></li>
<li><a role="tab" id="tab-bivariado" href="#bivariado" aria-controls="bivariado" aria-selected="false">Bivariado</a></li>
<li><a role="tab" id="tab-clusters" href="#clusters" aria-controls="clusters" aria-selected="false">Perfiles</a></li>
<li><a role="tab" id="tab-modelo" href="#modelo" aria-controls="modelo" aria-selected="false">Modelo</a></li>
<li><a role="tab" id="tab-xai" href="#xai" aria-controls="xai" aria-selected="false">XAI</a></li>
<li><a role="tab" id="tab-ideas" href="#ideas" aria-controls="ideas" aria-selected="false">Ideas</a></li>
<li><a role="tab" id="tab-metodos" href="#metodos" aria-controls="metodos" aria-selected="false">Métodos</a></li>
<li><a role="tab" id="tab-defensa" href="#defensa" aria-controls="defensa" aria-selected="false">Dudas</a></li>
<li><a role="tab" id="tab-literatura" href="#literatura" aria-controls="literatura" aria-selected="false">Literatura</a></li>
</ul></div></nav>

<section id="resumen" class="panel active" role="tabpanel" aria-labelledby="tab-resumen"><div class="wrap">
<h2><span class="num">Resumen</span>Lo que dicen los datos</h2>
<div class="tiles six">
<div class="tile"><div class="n">{NP}</div><div class="l">mujeres, {NE} episodios</div><div class="d">1,5 episodios por paciente</div></div>
<div class="tile"><div class="n">{edad['mediana']:.0f}</div><div class="l">años, mediana de edad</div><div class="d">inicio del consumo a los {ini['mediana']:.0f}</div></div>
<div class="tile"><div class="n">{g(pc['violencia_intrafamiliar'],'Sí')['pct']:.0f}%</div><div class="l">violencia intrafamiliar</div><div class="d">{g(pc['abuso_sexual'],'Sí')['pct']:.0f}% abuso sexual</div></div>
<div class="tile"><div class="n">{g(pc['intento_suicida_previo'],'Sí')['pct']:.0f}%</div><div class="l">con intento suicida previo</div><div class="d">{g(pc['conducta_parasuicida'],'Sí')['pct']:.0f}% conducta parasuicida</div></div>
<div class="tile"><div class="n">{MO["M1"]["AUC_corregida_optimismo"]}</div><div class="l">AUC del modelo de abandono</div><div class="d">puntaje de riesgo al ingreso</div></div>
<div class="tile"><div class="n">2</div><div class="l">perfiles clínicos</div><div class="d">silueta {K['silueta']} · ARI {K['estabilidad_ARI']['media']}</div></div>
</div>
<ul class="plain">
<li><b>Es una población joven, pobre y traumatizada.</b> Mediana de {edad['mediana']:.0f} años, {g(pc['ocupacion'],'Desempleada')['pct']}% desempleadas, {g(pc['ingreso_familiar'],'<500')['pct']}% con ingreso familiar menor de 500 balboas y {g(pc['algun_abuso'],'Sí')['pct']}% con violencia intrafamiliar o abuso sexual.</li>
<li><b>El consumo empieza en la adolescencia y es múltiple.</b> La mitad inició antes de los 15 años, {g(pc['policonsumo'],'Sí')['pct']}% tiene policonsumo activo y el diagnóstico de egreso más frecuente es F19.2 (dependencia a múltiples sustancias). Cocaína, alcohol y cannabis son las drogas de elección.</li>
<li><b>El policonsumo no explica la clínica del ingreso.</b> Ninguno de los cinco cruces del protocolo entre policonsumo y síntomas fue significativo. Lo que sí se asocia a psicosis y heteroagresión es la droga de elección (V de Cramér ≈ 0,4).</li>
<li><b>La vulnerabilidad psiquiátrica sí se asocia a la conducta parasuicida.</b> Depresión (OR 9,5), trastorno de personalidad, violencia intrafamiliar y abuso sexual sobreviven la corrección por comparaciones múltiples.</li>
<li><b>El abandono del tratamiento se puede anticipar al ingreso.</b> Trastorno de personalidad y policonsumo lo predicen tras ajuste mutuo; un puntaje de seis variables separa estratos con 0% y 43% de abandono, con AUC corregida de {MO["M1"]["AUC_corregida_optimismo"]}.</li>
<li><b>Hay dos perfiles clínicos claros.</b> Un perfil afectivo-internalizante (n={c1n}) que llega a CETA pero abandona, y un perfil psicótico-externalizante (n={c2n}) con antecedentes legales, pobreza, LAI y reingresos. La partición es estable (ARI bootstrap {K['estabilidad_ARI']['media']}) aunque de separación moderada (silueta {K['silueta']}).</li>
</ul>
</div></section>

<section id="limpieza" class="panel" role="tabpanel" aria-labelledby="tab-limpieza" hidden><div class="wrap">
<h2><span class="num">Paso 1 · Limpieza</span>De la hoja de cálculo a una base analizable</h2>
<p class="lede">La base original tenía nombres y cédulas, categorías escritas de tres formas distintas y varias inconsistencias internas. El script <code>01_limpieza.py</code> deja dos tablas anónimas y documenta cada cambio.</p>
<h3>Qué se hizo</h3>
<ul class="plain">
<li><b>Anonimización.</b> Se eliminaron nombre y cédula y se asignó el código que pide el protocolo (formato F-edad-número). La llave queda en un archivo aparte para custodia institucional.</li>
<li><b>Unidades de análisis.</b> Tabla de pacientes (n={NP}, características fijas) y tabla de episodios (n={NE}, presentación clínica, tratamiento y desenlace), enlazadas por el código.</li>
<li><b>Normalización.</b> Sí/No unificados; 16 variables con categorías reescritas (ver tabla); comorbilidad médica «0» convertida a «ninguna»; espacios y mayúsculas corregidos.</li>
<li><b>Variables derivadas.</b> Grupo de edad, conducta parasuicida (intento o autolesión), algún abuso, inicio temprano (&lt;15 años), años de consumo, síntoma psicótico, número de síntomas, número de fármacos, diagnóstico principal F1x, episodios por paciente, reingreso alguna vez.</li>
</ul>
<h3>Hallazgos de la validación</h3>
<ul class="plain">{cambios}</ul>
{table(["Verificación","Casos","Acción"], val_rows)}
<div class="callout warn"><p><b>Pendiente de la investigadora:</b> revisar en el expediente los {val['inconsistencia_intentos']+val['inconsistencia_comorb']+val['inconsistencia_policonsumo']+val['inconsistencia_lai']} registros inconsistentes y el episodio sin código F10–F19 al egreso. No alteran las conclusiones, pero deben resolverse antes de la versión final.</p></div>
<details><summary>Categorías unificadas (original → limpio)</summary>{table(["Variable","Recodificación"], unif_rows)}</details>
</div></section>

<section id="pacientes" class="panel" role="tabpanel" aria-labelledby="tab-pacientes" hidden><div class="wrap">
<h2><span class="num">Paso 2 · Descriptivo · pacientes</span>Quiénes son las {NP} pacientes</h2>
<p class="lede">Edad media {edad['media']} ± {edad['de']} años (rango {edad['min']:.0f}–{edad['max']:.0f}). Seis de cada diez tienen menos de 35 años. Casi todas son solteras, desempleadas y viven con familia.</p>
<div class="grid2">
<figure><figcaption><b>Grupo de edad</b><span class="src">pacientes</span></figcaption>{hbar(pc['grupo_edad'],'--c4')}</figure>
<figure><figcaption><b>Nivel educativo</b><span class="src">pacientes</span></figcaption>{hbar(pc['nivel_educativo'],'--c4')}</figure>
<figure><figcaption><b>Ocupación</b><span class="src">pacientes</span></figcaption>{hbar(desc(pc['ocupacion']),'--c4')}</figure>
<figure><figcaption><b>Ingreso familiar mensual (B/.)</b><span class="src">pacientes</span></figcaption>{hbar(pc['ingreso_familiar'],'--c4')}</figure>
<figure><figcaption><b>Tipo de convivencia</b><span class="src">pacientes</span></figcaption>{hbar(desc(pc['convivencia']),'--c4')}</figure>
<figure><figcaption><b>Estado civil</b><span class="src">pacientes</span></figcaption>{hbar(desc(pc['estado_civil']),'--c4')}</figure>
</div>
<h3>Trauma, antecedentes y riesgo suicida</h3>
<p>Los antecedentes de violencia son la norma, no la excepción. La conducta parasuicida (intento suicida o autolesión) está presente en {g(pc['conducta_parasuicida'],'Sí')['pct']}% y la mediana de intentos entre quienes los tienen es de 2.</p>
<figure><figcaption><b>Antecedentes psicosociales y psiquiátricos</b><span class="src">% de pacientes con «Sí»</span></figcaption>
{hbar([{"cat":l,"n":g(pc[c],'Sí')['n'],"pct":g(pc[c],'Sí')['pct']} for c,l in [("atencion_previa_sm","Atención previa en salud mental"),("violencia_intrafamiliar","Violencia intrafamiliar"),("policonsumo","Policonsumo activo"),("comorb_psiq","Comorbilidad psiquiátrica"),("abuso_sexual","Abuso sexual"),("intento_suicida_previo","Intento suicida previo"),("antec_legales","Antecedentes legales"),("conducta_autolesiva","Conducta autolesiva"),("hosp_previa_tus","Hospitalización previa por TUS"),("comorb_medica","Comorbilidad médica"),("grupos_autoayuda","Grupos de autoayuda previos"),("rehab_previa","Programa de rehabilitación previo")]])}</figure>
<div class="grid2">
<figure><figcaption><b>Comorbilidad psiquiátrica por tipo</b><span class="src">no excluyentes</span></figcaption>{hbar(sorted(E['pac_comorb_tipo'],key=lambda i:-i['n']))}</figure>
<figure><figcaption><b>Droga de elección</b><span class="src">pacientes</span></figcaption>{hbar(desc(pc['droga_eleccion']))}</figure>
<figure><figcaption><b>Número de sustancias</b><span class="src">pacientes</span></figcaption>{hbar(pc['n_sustancias'])}</figure>
<figure><figcaption><b>Episodios por paciente en el período</b><span class="src">pacientes</span></figcaption>{hbar(pc['n_episodios'],'--c4')}</figure>
</div>
<p>La edad de inicio del consumo tiene mediana {ini['mediana']:.0f} años (rango {ini['min']:.0f}–{ini['max']:.0f}); {g(pc['inicio_temprano_<15'],'Sí')['pct']}% empezó antes de los 15. La mediana de años de consumo al ingreso es {E['pac_num']['anios_consumo']['mediana']:.0f}.</p>
</div></section>

<section id="episodios" class="panel" role="tabpanel" aria-labelledby="tab-episodios" hidden><div class="wrap">
<h2><span class="num">Paso 3 · Descriptivo · episodios</span>Cómo transcurren los {NE} episodios</h2>
<p class="lede">{g(ec['motivo_hosp'],'Crisis')['pct']}% de los ingresos fue por crisis y solo {g(ec['motivo_hosp'],'Programa CETA')['pct']}% fue un ingreso programado al programa de rehabilitación. La mediana de estancia es {dias['mediana']:.0f} días (RIC {dias['q1']:.0f}–{dias['q3']:.0f}).</p>
<div class="grid2">
<figure><figcaption><b>Síntomas al ingreso</b><span class="src">episodios</span></figcaption>{hbar(E['epi_sintomas'],'--c3')}</figure>
<figure><figcaption><b>Último consumo antes del ingreso</b><span class="src">episodios</span></figcaption>{hbar(ec['ultimo_consumo'],'--c3')}</figure>
<figure><figcaption><b>Intervenciones farmacológicas</b><span class="src">episodios</span></figcaption>{hbar(E['epi_tx'],'--c2')}</figure>
<figure><figcaption><b>Interconsultas y estudios</b><span class="src">episodios</span></figcaption>{hbar([{"cat":l,"n":g(ec[c],'Sí')['n'],"pct":g(ec[c],'Sí')['pct']} for c,l in [("ic_trabajo_social","Trabajo social"),("laboratorios","Laboratorios"),("ic_psicologia","Psicología"),("ekg","Electrocardiograma"),("eeg","Electroencefalograma"),("ic_psiq_adicciones","Psiquiatría de adicciones")]],'--c2')}</figure>
<figure><figcaption><b>Motivo de egreso</b><span class="src">episodios</span></figcaption>{hbar(desc(ec['motivo_egreso']),'--c2')}</figure>
<figure><figcaption><b>Días de hospitalización</b><span class="src">episodios</span></figcaption>{hbar(ec['estancia_cat'],'--c2')}</figure>
</div>
<p>Prueba de metabolitos en orina: positiva en {g(ec['metabolitos_positivos'],'Sí')['pct']}%, negativa en {g(ec['metabolitos_positivos'],'No')['pct']}% y <b>no realizada en {g(ec['metabolitos_positivos'],'No se realizó')['pct']}%</b>. Reingreso en los 90 días posteriores: {g(ec['reingreso_90d'],'Sí')['pct']}% de los episodios. Diagnóstico principal de egreso: F19 en {g(ec['dx_egreso_cat'],'F19')['pct']}%, F10 en {g(ec['dx_egreso_cat'],'F10')['pct']}%, F12 en {g(ec['dx_egreso_cat'],'F12')['pct']}%.</p>
</div></section>

<section id="bivariado" class="panel" role="tabpanel" aria-labelledby="tab-bivariado" hidden><div class="wrap">
<h2><span class="num">Paso 4 · Bivariado</span>Qué se asocia con qué</h2>
<p class="lede">Primero se replican en Python los cruces del plan de análisis (χ² de Pearson o Fisher, OR con IC95%, Mann-Whitney, Kruskal-Wallis). Después se añade un cribado más amplio con corrección por comparaciones múltiples (FDR de Benjamini-Hochberg), que el protocolo no contemplaba pero que protege de falsos positivos.</p>
<h3>Bloque A · Policonsumo y presentación clínica <span class="chip">episodios, n={NE}</span></h3>
{table(["Exposición","Síntoma","Con vs sin exposición","OR (IC95%)","Prueba","p"], assoc_rows(A))}
<p>Ninguna asociación. El policonsumo está tan extendido ({g(pc['policonsumo'],'Sí')['pct']}%) que no discrimina. La droga de elección sí lo hace: droga × síntomas psicóticos V={multi[('droga_eleccion','sx_psicotico')]['cramer_v']} (p={pfmt(multi[('droga_eleccion','sx_psicotico')]['p'])}); droga × heteroagresión V={multi[('droga_eleccion','sx_heteroagresion')]['cramer_v']} (p={pfmt(multi[('droga_eleccion','sx_heteroagresion')]['p'])}).</p>
<h3>Bloques B y C · Vulnerabilidad psiquiátrica, violencia y conducta parasuicida <span class="chip">pacientes, n={NP}</span></h3>
{table(["Exposición","Desenlace","Con vs sin exposición","OR (IC95%)","Prueba","p"], assoc_rows(BC))}
<figure><figcaption><b>Cribado: conducta parasuicida</b><span class="src">pacientes · q = valor p ajustado por FDR · naranja = p&lt;0,05</span></figcaption>{forest(E['screen_parasuicida_pac'])}</figure>
<p>Depresión, trastorno de personalidad, violencia intrafamiliar y abuso sexual siguen siendo significativos tras la corrección. Dos hallazgos nuevos: el trastorno bipolar y los antecedentes legales se asocian a <em>menos</em> conducta parasuicida, lo que anticipa la separación en dos perfiles.</p>
<h3>Bloque D · Evolución hospitalaria</h3>
{table(["Motivo de egreso","n","Mediana de días","Q1","Q3"], [[esc(r['cat']), r['n'], f"{r['mediana']:.0f}", f"{r['q1']:.0f}", f"{r['q3']:.0f}"] for r in sorted(kw['grupos'],key=lambda r:-r['mediana'])])}
<p>Kruskal-Wallis H({kw['gl']}) = {kw['H']}, p&lt;0,001. La diferencia la explica el diseño del programa CETA (30 días) frente a las altas voluntarias (mediana 4 días).</p>
<figure><figcaption><b>Reingreso a 90 días según comorbilidad</b><span class="src">episodios, n={NE}</span></figcaption>{forest(D)}</figure>
<figure><figcaption><b>Cribado: reingreso a 90 días alguna vez</b><span class="src">pacientes, n={NP} · ajustado por FDR</span></figcaption>{forest(E['screen_reingreso_pac'])}</figure>
<div class="callout"><p><b>Lectura.</b> El trastorno bipolar es el único factor con señal de reingreso (OR {bip_ep['OR']} a nivel episodio, {bip_pac['OR']} a nivel paciente), pero con q={bip_pac['q_FDR']} tras corregir por las {len(E['screen_reingreso_pac'])} comparaciones no puede darse por establecido. Se reporta como hipótesis para un estudio con más eventos.</p></div>
<h3>Nuevo · Abandono del tratamiento <span class="chip">alta voluntaria, SSAM o expulsión · episodios</span></h3>
<figure><figcaption><b>Cribado: abandono del tratamiento</b><span class="src">episodios · ajustado por FDR</span></figcaption>{forest(abx)}</figure>
<p>Es el desenlace con más estructura de toda la base. Las pacientes con antipsicótico LAI, síntomas psicóticos, heteroagresión u hospitalización previa <em>se quedan</em>; las que tienen trastorno de personalidad o policonsumo <em>se van</em>. Cinco factores sobreviven la corrección FDR. Es candidato natural a un modelo multivariable.</p>
<h3>Comparaciones de variables numéricas</h3>
{table(["Grupo","Variable","Mediana Sí","Mediana No","p (Mann-Whitney)"], [[esc(m['grupo']),esc(m['var']),f"{m['mediana_si']:.0f}",f"{m['mediana_no']:.0f}",pfmt(m['p'])+sig(m['p'])] for m in E['biv_mw']])}
<h3>Mapa de asociaciones</h3>
<figure><figcaption><b>V de Cramér entre variables binarias</b><span class="src">pacientes · se rotulan V ≥ 0,20</span></figcaption>{heatmap(E['cramer_matrix']['labels'],E['cramer_matrix']['values'])}</figure>
</div></section>

<section id="clusters" class="panel" role="tabpanel" aria-labelledby="tab-clusters" hidden><div class="wrap">
<h2><span class="num">Paso 5 · Clustering</span>Dos perfiles clínicos</h2>
<p class="lede">Según el plan de análisis: {len(K['variables_entrada'])} variables sociodemográficas y clínicas de entrada (sin desenlaces), distancia de Gower para datos mixtos, k-medoides (PAM) y jerárquico, número de clústeres por silueta y codo, estabilidad por bootstrap.</p>
<div class="grid2">
<figure><figcaption><b>Elección de k</b><span class="src">coeficiente de silueta</span></figcaption>{silhouette(K['k_evaluados'])}</figure>
<figure><figcaption><b>Pacientes en dos dimensiones</b><span class="src">MDS sobre Gower · color = clúster</span></figcaption>{scatter(K['mds'])}</figure>
</div>
<div class="tiles">
<div class="tile"><div class="n">k = {K['k_elegido']}</div><div class="l">máxima silueta en PAM y jerárquico</div><div class="d">silueta {K['silueta']} (separación moderada)</div></div>
<div class="tile"><div class="n">{K['estabilidad_ARI']['media']}</div><div class="l">ARI medio en 50 remuestreos al 80%</div><div class="d">mín {K['estabilidad_ARI']['min']} · partición estable</div></div>
<div class="tile"><div class="n">{K['concordancia_pam_vs_jerarquico_ARI']}</div><div class="l">ARI PAM vs jerárquico</div><div class="d">dos métodos, misma estructura</div></div>
</div>
<div class="profiles">
<div class="profile"><div class="k">CLÚSTER 1 · n={c1n} · {c1n/NP*100:.0f}%</div><h4>Perfil afectivo-internalizante</h4>
<ul><li>Depresión {prof['T. depresivo']['1']:.0f}%, trastorno de personalidad {prof['T. personalidad']['1']:.0f}%, comorbilidad médica {prof['Comorbilidad médica']['1']:.0f}%</li>
<li>Intento suicida previo {prof['Intento suicida previo']['1']:.0f}%, autolesiones {prof['Conducta autolesiva']['1']:.0f}%</li>
<li>Casi sin psicosis ni heteroagresión al ingreso ({prof['Ideas delirantes (1er ingreso)']['1']:.0f}% / {prof['Heteroagresión (1er ingreso)']['1']:.0f}%)</li>
<li>{prof['Programa CETA (1er ingreso)']['1']:.0f}% entra directamente a CETA; ingreso familiar más alto</li>
<li>Desenlace ({K['episodios_por_cluster']['1']} episodios): {out['1']['alta_vol_pct']}% termina en alta voluntaria, SSAM o expulsión; reingreso a 90 días en {out['1']['reingreso_pct']}% de los episodios ({K['reingreso_episodios']['1']}/{K['episodios_por_cluster']['1']}) y en {prof['Reingreso 90 d (desenlace)']['1']:.0f}% de las pacientes ({K['reingreso_pacientes']['1']}/{c1n})</li></ul></div>
<div class="profile two"><div class="k">CLÚSTER 2 · n={c2n} · {c2n/NP*100:.0f}%</div><h4>Perfil psicótico-externalizante</h4>
<ul><li>Psicosis al ingreso {prof['Alt. sensoperceptuales (1er ingreso)']['2']:.0f}%, heteroagresión {prof['Heteroagresión (1er ingreso)']['2']:.0f}%, bipolaridad {prof['T. bipolar']['2']:.0f}%</li>
<li>Antecedentes legales {prof['Antecedentes legales']['2']:.0f}%, hospitalización previa {prof['Hospitalización previa TUS']['2']:.0f}%</li>
<li>Ingreso familiar &lt;500 en {prof['Ingreso <500']['2']:.0f}%; privadas de libertad o en situación de calle {K['convivencia_por_cluster']['2'].get('Privada de libertad',0)+K['convivencia_por_cluster']['2'].get('Situación de calle',0):.0f}%</li>
<li>Ningún ingreso programado a CETA</li>
<li>Desenlace ({K['episodios_por_cluster']['2']} episodios): LAI en {out['2']['lai_pct']}%, medicación de urgencia en {out['2']['urgencia_pct']}%; reingreso a 90 días en {out['2']['reingreso_pct']}% de los episodios ({K['reingreso_episodios']['2']}/{K['episodios_por_cluster']['2']}) y en {prof['Reingreso 90 d (desenlace)']['2']:.0f}% de las pacientes ({K['reingreso_pacientes']['2']}/{c2n}); {K['perfil_num']['Episodios (media)']['2']} episodios por paciente</li></ul></div>
</div>
<p>Lo que <em>no</em> separa a los perfiles es tan informativo como lo que sí: violencia intrafamiliar, abuso sexual, policonsumo, edad de inicio y droga de elección se distribuyen igual en ambos. El trauma y el consumo múltiple son el terreno común; lo que cambia es la forma clínica en que se expresan.</p>
<h3>Perfil completo</h3>
{prof_table}
<h3>Droga de elección por clúster</h3>
{table(["Droga","Clúster 1","Clúster 2"], drog_rows)}
<h3>Sensibilidad al conjunto de variables</h3>
<p>Para saber si la silueta de {K['silueta']} depende de qué variables entran, se repitió el análisis con distintos subconjuntos. El ARI mide cuánto coincide cada partición con la reportada.</p>
{table(["Conjunto de variables","Variables","k","Silueta","ARI vs reportado"], [[esc(r["conjunto"]), r["n_vars"], r["k"], r["silueta"], r["ARI_vs_reportado"]] for r in K["sensibilidad_variables"]])}
<p>Tres lecturas. Primera: quitar las variables nominales de muchas categorías (droga de elección, convivencia, ocupación, motivo) sube la silueta a {K["sensibilidad_variables"][1]["silueta"]} sin cambiar la partición (ARI {K["sensibilidad_variables"][1]["ARI_vs_reportado"]}): esas variables añaden ruido a la distancia de Gower, no estructura. Segunda: sin los síntomas del primer ingreso la estructura se desvanece (silueta {K["sensibilidad_variables"][4]["silueta"]}, ARI {K["sensibilidad_variables"][4]["ARI_vs_reportado"]}): la presentación psicótica es la columna vertebral de la separación. Tercera: el núcleo de 10 variables alcanza {K["sensibilidad_variables"][5]["silueta"]}, pero ese subconjunto se eligió <em>después</em> de ver qué discriminaba, así que es circular y no debe reportarse como resultado principal. El valor a reportar es el del conjunto preespecificado ({K['silueta']}), con la sensibilidad como apoyo.</p>
<div class="callout warn"><p><b>Cautela.</b> Una silueta de {K['silueta']} está en el límite de lo que Kaufman y Rousseeuw llaman «estructura débil» (0,26 a 0,50) y «sin estructura sustancial» (menor de 0,25); en datos clínicos mixtos con distancia de Gower es un valor habitual. La frase correcta para el texto final es <em>estructura débil pero estable y clínicamente interpretable</em>. La estabilidad alta y la coincidencia entre métodos sostienen que la partición es real, pero los perfiles son descriptivos y generadores de hipótesis, no categorías diagnósticas. Las diferencias en desenlaces (abandono p={pfmt(K['pruebas_p']['Abandono (alta vol/SSAM/expulsión)'])}, reingreso p={pfmt(K['pruebas_p']['Reingreso 90 d (episodios)'])}) son exploratorias.</p></div>
</div></section>

<section id="modelo" class="panel" role="tabpanel" aria-labelledby="tab-modelo" hidden><div class="wrap">
<h2><span class="num">Paso 6 · Modelo predictivo</span>¿Quién abandonará el tratamiento?</h2>
<p class="lede">De los tres desenlaces disponibles, el abandono del tratamiento (alta voluntaria, salida sin autorización médica o expulsión del programa) es el único con eventos suficientes y señal clara. Se construyó una regresión logística con seis predictores <em>conocidos en el momento del ingreso</em>, validada por remuestreo, y se tradujo a un puntaje de riesgo en puntos.</p>
<h3>Cómo se construyó</h3>
<ul class="plain">
<li><b>Desenlace.</b> {MO["M1"]["desenlace"]} en {MO["M1"]["n"]} episodios; {MO["M1"]["eventos"]} eventos ({MO["M1"]["eventos"]/MO["M1"]["n"]*100:.0f}%).</li>
<li><b>Predictores preespecificados por relevancia clínica</b>, no elegidos por significación: trastorno de personalidad, policonsumo activo, síntomas psicóticos al ingreso, hospitalización previa por TUS, ingreso programado a CETA y edad. Se excluyeron deliberadamente los tratamientos recibidos durante la estancia (LAI, medicación de urgencia) porque ocurren <em>después</em> del ingreso y en parte son consecuencia de quedarse: usarlos como predictores sería causalidad inversa.</li>
<li><b>Eventos por variable: {MO["M1"]["EPV"]}.</b> Está por debajo de los 10 que recomiendan Peduzzi et al. [21], así que el sobreajuste se midió y corrigió por bootstrap (Harrell) y el modelo se reporta con esa corrección.</li>
<li><b>Errores estándar robustos agrupados por paciente</b> (sandwich), porque 35 pacientes aportan más de un episodio. Los intervalos son más anchos y más honestos que los de un modelo que ignore esa dependencia.</li>
<li><b>Validación cruzada agrupada por paciente</b> (5 pliegues, 20 repeticiones): ningún episodio de una paciente cae en el conjunto de entrenamiento cuando otro episodio suyo está en el de prueba. Un bosque aleatorio se entrenó con el mismo esquema como comparador.</li>
<li>Reporte conforme a la guía TRIPOD [22]: discriminación, calibración, optimismo y muestra.</li>
</ul>
<figure><figcaption><b>Odds ratios ajustados</b><span class="src">n={MO["M1"]["n"]} episodios · EE robustos por paciente · naranja = p&lt;0,05</span></figcaption>{coef_forest(MO["M1"]["coeficientes"])}</figure>
<div class="tiles">
<div class="tile"><div class="n">{MO["M1"]["AUC_corregida_optimismo"]}</div><div class="l">AUC corregida por optimismo</div><div class="d">aparente {MO["M1"]["AUC_aparente"]} · optimismo {MO["M1"]["optimismo"]}</div></div>
<div class="tile"><div class="n">{MO["M1"]["CV_logistica"]["AUC_media"]}</div><div class="l">AUC en validación cruzada</div><div class="d">IC {MO["M1"]["CV_logistica"]["AUC_IC"][0]}–{MO["M1"]["CV_logistica"]["AUC_IC"][1]} · Brier {MO["M1"]["CV_logistica"]["Brier"]}</div></div>
<div class="tile"><div class="n">{MO["M1"]["CV_bosque"]["AUC_media"]}</div><div class="l">AUC del bosque aleatorio</div><div class="d">no supera a la logística</div></div>
<div class="tile"><div class="n">{MO["M1"]["pendiente_calibracion"]}</div><div class="l">pendiente de calibración</div><div class="d">1 = perfecta · &lt;1 = algo de sobreajuste</div></div>
</div>
<div class="grid2">
<figure><figcaption><b>Calibración</b><span class="src">quintiles de riesgo predicho (validación cruzada)</span></figcaption>{calib_chart(MO["M1"]["calibracion"], MO["M1"]["pendiente_calibracion"])}</figure>
<figure><figcaption><b>Riesgo observado por puntaje</b><span class="src">episodios</span></figcaption>{score_chart(MO["M1"]["puntaje"]["estratos"])}</figure>
</div>
<h3>Resumen de desempeño</h3>
{table(["Métrica","Valor","Lectura"], [
 ["Episodios / eventos", f'{MO["M1"]["n"]} / {MO["M1"]["eventos"]}', "Abandono en el 24% de los episodios"],
 ["Eventos por variable", MO["M1"]["EPV"], "Por debajo de 10: sobreajuste corregido por bootstrap"],
 ["AUC aparente", MO["M1"]["AUC_aparente"], "Sobre los mismos datos, optimista"],
 ["AUC corregida por optimismo", MO["M1"]["AUC_corregida_optimismo"], "Estimación honesta de la discriminación"],
 ["AUC en validación cruzada", f'{MO["M1"]["CV_logistica"]["AUC_media"]} (IC {MO["M1"]["CV_logistica"]["AUC_IC"][0]}–{MO["M1"]["CV_logistica"]["AUC_IC"][1]})', "Agrupada por paciente, 20 repeticiones"],
 ["AUC del bosque aleatorio", MO["M1"]["CV_bosque"]["AUC_media"], "No supera a la logística"],
 ["Brier", MO["M1"]["CV_logistica"]["Brier"], "0 = perfecto, 0,25 = azar con prevalencia 50%"],
 ["Pendiente de calibración", MO["M1"]["pendiente_calibracion"], "1 = perfecta, menor que 1 = predicciones algo extremas"],
 ["Pseudo R² de McFadden", MO["M1"]["pseudoR2_McFadden"], "Ajuste global modesto"],
 ["Prueba de razón de verosimilitud", pfmt(MO["M1"]["LR_test_p"]), "El modelo explica más que el azar"],
])}
<h3>Qué significa</h3>
<p>Un AUC de {MO["M1"]["AUC_corregida_optimismo"]} es discriminación <em>modesta</em>: el modelo ordena correctamente a una paciente que abandonará por delante de una que no en 7 de cada 10 pares. No sirve para decidir sobre una persona, pero sí para estratificar: en el estrato de puntaje más alto abandona el {MO["M1"]["puntaje"]["estratos"][-1]["riesgo_pct"]:.0f}% y en los dos más bajos nadie. Que el bosque aleatorio no mejore a la logística es lo esperado con {MO["M1"]["n"]} observaciones: los algoritmos flexibles necesitan muchos más datos para ganar, y aquí solo añaden varianza.</p>
<p>Dos predictores sostienen el modelo tras el ajuste mutuo: el <b>trastorno de personalidad</b> (OR {[c for c in MO["M1"]["coeficientes"] if c["variable"].startswith("Trastorno")][0]["OR"]}) y el <b>policonsumo activo</b> (OR {[c for c in MO["M1"]["coeficientes"] if c["variable"].startswith("Policonsumo")][0]["OR"]}). La hospitalización previa y los síntomas psicóticos reducen el riesgo, aunque con intervalos que cruzan 1 tras el ajuste. La lectura clínica es coherente con los dos perfiles: el perfil afectivo con rasgos de personalidad y consumo múltiple es el que se va; el perfil psicótico, con más contención y más historia institucional, se queda.</p>
<h3>Puntaje de riesgo al ingreso</h3>
{table(["Característica al ingreso","Puntos"], [[esc(k), f"{v:+d}" if v else "0"] for k,v in MO["M1"]["puntaje"]["puntos"].items() if k != "Edad (por 10 años)"])}
<p>Se suman los puntos (rango −3 a +6). Por debajo de 0 no hubo abandonos; de 2 a 3 puntos abandona una de cada tres; con 4 o más, casi la mitad. El puntaje se derivó de los coeficientes y <b>no ha sido validado en otra muestra</b>: es una herramienta de discusión, no un instrumento clínico.</p>
<h3>Los otros dos modelos</h3>
{table(["Modelo","Nivel","n / eventos","EPV","Predictores con p&lt;0,05 (OR ajustado)","AUC corregida"], [
 ["Conducta parasuicida","paciente",f'{MO["M2"]["n"]} / {MO["M2"]["eventos"]}',MO["M2"]["EPV"], ", ".join(f'{c["variable"]} ({c["OR"]})' for c in MO["M2"]["coeficientes"][1:] if c["p"]<0.05), f'{MO["M2"]["AUC_corregida_optimismo"]} (VC {MO["M2"]["CV_AUC"]})'],
 ["Reingreso a 90 días","paciente",f'{MO["M3"]["n"]} / {MO["M3"]["eventos"]}',MO["M3"]["EPV"], ", ".join(f'{c["variable"]} ({c["OR"]})' for c in MO["M3"]["coeficientes"][1:] if c["p"]<0.05), f'{MO["M3"]["AUC_corregida_optimismo"]}'],
])}
<p>El modelo de <b>conducta parasuicida</b> discrimina mejor (AUC {MO["M2"]["AUC_corregida_optimismo"]}) porque el desenlace es frecuente y sus determinantes son fuertes: tras ajustar, quedan la depresión (OR {[c for c in MO["M2"]["coeficientes"] if c["variable"]=="Trastorno depresivo"][0]["OR"]}) y la violencia intrafamiliar (OR {[c for c in MO["M2"]["coeficientes"] if c["variable"]=="Violencia intrafamiliar"][0]["OR"]}); el abuso sexual pierde significación al ajustar por violencia intrafamiliar, con la que se solapa. Los antecedentes legales se asocian a <em>menos</em> conducta parasuicida (OR {[c for c in MO["M2"]["coeficientes"] if c["variable"]=="Antecedentes legales"][0]["OR"]}), de nuevo la firma del perfil externalizante. El de <b>reingreso</b> tiene {MO["M3"]["eventos"]} eventos y apenas admite dos predictores; el trastorno bipolar cuadruplica las odds, pero el AUC de {MO["M3"]["AUC_corregida_optimismo"]} indica que con estas variables no se puede predecir quién reingresa.</p>
<div class="callout"><p><b>Uso responsable.</b> Un puntaje de riesgo de abandono sirve para <em>intensificar</em> el acompañamiento (psicología, trabajo social, plan de retención) en quienes puntúan alto, nunca para condicionar el acceso al tratamiento. El modelo se derivó en un solo centro con pocos eventos y necesita validación externa antes de cualquier uso asistencial.</p></div>
</div></section>

<section id="xai" class="panel" role="tabpanel" aria-labelledby="tab-xai" hidden><div class="wrap">
<h2><span class="num">Paso 7 · Explicabilidad</span>Por qué el modelo dice lo que dice</h2>
<p class="lede">Un modelo que solo entrega un número no sirve en clínica. Aquí se abre la caja: cuánto pesa cada variable en conjunto, cómo empuja el riesgo en cada episodio, qué habría cambiado el pronóstico de una paciente concreta, y una calculadora para probar escenarios.</p>
<h3>Método</h3>
<ul class="plain">
<li><b>Valores SHAP</b> [27]: reparten la predicción de cada episodio entre sus variables según los valores de Shapley de la teoría de juegos, la única atribución que cumple eficiencia, simetría y aditividad. Para la logística son exactos (β·(x − media)); para el bosque se usa TreeSHAP con la base completa como fondo.</li>
<li><b>Importancia por permutación</b> [28]: cuánto cae el AUC al barajar una variable. Es independiente del algoritmo y complementa a SHAP.</li>
<li><b>Contrafactuales</b> [29]: el cambio mínimo en una variable que más reduciría el riesgo de un episodio de alto riesgo.</li>
<li><b>Dependencia parcial</b> de la edad, la única variable continua, e <b>interacciones</b> SHAP del bosque.</li>
</ul>
<h3>Importancia global</h3>
<figure><figcaption><b>Peso de cada variable</b><span class="src">|SHAP| medio normalizado · pasa el cursor para ver la permutación</span></figcaption>{imp_chart(XA["importancia"])}</figure>
<p>Los dos modelos coinciden en lo esencial: <b>policonsumo, hospitalización previa y trastorno de personalidad</b> son las tres variables que más mueven el riesgo. Difieren en la edad: la logística casi la ignora (OR 0,96 por década) y el bosque le da peso por permutación, pero su dependencia parcial es plana y ruidosa, lo que apunta a sobreajuste del bosque y no a un efecto real. La correlación de Spearman entre los riesgos de ambos modelos es {XA["concordancia_modelos_spearman"]}.</p>
<h3>Cómo actúa cada variable episodio por episodio</h3>
<figure><figcaption><b>SHAP por episodio, regresión logística</b><span class="src">un punto = un episodio · color = valor de la variable</span></figcaption>{beeswarm(XA["beeswarm_logistica"])}</figure>
<p>La lectura es directa: tener policonsumo, trastorno de personalidad o un ingreso programado a CETA desplaza los puntos a la derecha (más riesgo); tener síntomas psicóticos o una hospitalización previa los desplaza a la izquierda. Como el policonsumo es tan frecuente ({int(XA["medias"]["Policonsumo activo"]*100)}% de los episodios), su ausencia es lo que más protege: los pocos episodios sin policonsumo reciben la contribución negativa más grande de toda la gráfica.</p>
<h3>Tres episodios explicados</h3>
<div class="examples">{"".join(waterfall(e) for e in XA["ejemplos"])}</div>
<h3>Contrafactuales del episodio A</h3>
<p>Si en el episodio de mayor riesgo se cambiara una sola característica, el riesgo pasaría de {XA["ejemplos"][0]["riesgo_logistica"]*100:.0f}% a:</p>
{table(["Cambio hipotético","Riesgo resultante"], [[esc(c["cambio"]), f'{c["riesgo"]*100:.0f}%'] for c in XA["contrafactuales_A"]])}
<p>Ninguna de estas variables es modificable en el momento del ingreso, así que el contrafactual no prescribe una acción sobre la paciente; muestra qué rasgos concentran el riesgo y por tanto dónde poner la intervención de retención: el consumo múltiple y la desregulación propia del trastorno de personalidad.</p>
<h3>Calculadora de riesgo</h3>
<p>Ajusta las características y observa el riesgo del modelo logístico y la contribución de cada variable respecto a una paciente promedio. Es una herramienta didáctica sobre un modelo no validado externamente.</p>
<div class="calc" id="calc">
<div class="calc-in">
<label><input type="checkbox" data-k="Trastorno de personalidad"> Trastorno de personalidad</label>
<label><input type="checkbox" data-k="Policonsumo activo" checked> Policonsumo activo</label>
<label><input type="checkbox" data-k="Síntomas psicóticos al ingreso"> Síntomas psicóticos al ingreso</label>
<label><input type="checkbox" data-k="Hospitalización previa por TUS"> Hospitalización previa por TUS</label>
<label><input type="checkbox" data-k="Ingreso programado a CETA"> Ingreso programado a CETA</label>
<label class="range">Edad <output id="calc-age-out">32</output> años<input type="range" min="18" max="75" value="32" data-k="Edad (años)" id="calc-age"></label>
</div>
<div class="calc-out"><div class="risk"><span class="n" id="calc-risk">–</span><span class="l">riesgo de abandono estimado<br><span class="muted" id="calc-pts"></span></span></div><div id="calc-bars"></div></div>
</div>
<div class="grid2">
<figure><figcaption><b>Dependencia parcial de la edad</b><span class="src">riesgo medio al fijar la edad en todos los episodios</span></figcaption>{pd_chart(XA["pd_edad"])}</figure>
<figure><figcaption><b>Interacciones (bosque)</b><span class="src">|SHAP de interacción| medio, escala de probabilidad</span></figcaption>{table(["Par de variables","Fuerza"], [[f'{esc(i["a"])} × {esc(i["b"])}', f'{i["fuerza"]:.3f}'] for i in XA["interacciones_bosque"]])}<p class="muted" style="font-size:13px;margin:0">Todas las interacciones son menores de 0,01 en probabilidad: el modelo es esencialmente aditivo, lo que justifica usar la logística como modelo final.</p></figure>
</div>
<div class="callout warn"><p><b>Qué explica y qué no.</b> SHAP explica el <em>modelo</em>, no la realidad: una contribución positiva significa que el modelo sube el riesgo con esa variable, no que la variable cause el abandono. El bosque alcanza AUC aparente {XA["AUC_aparente"]["bosque"]} sobre sus propios datos pero {MO["M1"]["CV_bosque"]["AUC_media"]} en validación cruzada: sus explicaciones incluyen ruido memorizado, y por eso las conclusiones se apoyan en la logística.</p></div>
</div></section>

<section id="ideas" class="panel" role="tabpanel" aria-labelledby="tab-ideas" hidden><div class="wrap">
<h2><span class="num">Propuestas · Lluvia de ideas</span>Qué hacer con esto</h2>
<p class="lede">Veintidós ideas ordenadas por urgencia: lo que la tesis necesita para sustentarse, lo que los datos permiten analizar además, lo que el INSAM podría cambiar y hacia dónde seguir.</p>
{ideas_html}
</div></section>

<section id="metodos" class="panel" role="tabpanel" aria-labelledby="tab-metodos" hidden><div class="wrap">
<h2><span class="num">Anexo · Métodos y reproducibilidad</span>Reproducibilidad y limitaciones</h2>
<h3>Pipeline</h3>
<ul class="plain">
<li><code>01_limpieza.py</code> → <code>pacientes_limpio.csv</code>, <code>episodios_limpio.csv</code>, <code>reporte_limpieza.json</code>.</li>
<li><code>02_eda.py</code> → <code>eda_resultados.json</code> y 16 gráficas PNG a 150 dpi en <code>graficas/</code>, listas para el documento Word.</li>
<li><code>03_clustering.py</code> → <code>cluster_resultados.json</code>, <code>pacientes_cluster.csv</code> y 4 gráficas.</li>
<li><code>05_modelo.py</code> → <code>modelo_resultados.json</code> y 3 gráficas (ROC y calibración, OR ajustados, puntaje).</li>
<li><code>06_xai.py</code> → <code>xai_resultados.json</code> y 5 gráficas (importancia, SHAP por episodio, ejemplos, dependencia parcial). Librería <code>shap</code> 0.48.</li>
<li><code>04_informe.py</code> → esta página. Python 3, pandas, scipy, scikit-learn, matplotlib. Semilla fija (42).</li>
</ul>
<h3>Decisiones metodológicas</h3>
<ul class="plain">
<li><b>Dos niveles de análisis.</b> Características fijas a nivel paciente; presentación, tratamiento y desenlace a nivel episodio. Los cruces a nivel episodio no son independientes (35 pacientes con más de un episodio) y se presentan como sensibilidad; en el modelo multivariable la dependencia se corrige con errores estándar agrupados por paciente [40].</li>
<li><b>Fisher cuando alguna frecuencia esperada es menor de 5.</b> OR con corrección de Haldane-Anscombe (0,5) cuando hay celdas en cero [35].</li>
<li><b>FDR de Benjamini-Hochberg</b> [36] en los cribados, con q&lt;0,05 como umbral: controla la proporción esperada de falsos positivos entre los hallazgos declarados, menos conservador que Bonferroni y adecuado para análisis exploratorios.</li>
<li><b>Distancia de Gower</b> [30]: la métrica de referencia para datos mixtos [45]; pondera igual variables numéricas (rango), ordinales, binarias y nominales. PAM (k-medoides) es el algoritmo de partición recomendado sobre distancias precomputadas porque, a diferencia de k-means, no requiere medias euclidianas y es robusto a atípicos [32]. Los desenlaces se excluyeron del clustering y solo se usaron para caracterizar.</li>
<li><b>k por silueta</b> [31] en un rango de 2 a 8, confirmado con el codo; estabilidad por remuestreo (50 submuestras al 80%, Hennig [34]) medida con el índice de Rand ajustado [33] frente a la partición completa.</li>
<li><b>Modelo predictivo</b>: predictores preespecificados, validación interna por bootstrap con corrección de optimismo [37,38] y validación cruzada agrupada, calibración reportada [42], eventos por variable declarados [21,39] y reporte según TRIPOD [22]. La superioridad no demostrada del bosque aleatorio es el hallazgo esperado en muestras clínicas pequeñas [43].</li>
</ul>

<h3>Lista de verificación STROBE</h3>
<p>Estado de los ítems de la declaración STROBE para estudios observacionales [46] que dependen del análisis. Los ítems de introducción y contexto los cubre el protocolo.</p>
{table(["Ítem STROBE","Estado","Dónde"], [
 ["4 Diseño","Cumplido","Observacional, retrospectivo, censo; protocolo v2.0"],
 ["5 Contexto y fechas","Cumplido","INSAM, oct 2022 a oct 2025"],
 ["6 Participantes y criterios","Cumplido","Criterios de inclusión y exclusión del protocolo; validación en pestaña Limpieza"],
 ["7 Variables","Parcial","Definidas en el protocolo; faltan fechas, vía y frecuencia de consumo, tomografía y seguimiento (ver Limitaciones)"],
 ["9 Sesgos","Cumplido","Dependencia entre episodios, reingreso solo al INSAM, sesgo de registro (ver Métodos y Limitaciones)"],
 ["10 Tamaño de muestra","Cumplido","Censo sin cálculo; eventos por variable declarados en el modelo"],
 ["12 Métodos estadísticos","Cumplido","Pestañas Métodos, Bivariado, Perfiles y Modelo"],
 ["13 Flujo de participantes","<b>Pendiente</b>","Falta el diagrama 150 → 118 con motivos de exclusión"],
 ["14 Datos descriptivos","Cumplido","Pestañas Pacientes y Episodios"],
 ["16 Resultados principales con IC","Cumplido","OR con IC95% en todas las tablas bivariadas y en el modelo"],
 ["17 Otros análisis","Cumplido","Sensibilidad por nivel de análisis y por conjunto de variables"],
 ["19 Limitaciones","Cumplido","Sección Limitaciones"],
 ["21 Generalización","Cumplido","Un centro de referencia nacional; validación externa pendiente (Ideas)"],
 ["22 Financiación","Cumplido","Protocolo: donación de tiempo, sin patrocinio"]])}
<h3>Glosario</h3>
{table(["Término","Qué mide","Cómo leerlo aquí"], [
 ["Odds ratio (OR)","Cuántas veces mayores son las odds del desenlace en expuestas frente a no expuestas","OR 2 duplica las odds; el IC95% que cruza 1 no permite descartar ausencia de asociación"],
 ["Valor q (FDR)","Valor p ajustado por comparaciones múltiples [36]","q&lt;0,05: menos de 5% de los hallazgos declarados serían falsos positivos"],
 ["V de Cramér","Fuerza de asociación entre categóricas, de 0 a 1","0,1 pequeña, 0,3 media, 0,5 grande"],
 ["Distancia de Gower","Disimilitud entre pacientes con variables mixtas, de 0 a 1 [30]","0 = idénticas en todas las variables"],
 ["Silueta","Cohesión dentro del clúster frente a separación del más cercano, de −1 a 1 [31]","&lt;0,25 sin estructura sustancial; 0,26 a 0,50 débil; &gt;0,50 razonable [32]"],
 ["ARI (índice de Rand ajustado)","Coincidencia entre dos particiones corregida por azar [33]","1 = idénticas; 0 = lo esperable por azar"],
 ["AUC","Probabilidad de que el modelo ordene un caso por delante de un no caso [47]","0,5 azar; 0,7 a 0,8 aceptable; &gt;0,8 excelente [44]"],
 ["Optimismo","Cuánto sobreestima el AUC aparente por evaluarse en los mismos datos [37]","Se resta al AUC aparente para obtener el corregido"],
 ["Pendiente de calibración","Relación entre riesgo predicho y observado [42]","1 ideal; &lt;1 predicciones demasiado extremas (sobreajuste)"],
 ["Eventos por variable (EPV)","Eventos del desenlace por cada predictor [21,39]","&lt;10 exige penalización o corrección por bootstrap"],
 ["SHAP","Contribución de cada variable a la predicción individual, según valores de Shapley [27]","Positivo sube el riesgo del modelo; no implica causalidad"]])}
<h3>Limitaciones</h3>
<ul class="plain">
<li>Retrospectivo, un solo centro, {NP} pacientes: los intervalos de confianza son amplios y varias celdas son pequeñas (TDAH, esquizoafectivo).</li>
<li>Sin fechas de ingreso y egreso no hay análisis de tiempo hasta el reingreso; sin vía ni frecuencia de consumo no se cubre por completo el objetivo 2 del protocolo.</li>
<li>El reingreso a 90 días solo captura reingresos al INSAM.</li>
<li>La prueba de metabolitos faltó en {g(ec['metabolitos_positivos'],'No se realizó')['pct']}% de los episodios, así que el «policonsumo activo» descansa en el interrogatorio.</li>
<li>El clustering tiene separación moderada; los perfiles deben validarse en otra muestra.</li>
</ul>
</div></section>
<section id="defensa" class="panel" role="tabpanel" aria-labelledby="tab-defensa" hidden><div class="wrap">
<h2><span class="num">Anexo · Respuestas a posibles dudas</span>Respuestas a posibles dudas</h2>
<p class="lede">Diez dudas que surgieron al revisar este informe, respondidas con los números exactos y la referencia metodológica que las sostiene. Sirven para anticipar las preguntas más probables.</p>
<h3>Separación de los clústeres</h3>
<details open class="faq"><summary>1. ¿La silueta de {K['silueta']} es una separación real aunque débil, o hay que matizarla?</summary>
<p>Hay que matizarla. Rousseeuw definió el coeficiente de silueta [31] y Kaufman y Rousseeuw propusieron la lectura habitual: más de 0,70 estructura fuerte, 0,51 a 0,70 razonable, 0,26 a 0,50 débil y menos de 0,25 sin estructura sustancial [32]. El valor de {K['silueta']} está en la frontera entre las dos últimas. Lo que autoriza a hablar de una partición y no de ruido no es la silueta sino tres apoyos independientes: la estabilidad por remuestreo (ARI {K['estabilidad_ARI']['media']} en 50 submuestras al 80%, el procedimiento de Hennig [34]), la coincidencia entre dos algoritmos distintos (ARI {K['concordancia_pam_vs_jerarquico_ARI']} entre PAM y jerárquico, medida con el índice de Hubert y Arabie [33]) y la validez externa: los perfiles difieren en desenlaces que no entraron al clustering, como el abandono (p={pfmt(K['pruebas_p']['Abandono (alta vol/SSAM/expulsión)'])}). Frase recomendada para el texto final: <em>estructura débil pero estable y clínicamente interpretable</em>. En datos clínicos mixtos con distancia de Gower las siluetas rara vez superan 0,30 [30,45].</p></details>
<details class="faq"><summary>2. ¿Se probó con otro número de variables o quitando las ruidosas? ¿0,244 es el valor final?</summary>
<p>Sí, se probó después de la pregunta, y el resultado está en la tabla de sensibilidad de la pestaña Perfiles. Sin las variables nominales de muchas categorías la silueta sube a {K["sensibilidad_variables"][1]["silueta"]} con la misma partición (ARI {K["sensibilidad_variables"][1]["ARI_vs_reportado"]}); sin los síntomas del primer ingreso la estructura desaparece (silueta {K["sensibilidad_variables"][4]["silueta"]}, ARI {K["sensibilidad_variables"][4]["ARI_vs_reportado"]}); un núcleo de 10 variables alcanza {K["sensibilidad_variables"][5]["silueta"]}, pero ese subconjunto se eligió tras ver qué discriminaba y reportarlo como principal sería circular, un sesgo de selección post hoc equivalente al que la corrección FDR evita en el bivariado [36]. <b>El valor a reportar es {K['silueta']}</b>, el del conjunto preespecificado en el protocolo, con la sensibilidad en un párrafo de apoyo.</p></details>
<h3>Reingreso a 90 días</h3>
<details class="faq"><summary>3. Las cifras de reingreso no coinciden entre tarjetas y tabla. ¿Cuál usar?</summary>
<p>Son dos unidades de análisis. Las tarjetas usan el episodio y la tabla la paciente. Como el clúster es un atributo de la paciente, la cifra principal debe ser <b>por paciente</b>: {prof['Reingreso 90 d (desenlace)']['1']:.0f}% en el clúster 1 y {prof['Reingreso 90 d (desenlace)']['2']:.0f}% en el clúster 2, con la de episodios como complemento. Ambas quedan ahora etiquetadas en las tarjetas de perfil.</p></details>
<details class="faq"><summary>4. ¿Sobre cuántos episodios se calculó cada cifra?</summary>
{table(["Clúster","Pacientes","Episodios","Reingreso por paciente","Reingreso por episodio"], [
 ["1 · afectivo-internalizante", c1n, K['episodios_por_cluster']['1'], f"{K['reingreso_pacientes']['1']}/{c1n} ({prof['Reingreso 90 d (desenlace)']['1']:.0f}%)", f"{K['reingreso_episodios']['1']}/{K['episodios_por_cluster']['1']} ({out['1']['reingreso_pct']}%)"],
 ["2 · psicótico-externalizante", c2n, K['episodios_por_cluster']['2'], f"{K['reingreso_pacientes']['2']}/{c2n} ({prof['Reingreso 90 d (desenlace)']['2']:.0f}%)", f"{K['reingreso_episodios']['2']}/{K['episodios_por_cluster']['2']} ({out['2']['reingreso_pct']}%)"]])}
<p>Cada paciente pertenece a un solo clúster y aporta todos sus episodios a él; por eso el clúster 2, con menos pacientes, tiene más episodios ({K['perfil_num']['Episodios (media)']['2']} por paciente frente a {K['perfil_num']['Episodios (media)']['1']}).</p></details>
<h3>Valores p</h3>
<details class="faq"><summary>5. Varias filas de la tabla de perfiles aparecían sin valor p. ¿Fue intencional?</summary>
<p>No, fue una omisión en el código, ya corregida. Los valores son: programa CETA p{pfmt(K['pruebas_p']['Programa CETA (1er ingreso)']).replace('<','&lt;') if K['pruebas_p']['Programa CETA (1er ingreso)']<0.001 else '='+pfmt(K['pruebas_p']['Programa CETA (1er ingreso)'])}, ingreso familiar menor de 500 p{'&lt;0,001' if K['pruebas_p']['Ingreso <500']<0.001 else '='+pfmt(K['pruebas_p']['Ingreso <500'])}, intentos suicidas p{'&lt;0,001' if K['pruebas_p']['Intentos suicidas']<0.001 else '='+pfmt(K['pruebas_p']['Intentos suicidas'])}, episodios por paciente p={pfmt(K['pruebas_p']['Episodios'])}, desempleada p={pfmt(K['pruebas_p']['Desempleada'])}, inicio antes de los 15 p={pfmt(K['pruebas_p']['Inicio <15 años'])} y cuatro o más sustancias p={pfmt(K['pruebas_p']['≥4 sustancias'])}. Se usó χ² para proporciones y Kruskal-Wallis para medianas. Todas estas comparaciones son descriptivas: las variables de entrada difieren entre clústeres por construcción, así que sus p no prueban nada más que la separación que el algoritmo buscó.</p></details>
<details class="faq"><summary>6. ¿Por qué el reingreso no tenía p? ¿Se calculó algún test?</summary>
<p>Se excluyó del clustering como desenlace, pero el test sí se calculó y no se mostraba por un error de la tabla. Por paciente p={pfmt(K['pruebas_p']['Reingreso 90 d (desenlace)'])} y por episodio p={pfmt(K['pruebas_p']['Reingreso 90 d (episodios)'])}. Se reporta descriptivamente: la dirección (más reingreso en el perfil psicótico) coincide con la literatura sobre manía y psicosis como predictores de reingreso [4,6], pero con 22 pacientes reingresadas el estudio no tiene potencia para demostrarlo.</p></details>
<h3>Modelo de abandono</h3>
<details class="faq"><summary>7. ¿Qué definió exactamente «abandono»?</summary>
<p>La unión de tres motivos de egreso: alta voluntaria, salida sin autorización médica (SSAM) y expulsión del programa CETA. Son {MO['M1']['eventos']} de {MO['M1']['n']} episodios ({MO['M1']['eventos']/MO['M1']['n']*100:.0f}%). Se agrupan porque los tres representan una interrupción del tratamiento no indicada por el equipo, que es el constructo que la literatura llama alta contra consejo médico o abandono [1,16].</p></details>
<details class="faq"><summary>8. ¿Qué modelo y qué variables?</summary>
<p>Regresión logística por máxima verosimilitud con errores estándar robustos agrupados por paciente (estimador sandwich de Williams [40]), porque 35 pacientes aportan más de un episodio. Seis predictores fijados por criterio clínico antes de mirar los resultados, todos disponibles en el momento del ingreso: trastorno de personalidad, policonsumo activo, síntomas psicóticos, hospitalización previa por TUS, ingreso programado a CETA y edad. Se excluyeron el LAI y la medicación de urgencia por ocurrir después del ingreso. Un bosque aleatorio se entrenó con el mismo esquema solo como comparador; no mejora (AUC {MO['M1']['CV_bosque']['AUC_media']} frente a {MO['M1']['CV_logistica']['AUC_media']}), lo que coincide con la revisión sistemática de Christodoulou et al., que no encontró ventaja del aprendizaje automático sobre la logística en modelos clínicos [43].</p></details>
<details class="faq"><summary>9. ¿Cómo se validó el AUC con una muestra tan pequeña?</summary>
<p>El n del modelo es {MO['M1']['n']} episodios, no 118 pacientes, con {MO['M1']['eventos']} eventos. Una partición única entrenamiento/prueba sería inestable con este tamaño [38,41], así que se usaron dos métodos de remuestreo, ambos recomendados por TRIPOD [22]. Primero, validación cruzada de 5 pliegues agrupada por paciente y repetida 20 veces, de modo que los episodios de una misma paciente nunca quedan a ambos lados: AUC {MO['M1']['CV_logistica']['AUC_media']} (IC {MO['M1']['CV_logistica']['AUC_IC'][0]} a {MO['M1']['CV_logistica']['AUC_IC'][1]}). Segundo, corrección por optimismo con bootstrap según Harrell [37]: AUC aparente {MO['M1']['AUC_aparente']} menos optimismo {MO['M1']['optimismo']} = <b>{MO['M1']['AUC_corregida_optimismo']}</b>. Los eventos por variable son {MO['M1']['EPV']}, por debajo de los 10 de Peduzzi [21] y del criterio más reciente de Riley et al. [39]; por eso el optimismo se midió en lugar de asumirse y la pendiente de calibración ({MO['M1']['pendiente_calibracion']}) se reporta como indicador de sobreajuste [42]. Un AUC de 0,7 a 0,8 se considera discriminación aceptable según Hosmer y Lemeshow [44].</p></details>
<details class="faq"><summary>10. ¿El modelo va en el trabajo final o es exploratorio?</summary>
<p>Recomendación del asesor metodológico: <b>análisis exploratorio adicional, no resultado central</b>. El protocolo aprobado (CBIHN-2026020002) promete análisis descriptivo, bivariado y clustering; la predicción no está en el plan y presentarla como objetivo sería una desviación del protocolo. Propuesta concreta: un párrafo en resultados con la tabla de OR ajustados y el AUC corregido, la interpretación en discusión vinculada a los dos perfiles, y el detalle completo (calibración, puntaje, SHAP) en un anexo o reservado para el artículo. La decisión es de la investigadora y de la asesora clínica.</p></details>
</div></section>

<section id="literatura" class="panel" role="tabpanel" aria-labelledby="tab-literatura" hidden><div class="wrap">
<h2><span class="num">Anexo · Literatura</span>Contraste con la evidencia publicada</h2>
<p class="lede">Cada hallazgo principal se confrontó con revisiones sistemáticas, metaanálisis y cohortes comparables. La columna de veredicto distingue lo que replica evidencia previa, lo que la matiza y lo que es genuinamente nuevo para Panamá.</p>
{table(["Hallazgo en el INSAM","Qué dice la literatura","Veredicto"], [
 ["<b>Violencia intrafamiliar en el 81% y abuso sexual en el 55%</b> de las pacientes.", "En 343 mujeres con TUS y TEPT en tratamiento, 93% reportó algún abuso o negligencia infantil y 7 de cada 10 abuso sexual moderado o grave [11]. En 145 mujeres drogodependientes españolas, la prevalencia total de maltrato psicológico y abuso sexual fue 63% [12]. La revisión regional de mujeres consumidoras en América Latina documenta la violencia como constante en las trayectorias de consumo [25].", '<span class="chip">Concordante</span> Las cifras del INSAM están en el rango alto de lo publicado, comparable a muestras clínicas con trauma.'],
 ["<b>Conducta parasuicida en el 64%</b>; intento suicida previo en 54%. La violencia intrafamiliar (OR ajustado 5,5) y la depresión (OR 5,2) son sus principales correlatos.", "Metaanálisis global: la violencia de pareja multiplica por 2,2 a 5,5 las odds de suicidalidad en mujeres [14]. Revisión de metaanálisis: el abuso sexual infantil se asocia a intento suicida con OR mediana 2,7 (rango 1,9 a 4,1) [15].", '<span class="chip">Concordante</span> El OR del INSAM para violencia intrafamiliar cae dentro del rango metaanalítico; el del abuso sexual (bivariado 2,9) coincide con la OR mediana publicada.'],
 ["<b>El abuso sexual se asocia a inicio más temprano del consumo</b> (mediana 14 vs 15 años, p&lt;0,001).", "Perfiles de trauma grave inician el consumo unos 3 años antes que los de trauma bajo [11]; el inicio problemático antes de los 18 es el doble en mujeres con antecedentes traumáticos (21,5% vs 10%) [12]; el efecto telescoping describe una progresión acelerada en mujeres [protocolo, ref. 6].", '<span class="chip">Concordante</span> Misma dirección, efecto más pequeño en el INSAM, quizá porque casi todas inician en la adolescencia (mediana 15) y hay poco margen.'],
 ["<b>Dos perfiles</b>: afectivo-internalizante (56%) y psicótico-externalizante (44%). Ambos comparten trauma y policonsumo.", "La tipología A/B de Babor separa un tipo de inicio tardío, menor gravedad y menos comorbilidad de un tipo B de inicio temprano, policonsumo, conducta antisocial y más comorbilidad; se ha replicado en cocaína, opiáceos y cannabis, y las mujeres caen con más frecuencia en el tipo A [7,8]. El modelo HiTOP formaliza los espectros internalizante, externalizante y de trastorno del pensamiento como estructura de la comorbilidad [9,10]. En tratamiento residencial, el subtipo internalizante funciona peor al ingreso y el externalizante tiene peores procesos y resultados de tratamiento [18]. En pacientes psiquiátricos hospitalizados, un análisis de clústeres encontró un subgrupo internalizante afectivo, uno externalizante intoxicado al ingreso y uno psicótico con mala adherencia [26].", '<span class="chip">Concordante con matiz</span> La estructura internalizante/externalizante replica la literatura. La diferencia: en el INSAM el eje externalizante viene marcado por psicosis, bipolaridad y antecedentes legales más que por policonsumo, que es transversal.'],
 ["<b>El abandono del tratamiento</b> (24% de los episodios) se predice por trastorno de personalidad (OR 2,5) y policonsumo (OR 3,8).", "Revisión de alta contra consejo médico en psiquiatría: prevalencia de 3% a 51%; predictores más consistentes son edad joven, estar soltera, trastorno de personalidad (antisocial, límite, paranoide), trastorno por sustancias y conducta disruptiva [1]. En un programa de buprenorfina, el policonsumo al ingreso y los rasgos antisociales predijeron independientemente la salida involuntaria [2]. En 21 378 mujeres chilenas, 54% abandonó y solo 24% completó el tratamiento [16]. Un análisis de clases latentes en tratamiento residencial vincula las clases de psicopatología con el abandono [24].", '<span class="chip">Concordante</span> Mismos predictores. La edad no fue predictor en el INSAM, probablemente por el rango restringido (mediana 32 años).'],
 ["<b>La hospitalización previa por TUS protege del abandono</b> (OR ajustado 0,43, p=0,07) y los síntomas psicóticos también (bivariado OR 0,26).", "La revisión de Brook et al. señala lo contrario: una historia de múltiples hospitalizaciones terminadas en alta voluntaria predice nuevas altas voluntarias [1].", '<span class="chip sig">Discordante</span> Hallazgo local que merece explicación: en el INSAM la hospitalización previa marca al perfil psicótico, que recibe más contención, LAI y manejo involuntario. Es un efecto del contexto institucional, no un factor protector en sí.'],
 ["<b>Reingreso a 90 días en 18% de los episodios</b>; el trastorno bipolar cuadruplica las odds, pero la hospitalización previa no se asocia.", "Reingreso a 30 días agrupado en salas psiquiátricas agudas: 16% (IC 13 a 20) [5]; 25% a 30 días en pacientes con TUS [3]; 41% a 12 meses en un servicio de adicciones suizo, donde psicosis o manía (OR 1,9) y sobre todo 4 o más ingresos previos (OR 5,4) predijeron el reingreso [4]. En bipolares, 3 o más hospitalizaciones previas, falta de seguro y situación de calle predicen reingreso a 30 y 90 días [6].", '<span class="chip">Parcialmente concordante</span> La tasa y el papel de la manía o bipolaridad coinciden. Que la hospitalización previa no prediga reingreso es discordante y probablemente refleja pocos eventos (22) y que el reingreso solo se capta si ocurre en el INSAM.'],
 ["<b>El policonsumo no se asocia a los síntomas del ingreso</b>; la droga de elección sí (V≈0,4 con psicosis y heteroagresión).", "En una cohorte de 561 pacientes con TUS, el policonsumo (42%) no se asoció de forma independiente al reingreso [3]. Alrededor de la mitad de los dependientes de cocaína refieren síntomas psicóticos durante la intoxicación [19,20] y la psicosis por metanfetamina cursa con delirios persecutorios y hostilidad en la mayoría de los estudios [20].", '<span class="chip">Concordante</span> Lo que importa clínicamente es qué se consume, no cuántas sustancias. El instrumento del INSAM no registró vía ni frecuencia, lo que limita esta línea.'],
 ["<b>El antipsicótico de acción prolongada</b> se asocia a permanecer hasta el alta (OR bivariado 0,05).", "Revisiones sistemáticas en esquizofrenia con TUS comórbido: los LAI mejoran la adherencia y reducen hospitalizaciones, aunque la evidencia es heterogénea [23].", '<span class="chip">Concordante con cautela</span> En el INSAM el LAI se pone durante la estancia, así que la asociación es en parte inversa (quien se va temprano no lo recibe). Por eso se excluyó del modelo predictivo.'],
 ["<b>Perfil femenino predominantemente internalizante</b>: depresión 36%, trastorno de personalidad 30%, bipolar 24%.", "En 142 pacientes residenciales españoles, las mujeres presentaron más depresión mayor (27% vs 11%), distimia (46% vs 15%) y patrones dependientes de personalidad; los hombres, más patrón antisocial [25b]. La revisión de Greenfield et al. describe mayor comorbilidad psiquiátrica y barreras de acceso en mujeres [17].", '<span class="chip">Concordante</span> Respalda que el clúster afectivo sea mayoritario y que el programa CETA lo reciba con más frecuencia.'],
])}
<div class="callout"><p><b>Lo que aporta este estudio.</b> No existía una descripción publicada de mujeres hospitalizadas por TUS en Panamá. Sobre ese vacío, tres resultados son propios: la magnitud del trauma en esta población (por encima de la mayoría de las series europeas), la coexistencia de un perfil psicótico-externalizante con alto contacto legal y pobreza extrema, y un puntaje de abandono construido solo con variables del ingreso. Los tres son hipótesis que un estudio prospectivo o multicéntrico debería confirmar.</p></div>
<h3>Referencias</h3>
<p class="muted" style="font-size:14px;max-width:70ch">1 a 29: evidencia clínica. 30 a 47: métodos estadísticos citados en las pestañas Métodos, Modelo, XAI y Dudas.</p>
<ol class="refs">
<li>Brook M, Hilty DM, Liu W, Hu R, Frye MA. Discharge against medical advice from inpatient psychiatric treatment: a literature review. <i>Psychiatr Serv</i>. 2006;57(8):1192–1198. <a href="https://pubmed.ncbi.nlm.nih.gov/16870972/">PubMed</a></li>
<li>Öhlin L, Hesse M, Fridell M, Tätting P. Poly-substance use and antisocial personality traits at admission predict cumulative retention in a buprenorphine programme with mandatory work and high compliance profile. <i>BMC Psychiatry</i>. 2011;11:81. <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3112080/">PMC</a></li>
<li>Ssentongo P, Nunez J, Dissinger D, Bali B. Rates and factors for 30-day readmission in patients with substance use disorders during the COVID-19 pandemic. <i>Front Psychiatry</i>. 2025;16:1654157. <a href="https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2025.1654157/full">Frontiers</a></li>
<li>Böckmann V, Lay B, Seifritz E, Kawohl W, Roser P, Habermeyer B. Patient-level predictors of psychiatric readmission in substance use disorders. <i>Front Psychiatry</i>. 2019;10:828. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC6988786/">PMC</a></li>
<li>Muhammad N, Talpur S, Sangroula N, Washdave FNU. Independent predictors of 30-day readmission to acute psychiatric wards in patients with mental disorders: a systematic review and meta-analysis. <i>Cureus</i>. 2023;15(7):e42490. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10453981/">PMC</a></li>
<li>Hamilton JE, Passos IC, Cardoso TA, et al. Predictors of psychiatric readmission among patients with bipolar disorder at an academic safety-net hospital. <i>Aust N Z J Psychiatry</i>. 2016;50(6):584–593. <a href="https://journals.sagepub.com/doi/10.1177/0004867415605171">SAGE</a></li>
<li>Ball SA. Type A and Type B alcoholism: applicability across subpopulations and treatment settings. <i>Alcohol Health Res World</i>. 1996;20(1):30–35. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC6876529/">PMC</a></li>
<li>Babor TF, Hofmann M, DelBoca FK, et al. Types of alcoholics, I: evidence for an empirically derived typology based on indicators of vulnerability and severity. <i>Arch Gen Psychiatry</i>. 1992;49(8):599–608.</li>
<li>Krueger RF, Hobbs KA, Conway CC, et al. Validity and utility of Hierarchical Taxonomy of Psychopathology (HiTOP): II. Externalizing superspectrum. <i>World Psychiatry</i>. 2021;20(2):171–193. <a href="https://onlinelibrary.wiley.com/doi/full/10.1002/wps.20844">Wiley</a></li>
<li>Kotov R, Krueger RF, Watson D, et al. The Hierarchical Taxonomy of Psychopathology (HiTOP): a dimensional alternative to traditional nosologies. <i>J Abnorm Psychol</i>. 2017;126(4):454–477. <a href="https://www.apa.org/pubs/journals/features/abn-abn0000258.pdf">APA</a></li>
<li>Lotzin A, Grundmann J, Hiller P, Pawils S, Schäfer I. Profiles of childhood trauma in women with substance use disorders and comorbid posttraumatic stress disorders. <i>Front Psychiatry</i>. 2019;10:674. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC6813657/">PMC</a></li>
<li>Santos Goñi MA, García Colmenero L, Bernardo Carrasco A, Quijano Arenas E, Sánchez Pardo L. Antecedentes traumáticos en mujeres drogodependientes: abuso sexual, físico y psicológico. <i>Trastornos Adictivos</i>. 2010;12(3):109–117. <a href="https://www.elsevier.es/es-revista-trastornos-adictivos-182-articulo-antecedentes-traumaticos-mujeres-drogodependientes-abuso-S1575097310700210">Elsevier</a></li>
<li>Pan Y, Lin X, Liu J, et al. Prevalence of childhood sexual abuse among women using the Childhood Trauma Questionnaire: a worldwide meta-analysis. <i>Trauma Violence Abuse</i>. 2021;22(5):1181–1191. <a href="https://dx.doi.org/10.1177/1524838020912867">DOI</a></li>
<li>White SJ, Sin J, Sweeney A, et al. Global prevalence and mental health outcomes of intimate partner violence among women: a systematic review and meta-analysis. <i>Trauma Violence Abuse</i>. 2024;25(1):494–511. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10666489/">PMC</a></li>
<li>The impact of childhood sexual, physical and emotional abuse and neglect on suicidal behavior and non-suicidal self-injury: a systematic review of meta-analyses. 2025. <a href="https://www.sciencedirect.com/science/article/pii/S2772598725000017">ScienceDirect</a></li>
<li>Olivari CF, Gaete J, Rodriguez N, et al. Treatment outcome and readmission risk among women in women-only versus mixed-gender drug treatment programs in Chile. <i>J Subst Abuse Treat</i>. 2022;134:108616. <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9052114/">PMC</a></li>
<li>Greenfield SF, Brooks AJ, Gordon SM, et al. Substance abuse treatment entry, retention, and outcome in women: a review of the literature. <i>Drug Alcohol Depend</i>. 2007;86(1):1–21. <a href="https://pubmed.ncbi.nlm.nih.gov/16759822/">PubMed</a></li>
<li>Blonigen DM, Timko C, Jacob T, Moos RH. Internalizing and externalizing personality subtypes predict differences in functioning and outcomes among veterans in residential substance use disorder treatment. <i>Psychol Assess</i>. 2015;27(4):1394–1404. <a href="https://www.researchgate.net/publication/282978853">ResearchGate</a></li>
<li>Sabe M, Zhao N, Kaiser S. A systematic review and meta-analysis of the prevalence of cocaine-induced psychosis in cocaine users. <i>Prog Neuropsychopharmacol Biol Psychiatry</i>. 2021;109:110263. <a href="https://www.sciencedirect.com/science/article/pii/S0278584621000221">ScienceDirect</a></li>
<li>Wearne TA, Cornish JL. A comparison of methamphetamine-induced psychosis and schizophrenia: a review of positive, negative, and cognitive symptomatology. <i>Front Psychiatry</i>. 2018;9:491. <a href="https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2018.00491/full">Frontiers</a></li>
<li>Peduzzi P, Concato J, Kemper E, Holford TR, Feinstein AR. A simulation study of the number of events per variable in logistic regression analysis. <i>J Clin Epidemiol</i>. 1996;49(12):1373–1379. <a href="https://www.sciencedirect.com/science/article/pii/S0895435696002363">ScienceDirect</a></li>
<li>Collins GS, Reitsma JB, Altman DG, Moons KGM. Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD): the TRIPOD statement. <i>Ann Intern Med</i>. 2015;162(1):55–63. Actualización TRIPOD+AI: <i>BMJ</i>. 2024. <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11019967/">PMC</a></li>
<li>Coles AS, Knezevic D, George TP, Correll CU, Kane JM, Castle D. Long-acting injectable antipsychotic treatment in schizophrenia and co-occurring substance use disorders: a systematic review. <i>Front Psychiatry</i>. 2021;12:808002. <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8715086/">PMC</a></li>
<li>Basting EJ, Medenblik AM, Schlachta S, Garner AR, Shorey RC, Stuart GL. A latent class analysis of psychopathology among adults in residential substance use treatment: associations with craving and treatment dropout. <i>Subst Use Res Treat</i>. 2025. <a href="https://journals.sagepub.com/doi/10.1177/29768357251337850">SAGE</a></li>
<li>Mujeres consumidoras de drogas, vulnerabilidades múltiples y cuidados: un análisis con perspectiva de género. <i>Acta Psiquiátr Psicol Am Lat</i>. <a href="https://ojs.acta.org.ar/index.php/actapsi/article/view/329">Acta</a>. [25b] Santos-de Pascual A, Saura-Garre P, López-Soler C. Salud mental en personas con trastorno por consumo de sustancias: aspectos diferenciales entre hombres y mujeres. <i>An Psicol</i>. 2020;36(3):443–452. <a href="https://scielo.isciii.es/scielo.php?pid=S0212-97282020000300009&script=sci_arttext&tlng=es">SciELO</a></li>
<li>Chai YK, Wheeler Z, Herbison P, Gale C, Glue P. Factors associated with hospitalization of adult psychiatric patients: cluster analysis. <i>Australas Psychiatry</i>. 2013;21(2):141–146. <a href="https://doi.org/10.1177/1039856213475682">DOI</a></li>
<li>Lundberg SM, Lee SI. A unified approach to interpreting model predictions. <i>Advances in Neural Information Processing Systems 30 (NeurIPS)</i>. 2017. <a href="https://arxiv.org/abs/1705.07874">arXiv</a></li>
<li>Breiman L. Random forests. <i>Mach Learn</i>. 2001;45(1):5–32. <a href="https://doi.org/10.1023/A:1010933404324">DOI</a></li>
<li>Wachter S, Mittelstadt B, Russell C. Counterfactual explanations without opening the black box: automated decisions and the GDPR. <i>Harv J Law Technol</i>. 2018;31(2):841–887. <a href="https://arxiv.org/abs/1711.00399">arXiv</a></li>
<li>Gower JC. A general coefficient of similarity and some of its properties. <i>Biometrics</i>. 1971;27(4):857–871. <a href="https://doi.org/10.2307/2528823">DOI</a></li>
<li>Rousseeuw PJ. Silhouettes: a graphical aid to the interpretation and validation of cluster analysis. <i>J Comput Appl Math</i>. 1987;20:53–65. <a href="https://doi.org/10.1016/0377-0427(87)90125-7">DOI</a></li>
<li>Kaufman L, Rousseeuw PJ. <i>Finding Groups in Data: An Introduction to Cluster Analysis</i>. Nueva York: Wiley; 1990. <a href="https://doi.org/10.1002/9780470316801">DOI</a></li>
<li>Hubert L, Arabie P. Comparing partitions. <i>J Classif</i>. 1985;2(1):193–218. <a href="https://doi.org/10.1007/BF01908075">DOI</a></li>
<li>Hennig C. Cluster-wise assessment of cluster stability. <i>Comput Stat Data Anal</i>. 2007;52(1):258–271. <a href="https://doi.org/10.1016/j.csda.2006.11.025">DOI</a></li>
<li>Haldane JBS. The estimation and significance of the logarithm of a ratio of frequencies. <i>Ann Hum Genet</i>. 1956;20(4):309–311. <a href="https://doi.org/10.1111/j.1469-1809.1955.tb01285.x">DOI</a></li>
<li>Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. <i>J R Stat Soc Ser B</i>. 1995;57(1):289–300. <a href="https://doi.org/10.1111/j.2517-6161.1995.tb02031.x">DOI</a></li>
<li>Harrell FE Jr, Lee KL, Mark DB. Multivariable prognostic models: issues in developing models, evaluating assumptions and adequacy, and measuring and reducing errors. <i>Stat Med</i>. 1996;15(4):361–387. <a href="https://doi.org/10.1002/(SICI)1097-0258(19960229)15:4%3C361::AID-SIM168%3E3.0.CO;2-4">DOI</a></li>
<li>Steyerberg EW. <i>Clinical Prediction Models: A Practical Approach to Development, Validation, and Updating</i>. 2.ª ed. Cham: Springer; 2019. <a href="https://doi.org/10.1007/978-3-030-16399-0">DOI</a></li>
<li>Riley RD, Ensor J, Snell KIE, et al. Calculating the sample size required for developing a clinical prediction model. <i>BMJ</i>. 2020;368:m441. <a href="https://doi.org/10.1136/bmj.m441">DOI</a></li>
<li>Williams RL. A note on robust variance estimation for cluster-correlated data. <i>Biometrics</i>. 2000;56(2):645–646. <a href="https://doi.org/10.1111/j.0006-341X.2000.00645.x">DOI</a></li>
<li>Varma S, Simon R. Bias in error estimation when using cross-validation for model selection. <i>BMC Bioinformatics</i>. 2006;7:91. <a href="https://doi.org/10.1186/1471-2105-7-91">DOI</a></li>
<li>Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. <i>BMC Med</i>. 2019;17:230. <a href="https://doi.org/10.1186/s12916-019-1466-7">DOI</a></li>
<li>Christodoulou E, Ma J, Collins GS, Steyerberg EW, Verbakel JY, Van Calster B. A systematic review shows no performance benefit of machine learning over logistic regression for clinical prediction models. <i>J Clin Epidemiol</i>. 2019;110:12–22. <a href="https://doi.org/10.1016/j.jclinepi.2019.02.004">DOI</a></li>
<li>Hosmer DW, Lemeshow S, Sturdivant RX. <i>Applied Logistic Regression</i>. 3.ª ed. Hoboken: Wiley; 2013. <a href="https://doi.org/10.1002/9781118548387">DOI</a></li>
<li>Foss AH, Markatou M, Ray B. Distance metrics and clustering methods for mixed-type data. <i>Int Stat Rev</i>. 2019;87(1):80–109. <a href="https://doi.org/10.1111/insr.12274">DOI</a></li>
<li>von Elm E, Altman DG, Egger M, Pocock SJ, Gøtzsche PC, Vandenbroucke JP. The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement. <i>Lancet</i>. 2007;370(9596):1453–1457. <a href="https://doi.org/10.1016/S0140-6736(07)61602-X">DOI</a></li>
<li>Hanley JA, McNeil BJ. The meaning and use of the area under a receiver operating characteristic (ROC) curve. <i>Radiology</i>. 1982;143(1):29–36. <a href="https://doi.org/10.1148/radiology.143.1.7063747">DOI</a></li>
</ol>
<p class="muted" style="font-size:14px">Las referencias 15 y 25 (primera parte) se citan por título y enlace porque el texto completo no fue accesible al verificarlas; no se han añadido autores no confirmados. Las referencias 1 a 29 son evidencia clínica y epidemiológica; las 30 a 47 son las referencias metodológicas que respaldan cada decisión estadística. Las 1 a 29 se localizaron y verificaron el {__import__('datetime').date.today().strftime('%d/%m/%Y')} a partir de PubMed, PMC, Frontiers, SAGE, Elsevier y SciELO. Complementan, no sustituyen, la bibliografía del protocolo (24 referencias), que sigue siendo la base del marco teórico.</p>
</div></section>

<footer><div class="wrap">Base anonimizada · sin datos identificables · protocolo aprobado CBIHN-2026020002 · RESEGIS 5054</div></footer>
<div id="tip" role="tooltip"></div>
<script>
(function(){{var tip=document.getElementById('tip');
var hideT=null;document.addEventListener('touchstart',function(e){{var el=e.target.closest('[data-tip]');clearTimeout(hideT);if(!el){{tip.classList.remove('on');return;}}var t0=e.touches[0];tip.textContent=el.getAttribute('data-tip');tip.classList.add('on');var x=Math.min(t0.clientX+12,window.innerWidth-tip.offsetWidth-8),y=t0.clientY-tip.offsetHeight-14;if(y<8)y=t0.clientY+18;tip.style.left=Math.max(8,x)+'px';tip.style.top=y+'px';hideT=setTimeout(function(){{tip.classList.remove('on');}},3500);}},{{passive:true}});
document.addEventListener('mousemove',function(e){{if(e.sourceCapabilities&&e.sourceCapabilities.firesTouchEvents)return;var el=e.target.closest('[data-tip]');if(!el){{tip.classList.remove('on');return;}}
tip.textContent=el.getAttribute('data-tip');tip.classList.add('on');var x=e.clientX+14,y=e.clientY+14;
if(x+tip.offsetWidth>window.innerWidth-8)x=e.clientX-tip.offsetWidth-10;if(y+tip.offsetHeight>window.innerHeight-8)y=e.clientY-tip.offsetHeight-10;
tip.style.left=x+'px';tip.style.top=y+'px';}});
var COEF={{intercept:{XA["coef_logistica"]["intercepto"]},b:{{{",".join(f'"{k}":{v}' for k,v in XA["coef_logistica"].items() if k!="intercepto")}}},m:{{{",".join(f'"{k}":{v}' for k,v in XA["medias"].items())}}}}};
var PTS={{{",".join(f'"{k}":{v}' for k,v in MO["M1"]["puntaje"]["puntos"].items())}}};
function calc(){{var box=document.getElementById('calc');if(!box)return;var x={{}};box.querySelectorAll('input[data-k]').forEach(function(i){{x[i.dataset.k]=i.type==='checkbox'?(i.checked?1:0):+i.value;}});
document.getElementById('calc-age-out').textContent=x['Edad (años)'];var lo=COEF.intercept,contrib=[];
Object.keys(COEF.b).forEach(function(k){{lo+=COEF.b[k]*x[k];contrib.push([k,COEF.b[k]*(x[k]-COEF.m[k])]);}});
var p=1/(1+Math.exp(-lo));document.getElementById('calc-risk').textContent=Math.round(p*100)+'%';
var pts=0;Object.keys(PTS).forEach(function(k){{if(k in x&&k!=='Edad (por 10 años)')pts+=PTS[k]*x[k];}});document.getElementById('calc-pts').textContent='puntaje de riesgo: '+(pts>0?'+':'')+pts+' puntos';
var mx=Math.max.apply(null,contrib.map(function(c){{return Math.abs(c[1]);}}))||1;contrib.sort(function(a,b){{return Math.abs(b[1])-Math.abs(a[1]);}});
document.getElementById('calc-bars').innerHTML=contrib.map(function(c){{var pos=c[1]>0;return '<div class="wf"><span class="wfl">'+c[0]+'</span><span class="wfb"><i class="'+(pos?'pos':'neg')+'" style="--w:'+Math.round(Math.abs(c[1])/mx*100)+'%"></i></span><span class="wfv mono">'+(c[1]>=0?'+':'')+c[1].toFixed(2)+'</span></div>';}}).join('')+'<div class="wfnote">Contribución en log-odds respecto a la paciente promedio (SHAP lineal).</div>';}}
document.querySelectorAll('#calc input').forEach(function(i){{i.addEventListener('input',calc);}});calc();
var tabs=[].slice.call(document.querySelectorAll('nav.toc a[role=tab]'));
function show(id,push){{var t=document.getElementById('tab-'+id);if(!t)return false;
tabs.forEach(function(a){{var on=a===t;a.classList.toggle('active',on);a.setAttribute('aria-selected',on?'true':'false');a.tabIndex=on?0:-1;
var p=document.getElementById(a.getAttribute('aria-controls'));if(p){{p.hidden=!on;p.classList.toggle('active',on);}}}});
if(push){{try{{history.replaceState(null,'','#'+id);}}catch(e){{}}try{{localStorage.setItem('insam-tab',id);}}catch(e){{}}}}
window.scrollTo({{top:0,behavior:'auto'}});var ul=t.closest('ul');if(ul){{ul.scrollTo({{left:t.offsetLeft-(ul.clientWidth-t.offsetWidth)/2,behavior:'auto'}});}}markScroll();return true;}}
function markScroll(){{document.querySelectorAll('.tblwrap,.scroll').forEach(function(el){{var inner=el.classList.contains('scroll')?el.firstElementChild:el.querySelector('table');el.classList.toggle('scrolls',!!inner&&inner.scrollWidth>el.clientWidth+4);}});}}
window.addEventListener('resize',markScroll);window.addEventListener('load',markScroll);
tabs.forEach(function(a,i){{a.addEventListener('click',function(ev){{ev.preventDefault();show(a.getAttribute('aria-controls'),true);a.focus();}});
a.addEventListener('keydown',function(ev){{var j=ev.key==='ArrowRight'?i+1:ev.key==='ArrowLeft'?i-1:ev.key==='Home'?0:ev.key==='End'?tabs.length-1:null;
if(j===null)return;ev.preventDefault();j=(j+tabs.length)%tabs.length;tabs[j].click();}});}});
var initial=(location.hash||'').replace('#','');if(!initial){{try{{initial=localStorage.getItem('insam-tab')||'';}}catch(e){{}}}}
if(initial&&initial!=='resumen')show(initial,false);
window.addEventListener('hashchange',function(){{show((location.hash||'').replace('#',''),false);}});
}})();
</script>
"""

def _p(d,c): return g(d,c)["pct"]
LECT = {
"Grupo de edad": (f"La edad de las {NP} pacientes al ingreso, agrupada por tramos. Seis de cada diez tienen menos de 35 años: es una población joven, en plena edad reproductiva y laboral, cuando el consumo ya ha requerido hospitalización.",
 f"Cada barra es un tramo de edad y su largo es el porcentaje de pacientes que caen en él; el número pequeño es cuántas son. Es la misma lógica de un censo cuando dice «el 32% de la población tiene entre 25 y 34 años». Si la sala tuviera 10 pacientes, unas 3 tendrían entre 25 y 34 años y otras 3 menos de 25."),
"Nivel educativo": (f"El máximo grado alcanzado. La mitad llegó a secundaria y una de cada cinco solo a primaria; apenas {_p(pc['nivel_educativo'],'Posgrado')+_p(pc['nivel_educativo'],'Universitaria'):.0f}% tiene estudios universitarios. La baja escolaridad limita el empleo y la comprensión de las indicaciones al alta.",
 "Barras de porcentaje ordenadas de menor a mayor nivel. De cada 10 mujeres, 5 terminaron secundaria, 2 primaria, 2 universidad y 1 estudios técnicos o posgrado."),
"Ocupación": (f"A qué se dedica la paciente. {_p(pc['ocupacion'],'Desempleada'):.0f}% está desempleada y otro {_p(pc['ocupacion'],'Empleo informal'):.0f}% trabaja en la informalidad: tres de cada cuatro no tienen un ingreso estable, lo que condiciona la adherencia y el acceso a tratamiento ambulatorio.",
 "Como una encuesta de empleo: cada barra cuenta a quienes están en esa situación. En una sala de 10 camas, 6 pacientes no tendrían trabajo."),
"Ingreso familiar mensual (B/.)": (f"El ingreso mensual de todo el hogar, en balboas. Un tercio vive con menos de 500 balboas al mes, por debajo del salario mínimo panameño; solo {_p(pc['ingreso_familiar'],'>2000'):.0f}% supera los 2 000.",
 "Las barras van de menos a más ingreso. Léase como los tramos de una declaración de renta: la mayoría de las pacientes se concentra en los dos tramos más bajos."),
"Tipo de convivencia": (f"Con quién vive la paciente. La mayoría vive con familia (extensa o nuclear), pero {_p(pc['convivencia'],'Sola'):.0f}% vive sola y hay mujeres en situación de calle o privadas de libertad, los dos grupos con menor red de apoyo al egreso.",
 "Cada barra es un tipo de hogar. Un pequeño porcentaje puede ser clínicamente muy importante: 4% en situación de calle son 5 mujeres para quienes el alta significa volver a la calle."),
"Estado civil": (f"Dos de cada tres pacientes son solteras y solo {_p(pc['estado_civil'],'Casada'):.0f}% casadas. Junto con la convivencia, describe cuánta pareja estable hay como soporte o, en el caso de la violencia, como riesgo.",
 "Barras de porcentaje, de la categoría más frecuente a la menos. Léase como el cuadro de estado civil de cualquier ficha de ingreso hospitalario."),
"Antecedentes psicosociales y psiquiátricos": (f"Qué proporción de pacientes tiene cada antecedente. Los tres más frecuentes son atención previa en salud mental ({_p(pc['atencion_previa_sm'],'Sí'):.0f}%), violencia intrafamiliar ({_p(pc['violencia_intrafamiliar'],'Sí'):.0f}%) y policonsumo ({_p(pc['policonsumo'],'Sí'):.0f}%). Más de la mitad ha intentado suicidarse y la mitad ha sufrido abuso sexual: el trauma es la regla.",
 "Aquí las barras no suman 100% porque una misma paciente puede tener varios antecedentes. Es como preguntar a 10 personas si tienen perro, gato o pez: cada barra cuenta a las que dijeron «sí» a esa pregunta, y una persona puede estar en las tres."),
"Comorbilidad psiquiátrica por tipo": (f"Los diagnósticos psiquiátricos que acompañan al trastorno por sustancias. Depresión ({_p(E['pac_comorb_tipo'],'Trastornos depresivos'):.0f}%), trastorno de la personalidad ({_p(E['pac_comorb_tipo'],'Trastorno de la personalidad'):.0f}%) y trastorno bipolar ({_p(E['pac_comorb_tipo'],'Trastorno afectivo bipolar'):.0f}%) son los tres grandes; esquizofrenia no aparece en ninguna paciente.",
 "Como el anterior, categorías no excluyentes: una paciente con depresión y trastorno límite cuenta en dos barras. Por eso la suma supera el 72% que tiene alguna comorbilidad."),
"Droga de elección": (f"La sustancia principal de cada paciente. Cocaína ({_p(pc['droga_eleccion'],'Cocaína'):.0f}%), alcohol ({_p(pc['droga_eleccion'],'Alcohol'):.0f}%) y cannabis ({_p(pc['droga_eleccion'],'Cannabis'):.0f}%) concentran tres de cada cuatro casos; los opioides son marginales, a diferencia de Norteamérica.",
 "Cada barra es una sustancia y su largo cuántas pacientes la señalan como principal. Aquí sí suman 100% porque cada mujer tiene una sola droga de elección, aunque consuma varias."),
"Número de sustancias": (f"Cuántas sustancias distintas consume cada paciente. Solo {_p(pc['n_sustancias'],'1'):.0f}% consume una; cuatro de cada cinco combinan dos o más, y una de cada diez seis o más.",
 "Barras ordenadas de una a seis o más sustancias. Léase como la pregunta «¿cuántos medicamentos toma usted?»: aquí la respuesta habitual es «entre dos y cinco»."),
"Episodios por paciente en el período": (f"Cuántas veces se hospitalizó cada mujer en los tres años. {_p(pc['n_episodios'],'1'):.0f}% ingresó una sola vez; el 30% restante volvió al menos una vez más y unas pocas hasta cinco o seis veces. Ese 30% concentra la carga asistencial repetida, la llamada «puerta giratoria».",
 "Cada barra es un número de hospitalizaciones. Como el historial de un cliente frecuente: la mayoría vino una vez, pero un grupo pequeño vuelve una y otra vez."),
"Síntomas al ingreso": (f"Con qué llega la paciente a urgencias, contado por episodio ({NE}). Casi todas presentan alteración del ánimo; tres de cada cuatro insomnio; y cerca de la mitad síntomas psicóticos (alucinaciones o delirios) o heteroagresión, que son los que obligan a un manejo de contención.",
 "Atención: la unidad aquí es el episodio de hospitalización, no la paciente, porque una misma mujer puede llegar distinta cada vez. Es como el parte diario de urgencias que dice, de 100 ingresos, cuántos llegaron con fiebre, cuántos con dolor y cuántos con ambos."),
"Último consumo antes del ingreso": (f"Cuánto tiempo pasó entre el último consumo y el ingreso. En {_p(ec['ultimo_consumo'],'<24 h'):.0f}% de los episodios la paciente consumió en las últimas 24 horas: la mayoría llega intoxicada o en abstinencia temprana, lo que explica el uso masivo de benzodiacepinas.",
 "Barras ordenadas de más reciente a más antiguo. Léase como la pregunta de triaje «¿cuándo fue la última dosis?»."),
"Intervenciones farmacológicas": (f"Qué grupos de fármacos se usaron en cada episodio. Antipsicóticos y benzodiacepinas en más del 85%; antipsicótico de depósito (LAI) en {_p(E['epi_tx'],'Antipsicótico LAI'):.0f}% y medicación de urgencia intramuscular en {_p(E['epi_tx'],'Medicación de urgencia'):.0f}%, indicadores de agitación grave.",
 "No excluyentes: un episodio suele combinar tres o cuatro grupos. Como la hoja de prescripción: cada barra dice en cuántos ingresos aparece ese tipo de fármaco."),
"Interconsultas y estudios": ("Qué evaluaciones y estudios recibió cada episodio. Trabajo social y laboratorios casi universales; psiquiatría de adicciones, la interconsulta específica del problema, solo en dos de cada tres episodios.",
 "Léase como una lista de verificación del expediente: cada barra es el porcentaje de ingresos en que ese ítem quedó registrado."),
"Motivo de egreso": (f"Cómo terminó cada hospitalización. {_p(ec['motivo_egreso'],'Mejoría'):.0f}% por mejoría clínica, pero alta voluntaria, salida sin autorización médica y expulsión de CETA suman uno de cada cuatro egresos: la definición de «abandono» que usa el modelo predictivo.",
 "Barras de la categoría más frecuente a la menos. Es el equivalente a la casilla «condición al alta» del libro de egresos."),
"Días de hospitalización": (f"La duración de la estancia, agrupada. La mediana es {dias['mediana']:.0f} días; el bloque de 22 a 30 días corresponde en gran parte al programa CETA, que dura un mes por diseño; las estancias de 1 a 7 días incluyen la mayoría de las altas voluntarias.",
 "Cada barra es un rango de días. Como un histograma de tiempos de espera: permite ver de un vistazo si predominan las estancias cortas o largas."),
"Cribado: conducta parasuicida": ("Para cada antecedente, cuántas veces mayores son las odds de conducta parasuicida (intento suicida o autolesión) cuando está presente. Depresión, trastorno de personalidad, violencia intrafamiliar y abuso sexual aumentan el riesgo; el trastorno bipolar y los antecedentes legales, curiosamente, lo reducen, porque marcan al perfil externalizante, que se hace daño a otros y no a sí mismo.",
 "Es un «forest plot». El punto es el odds ratio (OR) y la línea horizontal su intervalo de confianza del 95%. La raya vertical en 1 significa «sin efecto»: si el punto está a la derecha, el antecedente aumenta el riesgo; a la izquierda, lo reduce; si la línea toca el 1, no se puede afirmar nada. Ejemplo: OR 9,5 para depresión es como una apuesta que sin depresión paga 1 a 1 y con depresión paga 9,5 a 1. Los puntos naranja son significativos (p<0,05); la q corrige por haber hecho muchas comparaciones: si lanzas 15 monedas, alguna sacará cinco caras seguidas por puro azar, y la q descuenta ese azar."),
"Reingreso a 90 días según comorbilidad": ("Si cada comorbilidad psiquiátrica cambia la probabilidad de volver a ingresar en los 90 días siguientes al alta, contado por episodio. Solo el trastorno bipolar sale de la zona de incertidumbre: triplica las odds de reingreso, lo que coincide con lo publicado sobre manía y reingreso.",
 "Misma lectura que el forest plot anterior: punto a la derecha del 1 y línea que no lo toca = asociación. Las líneas largas (TDAH, esquizoafectivo) reflejan grupos muy pequeños: con 5 pacientes cualquier resultado es posible, igual que una encuesta con 5 entrevistados."),
"Cribado: reingreso a 90 días alguna vez": ("El mismo cribado a nivel de paciente (¿reingresó alguna vez en el período?). El trastorno bipolar sigue siendo el único con señal, pero tras corregir por las 17 comparaciones su q sube a 0,13: ya no supera el umbral. Se reporta como hipótesis, no como hallazgo firme.",
 "Cuando el valor p es pequeño pero la q no, es que el resultado podría ser uno de los «cinco caras seguidas» que aparecen al lanzar muchas monedas. Con solo 22 pacientes reingresadas el estudio tiene poca potencia para decidirlo."),
"Cribado: abandono del tratamiento": ("Qué características del episodio se asocian a que la paciente abandone (alta voluntaria, salida sin autorización o expulsión). Las que reciben antipsicótico de depósito, llegan con psicosis o heteroagresión, o ya habían estado hospitalizadas, se quedan; las que tienen trastorno de personalidad o policonsumo se van.",
 "Aquí muchos puntos están a la izquierda del 1: un OR de 0,26 para síntomas psicóticos significa que las odds de abandonar son cuatro veces menores. Es como leer una tabla de riesgo al revés: las variables de la izquierda «retienen», las de la derecha «expulsan». Cinco de ellas siguen siendo significativas después de la corrección q."),
"V de Cramér entre variables binarias": ("Un mapa de qué antecedentes tienden a aparecer juntos en la misma paciente. Las celdas oscuras entre intento suicida, autolesión y conducta parasuicida son obvias (una define a la otra); las clínicamente interesantes son las intermedias: depresión con intento suicida y con autolesión (0,4), y rehabilitación previa con grupos de autoayuda (0,6).",
 "Es un «mapa de calor», como los de temperatura: cada celda cruza dos variables y su color mide qué tan asociadas están, de 0 (independientes) a 1 (una determina a la otra). Se lee buscando las celdas oscuras fuera de la diagonal; 0,1 es asociación pequeña, 0,3 media y 0,5 grande."),
"Elección de k": ("Cuántos grupos (clústeres) de pacientes tiene sentido formar. Cada punto es el coeficiente de silueta para un número de grupos: mide, en promedio, qué tan bien encaja cada paciente en su grupo frente al grupo vecino. Con dos grupos se obtiene el valor más alto en los dos algoritmos; a partir de tres los grupos se mezclan.",
 "Imagine agrupar a las pacientes de una sala por parecido. Con 2 grupos cada una está más cerca de las suyas que de las otras; con 5 grupos hay pacientes que podrían estar en cualquiera. La silueta va de −1 a 1: 0,24 significa grupos reales pero que se tocan, como dos nubes que se solapan en el borde."),
"Pacientes en dos dimensiones": ("Cada punto es una paciente; el color, su clúster. Las verdes (perfil afectivo) ocupan la mitad superior y las ámbar (perfil psicótico-externalizante) la inferior, con una franja de solapamiento en el centro que es la que baja la silueta.",
 "Es un mapa construido solo a partir de las «distancias» entre pacientes en 26 variables, igual que se puede dibujar el mapa de las ciudades de Panamá conociendo únicamente los kilómetros que las separan. Los ejes no significan nada por sí mismos; lo que importa es que dos puntos cercanos son dos pacientes parecidas."),
"Odds ratios ajustados": ("El efecto de cada variable sobre el abandono manteniendo fijas las demás. Trastorno de personalidad y policonsumo siguen aumentando el riesgo tras el ajuste; la hospitalización previa lo reduce; la edad no importa.",
 "«Ajustado» significa comparar dos pacientes idénticas en todo salvo en una variable. Ejemplo: dos mujeres de la misma edad, ambas con policonsumo y sin psicosis; la que además tiene trastorno de personalidad tiene 2,5 veces las odds de irse antes del alta. La lectura del punto y la línea es la misma de los forest plots anteriores."),
"Calibración": ("Si el riesgo que calcula el modelo se parece a lo que ocurrió. Los episodios se ordenaron por riesgo predicho y se dividieron en cinco grupos; para cada grupo se compara lo predicho (eje horizontal) con lo observado (vertical). Los puntos siguen la diagonal con una desviación en el grupo de menor riesgo.",
 "Es como evaluar al meteorólogo: si dice «30% de lluvia» y llueve 3 de cada 10 días con ese pronóstico, está calibrado. Un punto por encima de la diagonal significa que el modelo subestimó el riesgo; por debajo, que lo exageró."),
"Riesgo observado por puntaje": ("El puntaje de riesgo al ingreso convertido en riesgo real: qué porcentaje de episodios abandonó en cada tramo de puntos. Por debajo de 0 puntos no hubo abandonos; de 2 a 3 puntos abandona una de cada tres; con 4 o más, casi la mitad.",
 "Funciona como las escalas clínicas conocidas (CURB-65 en neumonía, Glasgow en coma): se suman puntos por cada característica presente y cada total tiene un riesgo observado. La diferencia es que esta escala aún no se ha probado en otro hospital."),
"Peso de cada variable": ("Cuánto mueve cada variable, en promedio, la predicción de abandono en los dos modelos. Policonsumo, hospitalización previa y trastorno de personalidad son las tres más influyentes en ambos; la edad solo pesa en el bosque, y su curva de dependencia muestra que es ruido.",
 "Piense en una receta: la importancia de un ingrediente es cuánto cambia el sabor si lo quita. Las barras verdes son el modelo logístico y las ámbar el bosque aleatorio; que las dos coincidan en el orden da confianza en que el ranking no depende del algoritmo."),
"SHAP por episodio, regresión logística": ("Cómo empujó cada variable el riesgo de cada uno de los 173 episodios. Cada punto es un episodio: a la derecha del cero la variable subió su riesgo, a la izquierda lo bajó; el color dice si la variable estaba presente (naranja) o ausente (azul). Tener policonsumo o trastorno de personalidad empuja a la derecha; tener psicosis u hospitalización previa, a la izquierda.",
 "Es como la cuenta detallada de un restaurante: el total (el riesgo de esa paciente) se explica sumando lo que aportó cada plato (cada variable). Aquí se ven las «cuentas» de las 173 pacientes a la vez, una fila por variable. Los grupos de puntos apilados son pacientes con el mismo valor: por ejemplo, las 38 sin policonsumo reciben la mayor reducción de riesgo de toda la gráfica."),
"Dependencia parcial de la edad": ("Qué riesgo medio de abandono predeciría el modelo si todas las pacientes tuvieran 19, 22, 25 … 67 años. La línea del modelo logístico es casi plana: la edad no cambia el pronóstico. La del bosque sube y baja sin patrón, signo de que memorizó ruido.",
 "Es como probar un termostato: se sube la temperatura un grado cada vez y se anota qué hace la caldera. Si la respuesta no cambia, ese control no está conectado a nada. Aquí la edad es ese control."),
"Interacciones (bosque)": ("Si el efecto de una variable depende de otra (por ejemplo, si el policonsumo pesa más cuando hay psicosis). Todas las interacciones son menores de 0,01 en probabilidad: los efectos simplemente se suman, lo que justifica usar la regresión logística, un modelo aditivo, como modelo final.",
 "Ejemplo de interacción: el café y el azúcar. Si el azúcar endulza igual con o sin café, no hay interacción; si solo se nota en el café, sí la hay. El bosque no encontró parejas de variables que se comporten como el segundo caso."),
}
TABN = {
"<th>Exposición</th><th>Síntoma</th>": "<p><b>Qué muestra.</b> Los cinco cruces del protocolo entre policonsumo y síntomas al ingreso. Ninguno es significativo: las pacientes con policonsumo no llegan con más psicosis, agresividad ni insomnio que las que consumen una sola sustancia.</p><p><b>Cómo leerlo.</b> La columna «con vs sin exposición» compara el porcentaje con el síntoma en los dos grupos; el OR resume esa diferencia y el valor p dice si puede ser azar. Ejemplo: heteroagresión 53% con policonsumo frente a 42% sin él parece una diferencia real, pero con solo 38 episodios sin policonsumo la p de 0,22 indica que una diferencia así aparecería 22 de cada 100 veces aunque no hubiera efecto.</p>",
"<th>Exposición</th><th>Desenlace</th>": "<p><b>Qué muestra.</b> La relación entre vulnerabilidad psiquiátrica, violencia y conducta parasuicida a nivel de paciente. La depresión es el factor más fuerte: ocho de cada diez pacientes deprimidas han intentado suicidarse frente a cuatro de cada diez sin depresión.</p><p><b>Cómo leerlo.</b> Igual que la tabla anterior. Un OR de 8 no significa «8 veces más pacientes»: significa que las odds (la razón intentos/no intentos) son 8 veces mayores. En porcentajes reales pasa de 38% a 83%, que es lo que el clínico debe recordar.</p>",
"<th>Motivo de egreso</th><th>n</th><th>Mediana de días</th>": "<p><b>Qué muestra.</b> Cuántos días dura la hospitalización según cómo termina. Quienes completan CETA se quedan 30 días porque el programa dura eso; quienes se van por alta voluntaria duran 4 días de mediana: el abandono ocurre en la primera semana, que es la ventana para intervenir.</p><p><b>Cómo leerlo.</b> Mediana es el valor del medio (la mitad de las pacientes está por encima y la mitad por debajo); Q1 y Q3 encierran a la mitad central. La prueba de Kruskal-Wallis pregunta si al menos uno de los grupos es distinto, como comparar el tiempo de espera de cinco filas de un banco sin suponer que los tiempos se reparten de forma simétrica.</p>",
"<th>Grupo</th><th>Variable</th><th>Mediana Sí</th>": "<p><b>Qué muestra.</b> Comparaciones de una variable numérica entre dos grupos. La única diferencia clara es la edad de inicio del consumo: las pacientes con abuso sexual empezaron a los 14 años y las demás a los 15. Un año parece poco, pero es consistente y coincide con la literatura sobre trauma temprano y consumo precoz.</p><p><b>Cómo leerlo.</b> La prueba U de Mann-Whitney ordena a todas las pacientes en una sola fila según la variable y comprueba si un grupo tiende a ocupar los primeros puestos, como comparar las estaturas de dos clases poniendo a todos los alumnos en fila del más bajo al más alto. No necesita que los datos sigan una curva normal.</p>",
"<th>Característica</th><th>Clúster 1": "<p><b>Qué muestra.</b> El retrato completo de cada perfil: el porcentaje de pacientes de cada clúster con cada característica, y en las últimas filas las medianas. Las filas donde los dos porcentajes se parecen (violencia, abuso sexual, policonsumo, edad de inicio) son lo que ambos perfiles comparten; las filas con contraste fuerte (psicosis, antecedentes legales, depresión, intentos suicidas, CETA, ingreso menor de 500) son lo que los separa.</p><p><b>Cómo leerlo.</b> El color de fondo es proporcional al porcentaje, como un mapa de calor: más oscuro, más frecuente. La columna p compara los dos clústeres, pero para las variables que entraron en el clustering esa comparación es circular (el algoritmo los separó justamente por ellas); solo es informativa en las filas de desenlace, como el reingreso.</p>",
"<th>Droga</th><th>Clúster 1</th>": "<p><b>Qué muestra.</b> La sustancia principal dentro de cada perfil. Cocaína, alcohol y cannabis dominan en ambos con proporciones parecidas: la droga no define el perfil, lo define la forma clínica en que se expresa el consumo.</p><p><b>Cómo leerlo.</b> Cada columna suma 100% dentro de su clúster. Compare filas: si un porcentaje fuera muy distinto entre columnas (por ejemplo, metanfetamina solo en el clúster 2), esa droga caracterizaría a ese perfil.</p>",
"<th>Conjunto de variables</th>": "<p><b>Qué muestra.</b> Qué pasa con la silueta y con la partición cuando se cambia el conjunto de variables de entrada. Si al quitar un grupo de variables la partición se mantiene (ARI cercano a 1), esas variables no eran las que separaban a los grupos; si la partición se deshace (ARI bajo), eran esenciales.</p><p><b>Cómo leerlo.</b> El ARI mide la coincidencia entre dos formas de agrupar a las mismas pacientes: 1 es idéntica y 0 lo esperable por azar. Ejemplo: quitar las variables nominales deja el ARI en 0,97 (la misma partición, algo más nítida); quitar los síntomas psicóticos lo baja a 0,39 (otra partición distinta): la psicosis es la columna vertebral de los perfiles.</p>",
"<th>Métrica</th><th>Valor</th>": "<p><b>Qué muestra.</b> Las cifras que resumen qué tan bien predice el modelo. El AUC (0,5 es lanzar una moneda, 1 es perfecto) mide si el modelo ordena bien a las pacientes; el Brier mide el error de las probabilidades; la pendiente de calibración, si las probabilidades son realistas.</p><p><b>Cómo leerlo.</b> Un AUC de 0,71 significa que, si se toman al azar una paciente que abandonó y una que no, el modelo asigna más riesgo a la primera 71 de cada 100 veces. El «AUC aparente» es la nota del examen cuando el alumno ya vio las preguntas; el corregido y el de validación cruzada son la nota con preguntas nuevas, y por eso son más bajos y más creíbles.</p>",
"<th>Característica al ingreso</th><th>Puntos</th>": "<p><b>Qué muestra.</b> La escala de riesgo de abandono en puntos, derivada de los coeficientes del modelo. Se marcan las características presentes al ingreso y se suman: los puntos positivos aumentan el riesgo y los negativos lo reducen.</p><p><b>Cómo leerlo.</b> Ejemplo: una paciente con trastorno de personalidad (+2) y policonsumo (+3), sin psicosis ni hospitalización previa, que entra por crisis, suma 5 puntos y cae en el tramo de mayor riesgo, donde abandonó casi la mitad. Es la misma mecánica de escalas como CURB-65 o CHA₂DS₂-VASc.</p>",
"<th>Modelo</th><th>Nivel</th>": "<p><b>Qué muestra.</b> Los otros dos desenlaces modelados, con su tamaño de muestra, el número de eventos y los predictores que sobreviven al ajuste. La conducta parasuicida se predice bien porque sus causas son fuertes (depresión, violencia); el reingreso no se predice porque hay muy pocos eventos.</p><p><b>Cómo leerlo.</b> EPV es «eventos por variable»: con menos de 10 el modelo tiende a aprenderse los datos de memoria, y por eso el AUC se corrige por bootstrap. Ejemplo: predecir el reingreso con 22 casos y 2 variables es como intentar adivinar el resultado de una elección con una encuesta de 22 personas.</p>",
"<th>Cambio hipotético</th>": "<p><b>Qué muestra.</b> Para el episodio de mayor riesgo, cuánto bajaría el riesgo si una sola característica fuera distinta. Quitar el policonsumo lo reduce a la mitad; quitar el trastorno de personalidad, a dos tercios.</p><p><b>Cómo leerlo.</b> Es un ejercicio de «¿y si…?», no una recomendación: ninguna de estas características se puede cambiar en la sala de urgencias. Lo que enseña es dónde concentrar la intervención de retención: en el consumo múltiple y en la desregulación emocional del trastorno de personalidad.</p>",
"<th>Verificación</th><th>Casos</th>": "<p><b>Qué muestra.</b> Las comprobaciones automáticas sobre la base: criterios de inclusión (edad, diagnóstico F10–F19) y contradicciones internas entre casillas que deberían coincidir (por ejemplo, «intento suicida: No» con «número de intentos: 2»).</p><p><b>Cómo leerlo.</b> Cada fila es una regla y la cifra cuántos registros la incumplen. Es el equivalente a revisar que en una historia clínica la fecha de egreso no sea anterior a la de ingreso; son pocos casos y no cambian los resultados, pero deben corregirse en el expediente.</p>",
"<th>Hallazgo en el INSAM</th>": "<p><b>Cómo leerlo.</b> Cada fila enfrenta un resultado de este estudio con lo que dicen revisiones y cohortes publicadas, citadas por número. El veredicto resume la comparación: «concordante» cuando la dirección y la magnitud coinciden, «con matiz» cuando coincide la dirección pero no la magnitud o el contexto, y «discordante» cuando el hallazgo contradice lo publicado y por tanto exige una explicación local, que se ofrece en la misma celda.</p>",
"<th>Ítem STROBE</th>": "<p><b>Cómo leerlo.</b> STROBE es la lista de verificación internacional de lo que un estudio observacional debe reportar. Cada fila es un ítem, su estado y dónde se cumple en esta página o en el protocolo. El único pendiente es el diagrama de flujo de pacientes, que debe elaborar la investigadora con los motivos de exclusión.</p>",
}

def _lect(title):
    q=LECT.get(title)
    if not q: return ""
    return f'<div class="lectura"><p><b>Qué muestra.</b> {q[0]}</p><p><b>Cómo leerlo.</b> {q[1]}</p></div>'
def _fig(m):
    block=m.group(0); t=re.search(r'<figcaption><b>(.*?)</b>', block, re.S)
    title=re.sub(r'<[^>]+>','',t.group(1)).strip() if t else ''
    return block[:-len('</figure>')] + _lect(title) + '</figure>'
page = re.sub(r'<figure>.*?</figure>', _fig, page, flags=re.S)
def _tab(m):
    block=m.group(0)
    for k,v in TABN.items():
        if k in block: return block[:-len('</div>')] + f'<div class="lectura">{v}</div></div>'
    return block
page = re.sub(r'<div class="tblwrap">.*?</table></div>', _tab, page, flags=re.S)
_fc = itertools.count(1)
page = re.sub(r'<figcaption><b>', lambda m: f'<figcaption><b><span class="fignum">Figura {next(_fc)}</span>', page)
open("informe.html", "w", encoding="utf-8").write(page)
# Versión autónoma para hospedar en cualquier servidor (GitHub Pages, Netlify, Cloudflare, servidor institucional)
os.makedirs("../docs", exist_ok=True)
standalone = ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
              '<meta name="robots" content="noindex,nofollow"><meta name="description" content="Características sociodemográficas y clínicas de mujeres hospitalizadas por TUS en el INSAM, Panamá, 2022–2025. Informe de análisis.">'
              '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + page + '</body></html>')
open("../docs/index.html", "w", encoding="utf-8").write(standalone)
print("informe.html", len(page)//1024, "KB")
