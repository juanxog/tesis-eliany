"""Paso 3: análisis no supervisado (clustering) a nivel paciente, según el protocolo:
distancia de Gower para datos mixtos, PAM (k-medoides) y jerárquico (average linkage),
elección de k por silueta (y codo), estabilidad por bootstrap (ARI). Desenlaces excluidos del clustering."""
import pandas as pd, numpy as np, json, os, warnings
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform
from sklearn.metrics import silhouette_score, silhouette_samples, adjusted_rand_score
from sklearn.manifold import MDS
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore"); np.random.seed(42)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
C1, C2, C3, C4 = "#4a3aa7", "#1baf7a", "#eb6834", "#2a78d6"; COLS=[C1,C2,C3,C4,"#eda100","#e87ba4"]
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":"#e6e4ee","axes.axisbelow":True,"figure.dpi":150})

pac = pd.read_csv("pacientes_limpio.csv"); epi = pd.read_csv("episodios_limpio.csv")
first = epi.sort_values(["id_paciente","n_episodio"]).groupby("id_paciente").first()
pac = pac.set_index("id_paciente")
for c in ["sx_heteroagresion","sx_sensoperceptual","sx_delirante","sx_insomnio","sx_humor","motivo_hosp","ultimo_consumo"]:
    pac[c+"_e1"] = first[c]

# ---------- variables de entrada (sin desenlaces) ----------
NUM = ["edad","edad_inicio_consumo","n_hijos"]
ORD = {"nivel_educativo":["Primaria","Secundaria","Técnica","Universitaria","Posgrado"],
       "ingreso_familiar":["<500","500–1000","1001–2000",">2000"],
       "n_sustancias":["1","2–3","4–5","≥6"]}
BIN = ["antec_legales","violencia_intrafamiliar","abuso_sexual","hosp_previa_tus","rehab_previa","intento_suicida_previo",
       "conducta_autolesiva","cp_depresivo","cp_personalidad","cp_bipolar","comorb_medica","policonsumo",
       "sx_heteroagresion_e1","sx_sensoperceptual_e1","sx_delirante_e1","es_extranjera"]
NOM = ["droga_eleccion","convivencia","ocupacion","motivo_hosp_e1"]
X = pac.copy()
for c,o in ORD.items(): X[c] = X[c].map({v:i for i,v in enumerate(o)})
for c in BIN: X[c] = (X[c]=="Sí").astype(float)
feats = NUM+list(ORD)+BIN+NOM
n = len(X)

# ---------- distancia de Gower ----------
D = np.zeros((n,n))
for c in NUM+list(ORD):
    v = X[c].values.astype(float); rng = np.nanmax(v)-np.nanmin(v)
    d = np.abs(v[:,None]-v[None,:])/rng; d[np.isnan(d)] = np.nanmean(d); D += d
for c in BIN:
    v = X[c].values; D += (v[:,None]!=v[None,:]).astype(float)
for c in NOM:
    v = X[c].values; D += (v[:,None]!=v[None,:]).astype(float)
D /= len(feats); np.fill_diagonal(D, 0.0)

# ---------- PAM ----------
def pam(D,k,iters=100,seed=0):
    rs = np.random.RandomState(seed); n=len(D)
    med = list(rs.choice(n,k,replace=False)); best = D[:,med].min(1).sum()
    for _ in range(iters):
        improved=False
        for i in range(k):
            for h in range(n):
                if h in med: continue
                cand = med.copy(); cand[i]=h; cost = D[:,cand].min(1).sum()
                if cost < best-1e-12: med,best,improved = cand,cost,True
        if not improved: break
    return np.array(med), D[:,med].argmin(1), best
def best_pam(D,k):
    return min((pam(D,k,seed=s) for s in range(5)), key=lambda r:r[2])

Z = linkage(squareform(D,checks=False), method="average")
res = {"k":[], "sil_pam":[], "sil_hc":[], "cost_pam":[]}
labels_pam, labels_hc = {}, {}
for k in range(2,9):
    med,lab,cost = best_pam(D,k); labels_pam[k]=lab
    hc = fcluster(Z,k,criterion="maxclust"); labels_hc[k]=hc
    res["k"].append(k); res["cost_pam"].append(round(cost,3))
    res["sil_pam"].append(round(silhouette_score(D,lab,metric="precomputed"),3))
    res["sil_hc"].append(round(silhouette_score(D,hc,metric="precomputed"),3) if len(set(hc))>1 else None)
kbest = res["k"][int(np.argmax(res["sil_pam"]))]
# también Ward sobre MDS (aprox) para comparar
lab = labels_pam[kbest]; med = best_pam(D,kbest)[0]
sizes = np.bincount(lab)
# ---------- estabilidad bootstrap ----------
aris=[]
for b in range(50):
    idx = np.random.choice(n,int(0.8*n),replace=False); Db = D[np.ix_(idx,idx)]
    _,lb,_ = pam(Db,kbest,seed=b); aris.append(adjusted_rand_score(lab[idx],lb))
# ---------- silueta por paciente ----------
sil_i = silhouette_samples(D,lab,metric="precomputed")
# ---------- perfiles ----------
pac["cluster"] = lab+1
epi["cluster"] = epi["id_paciente"].map(pac["cluster"])
def pct(df,c,val="Sí"): return df.groupby("cluster")[c].apply(lambda s:(s==val).mean()*100).round(1)
prof = {}
for c in BIN: prof[c] = pct(pac,c.replace("_e1","") if False else c, 1.0 if False else "Sí") if pac[c].dtype==object else pac.groupby("cluster")[c].mean().round(3)
# recalc from pac (strings)
pac_raw = pd.read_csv("pacientes_limpio.csv").set_index("id_paciente"); pac_raw["cluster"]=pac["cluster"]
for c in ["sx_heteroagresion","sx_sensoperceptual","sx_delirante","sx_insomnio","sx_humor","motivo_hosp"]: pac_raw[c+"_e1"]=first[c]
profile = {}
binlabels = {"antec_legales":"Antecedentes legales","violencia_intrafamiliar":"Violencia intrafamiliar","abuso_sexual":"Abuso sexual",
 "hosp_previa_tus":"Hospitalización previa TUS","rehab_previa":"Rehabilitación previa","intento_suicida_previo":"Intento suicida previo",
 "conducta_autolesiva":"Conducta autolesiva","cp_depresivo":"T. depresivo","cp_personalidad":"T. personalidad","cp_bipolar":"T. bipolar",
 "comorb_medica":"Comorbilidad médica","policonsumo":"Policonsumo","sx_heteroagresion_e1":"Heteroagresión (1er ingreso)",
 "sx_sensoperceptual_e1":"Alt. sensoperceptuales (1er ingreso)","sx_delirante_e1":"Ideas delirantes (1er ingreso)","es_extranjera":"Extranjera",
 "reingreso_alguna_vez":"Reingreso 90 d (desenlace)","comorb_psiq":"Comorbilidad psiquiátrica","grupos_autoayuda":"Grupos de autoayuda","atencion_previa_sm":"Atención previa SM"}
for c,l in binlabels.items(): profile[l] = pct(pac_raw,c).to_dict()
profile["Programa CETA (1er ingreso)"] = pct(pac_raw,"motivo_hosp_e1","Programa CETA").to_dict()
profile["Inicio <15 años"] = pct(pac_raw,"inicio_temprano_<15").to_dict()
profile["Desempleada"] = pct(pac_raw,"ocupacion","Desempleada").to_dict()
profile["Ingreso <500"] = pct(pac_raw,"ingreso_familiar","<500").to_dict()
profile["≥4 sustancias"] = pac_raw.groupby("cluster")["n_sustancias"].apply(lambda s:s.isin(["4–5","≥6"]).mean()*100).round(1).to_dict()
numprof = {l: pac_raw.groupby("cluster")[c].median().to_dict() for c,l in {"edad":"Edad (mediana)","edad_inicio_consumo":"Edad inicio (mediana)","n_hijos":"Hijos (mediana)","n_intentos_suicidas":"Intentos suicidas (mediana)","n_episodios":"Episodios (media)"}.items()}
numprof["Episodios (media)"] = pac_raw.groupby("cluster")["n_episodios"].mean().round(2).to_dict()
drogas = pd.crosstab(pac_raw["cluster"],pac_raw["droga_eleccion"],normalize="index").round(3)*100
conv = pd.crosstab(pac_raw["cluster"],pac_raw["convivencia"],normalize="index").round(3)*100
edu = pd.crosstab(pac_raw["cluster"],pac_raw["nivel_educativo"],normalize="index").round(3)*100
# desenlaces por cluster (nivel episodio)
out = epi.groupby("cluster").agg(episodios=("id_episodio","size"),dias_mediana=("dias_hosp","median"),
        reingreso_pct=("reingreso_90d",lambda s:round((s=="Sí").mean()*100,1)),
        alta_vol_pct=("motivo_egreso",lambda s:round(s.isin(["Alta voluntaria","SSAM","Expulsión de CETA"]).mean()*100,1)),
        ceta_completo_pct=("motivo_egreso",lambda s:round((s=="Completó programa CETA").mean()*100,1)),
        lai_pct=("tx_lai",lambda s:round((s=="Sí").mean()*100,1)),
        urgencia_pct=("tx_med_urgencia",lambda s:round((s=="Sí").mean()*100,1)))
# pruebas entre clusters para las variables de perfil (exploratorias)
tests = {}
for c,l in binlabels.items():
    t = pd.crosstab(pac_raw["cluster"],pac_raw[c]); 
    if t.shape[1]>1: tests[l] = round(stats.chi2_contingency(t)[1],4)
for c,l in {"edad":"Edad","edad_inicio_consumo":"Edad inicio","n_hijos":"Hijos"}.items():
    tests[l] = round(stats.kruskal(*[g[c].dropna().values for _,g in pac_raw.groupby("cluster")])[1],4)
for lbl,col,val in [("Programa CETA (1er ingreso)","motivo_hosp_e1","Programa CETA"),("Inicio <15 años","inicio_temprano_<15","Sí"),("Desempleada","ocupacion","Desempleada"),("Ingreso <500","ingreso_familiar","<500")]:
    tests[lbl] = round(stats.chi2_contingency(pd.crosstab(pac_raw["cluster"],pac_raw[col]==val))[1],4)
tests["≥4 sustancias"] = round(stats.chi2_contingency(pd.crosstab(pac_raw["cluster"],pac_raw["n_sustancias"].isin(["4–5","≥6"])))[1],4)
tests["Intentos suicidas"] = round(stats.kruskal(*[g["n_intentos_suicidas"].dropna().values for _,g in pac_raw.groupby("cluster")])[1],4)
tests["Episodios"] = round(stats.kruskal(*[g["n_episodios"].values for _,g in pac_raw.groupby("cluster")])[1],4)
tests["Días de hospitalización (episodios)"] = round(stats.kruskal(*[g["dias_hosp"].values for _,g in epi.groupby("cluster")])[1],4)
tests["Reingreso 90 d (episodios)"] = round(stats.chi2_contingency(pd.crosstab(epi["cluster"],epi["reingreso_90d"]))[1],4)
tests["Abandono (alta vol/SSAM/expulsión)"] = round(stats.chi2_contingency(pd.crosstab(epi["cluster"],epi["motivo_egreso"].isin(["Alta voluntaria","SSAM","Expulsión de CETA"])))[1],4)

# ---------- sensibilidad: silueta con distintos conjuntos de variables ----------
def gower(cols):
    Dd=np.zeros((n,n))
    for c in cols:
        v=X[c].values
        if c in NUM or c in ORD:
            v=v.astype(float); rng_=np.nanmax(v)-np.nanmin(v); d=np.abs(v[:,None]-v[None,:])/rng_; d[np.isnan(d)]=np.nanmean(d); Dd+=d
        else: Dd+=(v[:,None]!=v[None,:]).astype(float)
    Dd/=len(cols); np.fill_diagonal(Dd,0); return Dd
subsets={"Todas (26, reportado)":feats,
 "Sin nominales (droga, convivencia, ocupación, motivo)":[f for f in feats if f not in NOM],
 "Solo clínicas (sin sociodemográficas)":[f for f in feats if f not in ("edad","n_hijos","nivel_educativo","ingreso_familiar","convivencia","ocupacion","es_extranjera")],
 "Solo sociodemográficas":["edad","n_hijos","nivel_educativo","ingreso_familiar","convivencia","ocupacion","es_extranjera","antec_legales"],
 "Sin síntomas del 1er ingreso":[f for f in feats if not f.startswith("sx_")],
 "Núcleo de 10 variables discriminantes":["antec_legales","hosp_previa_tus","intento_suicida_previo","conducta_autolesiva","cp_depresivo","cp_bipolar","cp_personalidad","sx_heteroagresion_e1","sx_sensoperceptual_e1","sx_delirante_e1"]}
sens=[]
for name_,cols in subsets.items():
    Ds=gower(cols); best=None
    for k in range(2,6):
        _,lb,_=best_pam(Ds,k); sil=silhouette_score(Ds,lb,metric="precomputed")
        if best is None or sil>best[1]: best=(k,round(float(sil),3),lb)
    sens.append({"conjunto":name_,"n_vars":len(cols),"k":best[0],"silueta":best[1],"ARI_vs_reportado":round(adjusted_rand_score(lab,best[2]),3)})
R_sens=sens
# ---------- MDS 2D ----------
mds = MDS(n_components=2,dissimilarity="precomputed",random_state=42,normalized_stress="auto"); XY = mds.fit_transform(D)

R = {"variables_entrada":feats,"n":n,"k_evaluados":res,"k_elegido":int(kbest),"silueta":res["sil_pam"][res["k"].index(kbest)],
     "tamanos":{str(i+1):int(s) for i,s in enumerate(sizes)},
     "estabilidad_ARI":{"media":round(float(np.mean(aris)),3),"de":round(float(np.std(aris)),3),"min":round(float(np.min(aris)),3)},
     "silueta_por_cluster":{str(i+1):round(float(sil_i[lab==i].mean()),3) for i in range(kbest)},
     "perfil_pct":profile,"perfil_num":numprof,"droga_por_cluster":drogas.to_dict("index"),"convivencia_por_cluster":conv.to_dict("index"),
     "educacion_por_cluster":edu.to_dict("index"),"desenlaces":out.to_dict("index"),"pruebas_p":tests,
     "mds":[{"x":round(float(x),3),"y":round(float(y),3),"c":int(l)+1} for (x,y),l in zip(XY,lab)],
     "concordancia_pam_vs_jerarquico_ARI":round(adjusted_rand_score(lab,labels_hc[kbest]),3),"sensibilidad_variables":R_sens,"episodios_por_cluster":{str(k):int(v) for k,v in epi.groupby("cluster").size().items()},"reingreso_pacientes":{str(k):int(v) for k,v in pac_raw.groupby("cluster")["reingreso_alguna_vez"].apply(lambda s:(s=="Sí").sum()).items()},"reingreso_episodios":{str(k):int(v) for k,v in epi.groupby("cluster")["reingreso_90d"].apply(lambda s:(s=="Sí").sum()).items()}}
pac_raw[["cluster"]].to_csv("pacientes_cluster.csv")
json.dump(R,open("cluster_resultados.json","w"),ensure_ascii=False,indent=1,default=float)

# ---------- gráficas ----------
fig,ax=plt.subplots(1,2,figsize=(9,3.4))
ax[0].plot(res["k"],res["sil_pam"],"o-",color=C1,label="PAM (k-medoides)"); ax[0].plot(res["k"],res["sil_hc"],"s--",color=C2,label="Jerárquico (average)")
ax[0].axvline(kbest,color=C3,ls=":"); ax[0].set_xlabel("k"); ax[0].set_ylabel("Coeficiente de silueta"); ax[0].legend(fontsize=8); ax[0].set_title("Silueta por k",loc="left",fontweight="bold")
ax[1].plot(res["k"],res["cost_pam"],"o-",color=C1); ax[1].set_xlabel("k"); ax[1].set_ylabel("Costo total (suma de distancias)"); ax[1].set_title("Método del codo (PAM)",loc="left",fontweight="bold")
fig.tight_layout(); fig.savefig("graficas/17_silueta_codo.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(6.5,5))
for i in range(kbest): ax.scatter(XY[lab==i,0],XY[lab==i,1],s=34,color=COLS[i],label=f"Clúster {i+1} (n={sizes[i]})",edgecolor="white",lw=0.6)
ax.scatter(XY[med,0],XY[med,1],s=140,facecolor="none",edgecolor="#111",lw=1.4,label="Medoides")
ax.set_xlabel("MDS 1"); ax.set_ylabel("MDS 2"); ax.legend(fontsize=8); ax.set_title(f"Pacientes en 2D (MDS sobre distancia de Gower), k={kbest}",loc="left",fontweight="bold",fontsize=10)
fig.tight_layout(); fig.savefig("graficas/18_mds_clusters.png"); plt.close(fig)
P = pd.DataFrame(profile).T; P.columns=[f"C{c}" for c in P.columns]
fig,ax=plt.subplots(figsize=(7.5,0.32*len(P)+1.2)); im=ax.imshow(P.values,cmap="Purples",vmin=0,vmax=100,aspect="auto")
ax.set_xticks(range(P.shape[1])); ax.set_xticklabels([f"{c}\n(n={sizes[i]})" for i,c in enumerate(P.columns)]); ax.set_yticks(range(len(P))); ax.set_yticklabels(P.index,fontsize=8); ax.grid(False)
for i in range(len(P)):
    for j in range(P.shape[1]): ax.text(j,i,f"{P.iloc[i,j]:.0f}%",ha="center",va="center",fontsize=7.5,color="white" if P.iloc[i,j]>55 else "#2a2540")
ax.set_title("Perfil de cada clúster (% de pacientes)",loc="left",fontweight="bold",fontsize=10); fig.tight_layout(); fig.savefig("graficas/19_perfil_clusters.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(9,3.2)); dendrogram(Z,no_labels=True,color_threshold=0,above_threshold_color=C1,ax=ax); ax.set_ylabel("Distancia de Gower"); ax.set_title("Dendrograma (average linkage)",loc="left",fontweight="bold"); ax.grid(False)
fig.tight_layout(); fig.savefig("graficas/20_dendrograma.png"); plt.close(fig)

print(json.dumps({k:R[k] for k in ["k_evaluados","k_elegido","silueta","tamanos","estabilidad_ARI","silueta_por_cluster","concordancia_pam_vs_jerarquico_ARI","perfil_num","desenlaces","pruebas_p"]},ensure_ascii=False,indent=1,default=float))
print(P.round(0).to_string()); print(drogas.round(0).to_string()); print(conv.round(0).to_string())
