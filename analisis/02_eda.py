"""Paso 2: análisis exploratorio (descriptivo + bivariado) sobre la base limpia.
Salidas: eda_resultados.json y gráficas PNG en ./graficas"""
import pandas as pd, numpy as np, json, os, warnings
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.abspath(__file__))); os.makedirs("graficas", exist_ok=True)
pac = pd.read_csv("pacientes_limpio.csv"); epi = pd.read_csv("episodios_limpio.csv")
C1, C2, C3, C4 = "#4a3aa7", "#1baf7a", "#eb6834", "#2a78d6"
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,
                     "grid.color":"#e6e4ee","grid.linewidth":0.6,"axes.axisbelow":True,"figure.dpi":150})
R = {}

# ---------- descriptivos ----------
def freq(df, col, order=None):
    s = df[col].astype(str).value_counts(dropna=False)
    if order: s = s.reindex([o for o in order if o in s.index]).dropna()
    return [{"cat":k, "n":int(v), "pct":round(100*v/len(df),1)} for k,v in s.items()]
def num(df, col):
    s = df[col].dropna()
    return {"n":int(s.size),"media":round(s.mean(),1),"de":round(s.std(),1),"mediana":float(s.median()),
            "q1":float(s.quantile(.25)),"q3":float(s.quantile(.75)),"min":float(s.min()),"max":float(s.max())}

PAC_CAT = {"grupo_edad":["18–24","25–34","35–44","45–54","55–64","≥65"],
 "nivel_educativo":["Primaria","Secundaria","Técnica","Universitaria","Posgrado"],
 "estado_civil":None,"nacionalidad":None,"provincia":None,"ocupacion":None,"convivencia":None,
 "ingreso_familiar":["<500","500–1000","1001–2000",">2000","No especificado"],"religion":None,
 "antec_legales":None,"violencia_intrafamiliar":None,"abuso_sexual":None,"algun_abuso":None,
 "atencion_previa_sm":None,"hosp_previa_tus":None,"rehab_previa":None,"grupos_autoayuda":None,
 "intento_suicida_previo":None,"conducta_autolesiva":None,"conducta_parasuicida":None,
 "comorb_psiq":None,"n_comorb_psiq":["0","1","2–3"],"comorb_medica":None,
 "n_sustancias":["1","2–3","4–5","≥6"],"droga_eleccion":None,"policonsumo":None,"inicio_temprano_<15":None,
 "n_episodios":None,"reingreso_alguna_vez":None}
R["pac_cat"] = {c: freq(pac, c, o) for c,o in PAC_CAT.items()}
R["pac_num"] = {c: num(pac, c) for c in ["edad","n_hijos","n_intentos_suicidas","edad_inicio_consumo","anios_consumo","n_comorb_psiq_num"]}
cps = {"cp_depresivo":"Trastornos depresivos","cp_ansiedad":"Trastornos de ansiedad","cp_personalidad":"Trastorno de la personalidad",
       "cp_bipolar":"Trastorno afectivo bipolar","cp_esquizoafectivo":"Trastorno esquizoafectivo","cp_tdah":"TDAH",
       "cp_discap_intelectual":"Discapacidad intelectual","cp_otros":"Otros"}
R["pac_comorb_tipo"] = [{"cat":l,"n":int((pac[c]=="Sí").sum()),"pct":round(100*(pac[c]=="Sí").mean(),1)} for c,l in cps.items()]

EPI_CAT = {"motivo_hosp":None,"sx_heteroagresion":None,"sx_sensoperceptual":None,"sx_delirante":None,"sx_insomnio":None,"sx_humor":None,
 "sx_psicotico":None,"ultimo_consumo":["<24 h","≤1 semana","≤1 mes",">1 mes","No especificado"],"metabolitos_positivos":None,
 "tx_antipsicotico":None,"tx_benzodiacepina":None,"tx_estabilizador":None,"tx_antidepresivo":None,"tx_antiextrapiramidal":None,
 "tx_lai":None,"tx_lai_tipo":None,"tx_med_urgencia":None,"ic_trabajo_social":None,"ic_psicologia":None,"ic_psiq_adicciones":None,
 "ekg":None,"eeg":None,"laboratorios":None,"estancia_cat":["1–7","8–14","15–21","22–30",">30"],"dx_egreso_cat":None,
 "motivo_egreso":None,"reingreso_90d":None}
R["epi_cat"] = {c: freq(epi, c, o) for c,o in EPI_CAT.items()}
R["epi_num"] = {c: num(epi, c) for c in ["dias_hosp","n_sintomas_ingreso","n_farmacos"]}
sx = {"sx_humor":"Alteración del humor/afecto","sx_insomnio":"Insomnio","sx_heteroagresion":"Heteroagresión",
      "sx_sensoperceptual":"Alteraciones sensoperceptuales","sx_delirante":"Ideas delirantes"}
R["epi_sintomas"] = [{"cat":l,"n":int((epi[c]=="Sí").sum()),"pct":round(100*(epi[c]=="Sí").mean(),1)} for c,l in sx.items()]
tx = {"tx_benzodiacepina":"Benzodiacepinas","tx_antipsicotico":"Antipsicóticos","tx_antiextrapiramidal":"Antiextrapiramidales",
      "tx_estabilizador":"Estabilizadores del ánimo","tx_med_urgencia":"Medicación de urgencia","tx_antidepresivo":"Antidepresivos","tx_lai":"Antipsicótico LAI"}
R["epi_tx"] = [{"cat":l,"n":int((epi[c]=="Sí").sum()),"pct":round(100*(epi[c]=="Sí").mean(),1)} for c,l in tx.items()]

# ---------- bivariado ----------
def or_ci(t):
    a,b,c,d = t[0][0],t[0][1],t[1][0],t[1][1]
    if 0 in (a,b,c,d): a,b,c,d = a+.5,b+.5,c+.5,d+.5
    o = (a*d)/(b*c); se = np.sqrt(1/a+1/b+1/c+1/d)
    return o, o*np.exp(-1.96*se), o*np.exp(1.96*se)
def assoc(df, x, y, xl=None, yl=None, xpos="Sí", ypos="Sí"):
    d = df[[x,y]].dropna()
    t = [[int(((d[x]==xpos)&(d[y]==ypos)).sum()), int(((d[x]==xpos)&(d[y]!=ypos)).sum())],
         [int(((d[x]!=xpos)&(d[y]==ypos)).sum()), int(((d[x]!=xpos)&(d[y]!=ypos)).sum())]]
    chi, p, _, exp = stats.chi2_contingency(t, correction=False)
    fisher = bool((exp < 5).any())
    if fisher: p = stats.fisher_exact(t)[1]
    o, lo, hi = or_ci(t)
    n1 = t[0][0]+t[0][1]; n0 = t[1][0]+t[1][1]
    return {"x":xl or x,"y":yl or y,"tabla":t,"pct_exp":round(100*t[0][0]/n1,1) if n1 else None,"pct_noexp":round(100*t[1][0]/n0,1) if n0 else None,
            "OR":round(o,2),"IC_lo":round(lo,2),"IC_hi":round(hi,2),"p":round(p,4),"prueba":"Fisher" if fisher else "χ²","n":int(len(d))}

# Bloque A (episodios) - replicación del protocolo
A = [assoc(epi,"policonsumo",s,"Policonsumo activo",l) for s,l in sx.items()]
# Bloque B/C (pacientes)
BC = [assoc(pac,"comorb_psiq","conducta_parasuicida","Comorbilidad psiquiátrica","Conducta parasuicida"),
      assoc(pac,"cp_depresivo","intento_suicida_previo","Trastorno depresivo","Intento suicida previo"),
      assoc(pac,"cp_depresivo","conducta_autolesiva","Trastorno depresivo","Conducta autolesiva"),
      assoc(pac,"cp_personalidad","conducta_parasuicida","Trastorno de personalidad","Conducta parasuicida"),
      assoc(pac,"algun_abuso","comorb_psiq","Violencia o abuso","Comorbilidad psiquiátrica"),
      assoc(pac,"algun_abuso","conducta_parasuicida","Violencia o abuso","Conducta parasuicida"),
      assoc(pac,"violencia_intrafamiliar","conducta_parasuicida","Violencia intrafamiliar","Conducta parasuicida"),
      assoc(pac,"abuso_sexual","conducta_parasuicida","Abuso sexual","Conducta parasuicida")]
# Bloque D (reingreso) a nivel PACIENTE (reingreso en cualquier episodio) y a nivel episodio
D_ep = [assoc(epi,"comorb_psiq","reingreso_90d","Comorbilidad psiquiátrica","Reingreso 90 d"),
        assoc(epi,"hosp_previa_tus","reingreso_90d","Hospitalización previa por TUS","Reingreso 90 d")]
D_ep += [assoc(epi,c,"reingreso_90d",l,"Reingreso 90 d") for c,l in cps.items() if c!="cp_discap_intelectual"]
R["biv_protocolo"] = {"A_policonsumo_sintomas":A,"BC_vulnerabilidad":BC,"D_reingreso_episodio":D_ep}
# Mann-Whitney / Kruskal
def mw(df,g,y,gl,yl):
    a = df.loc[df[g]=="Sí",y].dropna(); b = df.loc[df[g]=="No",y].dropna()
    u,p = stats.mannwhitneyu(a,b,alternative="two-sided")
    return {"grupo":gl,"var":yl,"mediana_si":float(a.median()),"mediana_no":float(b.median()),"n_si":int(a.size),"n_no":int(b.size),"U":float(u),"p":round(p,4)}
R["biv_mw"] = [mw(pac,"comorb_psiq","edad_inicio_consumo","Comorbilidad psiquiátrica","Edad de inicio"),
               mw(pac,"abuso_sexual","edad_inicio_consumo","Abuso sexual","Edad de inicio"),
               mw(pac,"violencia_intrafamiliar","edad_inicio_consumo","Violencia intrafamiliar","Edad de inicio"),
               mw(pac,"policonsumo","edad_inicio_consumo","Policonsumo","Edad de inicio"),
               mw(epi,"reingreso_90d","dias_hosp","Reingreso 90 d","Días de hospitalización"),
               mw(epi,"tx_lai","dias_hosp","Antipsicótico LAI","Días de hospitalización")]
grp = {k: v["dias_hosp"].values for k,v in epi.groupby("motivo_egreso")}
H,p = stats.kruskal(*grp.values())
R["kw_dias_egreso"] = {"H":round(H,2),"gl":len(grp)-1,"p":float(p),
   "grupos":[{"cat":k,"n":int(len(v)),"mediana":float(np.median(v)),"q1":float(np.percentile(v,25)),"q3":float(np.percentile(v,75))} for k,v in grp.items()]}

# ---------- cribado exploratorio con corrección FDR (nuevo) ----------
bin_pac = ["antec_legales","violencia_intrafamiliar","abuso_sexual","atencion_previa_sm","hosp_previa_tus","rehab_previa","grupos_autoayuda",
           "intento_suicida_previo","conducta_autolesiva","comorb_psiq","cp_depresivo","cp_personalidad","cp_bipolar","comorb_medica","policonsumo",
           "inicio_temprano_<15","es_extranjera"]
LBL = {"antec_legales":"Antecedentes legales","violencia_intrafamiliar":"Violencia intrafamiliar","abuso_sexual":"Abuso sexual",
 "atencion_previa_sm":"Atención previa salud mental","hosp_previa_tus":"Hospitalización previa TUS","rehab_previa":"Rehabilitación previa",
 "grupos_autoayuda":"Grupos de autoayuda","intento_suicida_previo":"Intento suicida previo","conducta_autolesiva":"Conducta autolesiva",
 "comorb_psiq":"Comorbilidad psiquiátrica","cp_depresivo":"T. depresivo","cp_personalidad":"T. personalidad","cp_bipolar":"T. bipolar",
 "comorb_medica":"Comorbilidad médica","policonsumo":"Policonsumo","inicio_temprano_<15":"Inicio <15 años","es_extranjera":"Extranjera",
 "reingreso_alguna_vez":"Reingreso 90 d (alguna vez)","conducta_parasuicida":"Conducta parasuicida",
 "sx_heteroagresion":"Heteroagresión al ingreso","sx_psicotico":"Síntomas psicóticos al ingreso","tx_lai":"Antipsicótico LAI","tx_med_urgencia":"Medicación de urgencia"}
def screen(df, xs, y, yl):
    out = [assoc(df,x,y,LBL[x],yl) for x in xs if x!=y]
    ps = np.array([o["p"] for o in out]); m=len(ps); order=np.argsort(ps); q=np.empty(m)
    prev=1.0
    for rank,i in reversed(list(enumerate(order,1))):
        prev = min(prev, ps[i]*m/rank); q[i]=prev
    for o,qq in zip(out,q): o["q_FDR"]=round(float(qq),3)
    return sorted(out,key=lambda o:o["p"])
R["screen_reingreso_pac"] = screen(pac, bin_pac, "reingreso_alguna_vez", "Reingreso 90 d (alguna vez)")
R["screen_parasuicida_pac"] = screen(pac, [b for b in bin_pac if b not in ("intento_suicida_previo","conducta_autolesiva")], "conducta_parasuicida", "Conducta parasuicida")
# alta voluntaria/SSAM (abandono) por episodio
epi["abandono"] = np.where(epi["motivo_egreso"].isin(["Alta voluntaria","SSAM","Expulsión de CETA"]),"Sí","No")
R["screen_abandono_epi"] = screen(epi, ["policonsumo","comorb_psiq","cp_personalidad","cp_bipolar","hosp_previa_tus","sx_heteroagresion","sx_psicotico","tx_lai","tx_med_urgencia","antec_legales","conducta_autolesiva"], "abandono", "Alta voluntaria / SSAM / expulsión")
# Multi-categoría: droga de elección x síntomas psicóticos, x motivo egreso (Fisher-Freeman-Halton aprox por chi2 + simulación)
def chi_multi(df,x,y):
    t = pd.crosstab(df[x],df[y]); chi,p,dof,exp = stats.chi2_contingency(t)
    v = np.sqrt(chi/(t.values.sum()*(min(t.shape)-1)))
    return {"x":x,"y":y,"chi2":round(chi,2),"gl":int(dof),"p":round(p,4),"cramer_v":round(v,3),"celdas_esperadas_<5":int((exp<5).sum()),
            "tabla":{str(i):{str(c):int(t.loc[i,c]) for c in t.columns} for i in t.index}}
R["multi"] = [chi_multi(epi,"droga_eleccion","sx_psicotico"),chi_multi(epi,"droga_eleccion","sx_heteroagresion"),
              chi_multi(epi,"motivo_hosp","motivo_egreso"),chi_multi(pac,"droga_eleccion","grupo_edad"),chi_multi(epi,"n_sustancias","sx_psicotico")]

# ---------- matriz de asociación (V de Cramér) ----------
vars_v = bin_pac + ["conducta_parasuicida","reingreso_alguna_vez"]
M = pd.DataFrame(index=[LBL[v] for v in vars_v], columns=[LBL[v] for v in vars_v], dtype=float)
for a in vars_v:
    for b in vars_v:
        t = pd.crosstab(pac[a],pac[b]); chi = stats.chi2_contingency(t,correction=False)[0]
        M.loc[LBL[a],LBL[b]] = np.sqrt(chi/(len(pac)*(min(t.shape)-1))) if a!=b else 1
R["cramer_matrix"] = {"labels":list(M.index),"values":M.round(2).values.tolist()}
top = [(M.index[i],M.columns[j],round(M.iloc[i,j],2)) for i in range(len(M)) for j in range(i+1,len(M))]
R["cramer_top"] = sorted(top,key=lambda t:-t[2])[:12]

# ---------- gráficas PNG ----------
def barh(items, title, fn, color=C1, pct=True):
    items = list(items); fig,ax = plt.subplots(figsize=(7,0.42*len(items)+1.2))
    y = np.arange(len(items)); vals=[i["pct"] if pct else i["n"] for i in items]
    ax.barh(y, vals, color=color, height=0.62); ax.set_yticks(y); ax.set_yticklabels([i["cat"] for i in items]); ax.invert_yaxis()
    for yi,v,it in zip(y,vals,items): ax.text(v+0.6, yi, f"{it['pct']}% (n={it['n']})", va="center", fontsize=8, color="#3b3750")
    ax.set_xlim(0, max(vals)*1.3); ax.set_xlabel("%" if pct else "n"); ax.set_title(title, loc="left", fontsize=11, fontweight="bold"); ax.grid(axis="y",visible=False)
    fig.tight_layout(); fig.savefig(f"graficas/{fn}.png"); plt.close(fig)
barh(sorted(R["pac_cat"]["droga_eleccion"],key=lambda i:-i["n"]),"Droga de elección (n=118 pacientes)","01_droga_eleccion")
barh(R["pac_cat"]["grupo_edad"],"Grupo de edad al ingreso (pacientes)","02_grupo_edad",C4)
barh(sorted(R["pac_cat"]["convivencia"],key=lambda i:-i["n"]),"Tipo de convivencia","03_convivencia",C4)
barh(R["pac_comorb_tipo"],"Comorbilidad psiquiátrica por tipo (pacientes)","04_comorb_psiq")
barh(R["epi_sintomas"],"Síntomas al ingreso (n=173 episodios)","05_sintomas_ingreso",C3)
barh(R["epi_tx"],"Intervenciones farmacológicas (episodios)","06_farmacos",C2)
barh(sorted(R["epi_cat"]["motivo_egreso"],key=lambda i:-i["n"]),"Motivo de egreso (episodios)","07_motivo_egreso",C2)
fig,ax=plt.subplots(figsize=(7,3.6)); ax.hist(pac["edad"],bins=range(18,72,4),color=C4,edgecolor="white"); ax.set_xlabel("Edad (años)"); ax.set_ylabel("Pacientes")
ax.axvline(pac["edad"].median(),color=C3,ls="--"); ax.text(pac["edad"].median()+0.5,ax.get_ylim()[1]*0.9,f"mediana {pac['edad'].median():.0f}",color=C3)
ax.set_title("Distribución de la edad al ingreso",loc="left",fontweight="bold"); fig.tight_layout(); fig.savefig("graficas/08_edad_hist.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(7,3.6)); ax.hist(pac["edad_inicio_consumo"],bins=range(8,48,2),color=C1,edgecolor="white"); ax.set_xlabel("Edad de inicio del consumo (años)"); ax.set_ylabel("Pacientes")
ax.axvline(15,color=C3,ls="--"); ax.text(15.3,ax.get_ylim()[1]*0.9,f"{(pac['edad_inicio_consumo']<15).mean()*100:.0f}% inició antes de los 15",color=C3)
ax.set_title("Edad de inicio del consumo",loc="left",fontweight="bold"); fig.tight_layout(); fig.savefig("graficas/09_edad_inicio.png"); plt.close(fig)
# boxplot días x motivo egreso
order = sorted(grp, key=lambda k:-np.median(grp[k]))
fig,ax=plt.subplots(figsize=(7,3.8)); ax.boxplot([grp[k] for k in order],vert=False,labels=[f"{k} (n={len(grp[k])})" for k in order],patch_artist=True,
  boxprops=dict(facecolor="#dcd7f2",color=C1),medianprops=dict(color=C3,lw=2),whiskerprops=dict(color=C1),capprops=dict(color=C1),flierprops=dict(marker="o",ms=3,mfc=C1,mec="none"))
ax.invert_yaxis(); ax.set_xlabel("Días de hospitalización"); ax.set_title(f"Estancia según motivo de egreso (Kruskal-Wallis H={H:.1f}, p<0,001)",loc="left",fontweight="bold",fontsize=10)
ax.grid(axis="y",visible=False); fig.tight_layout(); fig.savefig("graficas/10_dias_por_egreso.png"); plt.close(fig)
# forest plot reingreso (episodio) + cribado paciente
def forest(items,title,fn):
    items=[i for i in items if i["OR"]<50]; fig,ax=plt.subplots(figsize=(9.5,0.42*len(items)+1.3)); y=np.arange(len(items))
    for yi,i in zip(y,items):
        col = C3 if i["p"]<0.05 else C1
        ax.plot([i["IC_lo"],i["IC_hi"]],[yi,yi],color=col,lw=1.8); ax.plot(i["OR"],yi,"o",color=col,ms=7)
        ax.text(1.02,yi,transform=ax.get_yaxis_transform(),s=f"OR {i['OR']} ({i['IC_lo']}–{i['IC_hi']})  p={i['p']}"+(f"  q={i['q_FDR']}" if "q_FDR" in i else ""),va="center",fontsize=7.5,color="#3b3750",clip_on=False)
    ax.axvline(1,color="#9a95b3",ls="--"); ax.set_xscale("log"); ax.set_xlim(0.03,60); ax.set_yticks(y); ax.set_yticklabels([i["x"] for i in items]); ax.invert_yaxis()
    ax.set_xlabel("Odds ratio (escala log)"); ax.set_title(title,loc="left",fontweight="bold",fontsize=10); ax.grid(axis="y",visible=False); fig.tight_layout(rect=(0,0,0.72,1)); fig.savefig(f"graficas/{fn}.png"); plt.close(fig)
forest(D_ep,"Factores asociados a reingreso a 90 días (nivel episodio, n=173)","11_forest_reingreso_episodio")
forest(R["screen_reingreso_pac"],"Cribado: reingreso a 90 días alguna vez (nivel paciente, n=118, q=FDR)","12_forest_reingreso_paciente")
forest(R["screen_parasuicida_pac"],"Cribado: conducta parasuicida (nivel paciente, n=118, q=FDR)","13_forest_parasuicida")
forest(R["screen_abandono_epi"],"Cribado: alta voluntaria / SSAM / expulsión (nivel episodio, q=FDR)","14_forest_abandono")
# heatmap Cramér
fig,ax=plt.subplots(figsize=(8.5,7.5)); im=ax.imshow(M.values.astype(float),cmap="Purples",vmin=0,vmax=0.6)
ax.set_xticks(range(len(M))); ax.set_xticklabels(M.columns,rotation=60,ha="right",fontsize=7.5); ax.set_yticks(range(len(M))); ax.set_yticklabels(M.index,fontsize=7.5); ax.grid(False)
for i in range(len(M)):
    for j in range(len(M)):
        if i!=j and M.iloc[i,j]>=0.2: ax.text(j,i,f"{M.iloc[i,j]:.2f}",ha="center",va="center",fontsize=6,color="white" if M.iloc[i,j]>0.4 else "#2a2540")
fig.colorbar(im,ax=ax,shrink=0.7,label="V de Cramér"); ax.set_title("Asociación entre variables binarias (pacientes)",loc="left",fontweight="bold"); fig.tight_layout(); fig.savefig("graficas/15_cramer_heatmap.png"); plt.close(fig)
# episodios por paciente
fig,ax=plt.subplots(figsize=(6,3)); vc=pac["n_episodios"].value_counts().sort_index(); ax.bar(vc.index.astype(str),vc.values,color=C4)
for x,v in zip(range(len(vc)),vc.values): ax.text(x,v+1,f"{v} ({100*v/len(pac):.0f}%)",ha="center",fontsize=8)
ax.set_xlabel("Episodios de hospitalización por paciente"); ax.set_ylabel("Pacientes"); ax.set_title("Reingresos en el período",loc="left",fontweight="bold"); ax.grid(axis="x",visible=False); fig.tight_layout(); fig.savefig("graficas/16_episodios_por_paciente.png"); plt.close(fig)

json.dump(R, open("eda_resultados.json","w"), ensure_ascii=False, indent=1, default=float)
print("A:", [(a["y"],a["OR"],a["p"]) for a in A])
print("BC:", [(a["x"],a["y"],a["OR"],a["p"]) for a in BC])
print("D:", [(a["x"],a["OR"],a["p"]) for a in D_ep])
print("MW:", [(m["grupo"],m["var"],m["mediana_si"],m["mediana_no"],m["p"]) for m in R["biv_mw"]])
print("KW:", R["kw_dias_egreso"]["H"], R["kw_dias_egreso"]["p"])
print("SCREEN reingreso pac:", [(a["x"],a["OR"],a["p"],a["q_FDR"]) for a in R["screen_reingreso_pac"][:6]])
print("SCREEN parasuicida:", [(a["x"],a["OR"],a["p"],a["q_FDR"]) for a in R["screen_parasuicida_pac"][:6]])
print("SCREEN abandono:", [(a["x"],a["OR"],a["p"],a["q_FDR"]) for a in R["screen_abandono_epi"][:6]])
print("MULTI:", [(m["x"],m["y"],m["p"],m["cramer_v"]) for m in R["multi"]])
print("CRAMER top:", R["cramer_top"][:8])
print(os.listdir("graficas"))
