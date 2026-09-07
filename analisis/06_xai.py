"""Paso 6: explicabilidad (XAI) del modelo de abandono.
 - SHAP exacto (lineal) para la regresión logística, en escala log-odds.
 - TreeSHAP (interventional, con la base como fondo) para el bosque aleatorio, en escala de probabilidad.
 - Importancia por permutación (AUC) para ambos modelos.
 - Explicaciones individuales (cascada) de tres episodios ejemplo, dependencia parcial de la edad, interacciones."""
import pandas as pd, numpy as np, json, os, warnings, shap
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore"); rng=np.random.RandomState(42)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
C1,C2,C3,C4="#4a3aa7","#1baf7a","#eb6834","#2a78d6"
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":"#e6e4ee","axes.axisbelow":True,"figure.dpi":150})
epi=pd.read_csv("episodios_limpio.csv")
epi["abandono"]=epi["motivo_egreso"].isin(["Alta voluntaria","SSAM","Expulsión de CETA"]).astype(int)
V={"cp_personalidad":"Trastorno de personalidad","policonsumo":"Policonsumo activo","sx_psicotico":"Síntomas psicóticos al ingreso",
   "hosp_previa_tus":"Hospitalización previa por TUS","motivo_hosp":"Ingreso programado a CETA","edad":"Edad (años)"}
X=pd.DataFrame({"cp_personalidad":(epi.cp_personalidad=="Sí").astype(float),"policonsumo":(epi.policonsumo=="Sí").astype(float),
   "sx_psicotico":(epi.sx_psicotico=="Sí").astype(float),"hosp_previa_tus":(epi.hosp_previa_tus=="Sí").astype(float),
   "motivo_hosp":(epi.motivo_hosp=="Programa CETA").astype(float),"edad":epi.edad.astype(float)})
y=epi["abandono"].values; names=list(V.values())
lr=LogisticRegression(C=1e6,max_iter=5000).fit(X,y)      # ≈ máxima verosimilitud sin penalización
rf=RandomForestClassifier(n_estimators=500,min_samples_leaf=5,random_state=0).fit(X,y)
p_lr=lr.predict_proba(X)[:,1]; p_rf=rf.predict_proba(X)[:,1]

# ---------- SHAP ----------
ex_lr=shap.LinearExplainer(lr,X,feature_perturbation="interventional"); S_lr=ex_lr.shap_values(X); base_lr=float(ex_lr.expected_value)
ex_rf=shap.TreeExplainer(rf,data=X,feature_perturbation="interventional",model_output="probability"); S_rf=ex_rf.shap_values(X)
S_rf=S_rf[...,1] if S_rf.ndim==3 else (S_rf[1] if isinstance(S_rf,list) else S_rf); base_rf=float(np.ravel(ex_rf.expected_value)[-1])
imp_lr=np.abs(S_lr).mean(0); imp_rf=np.abs(S_rf).mean(0)
# interacciones (bosque, escala prob.)
ex_rf_raw=shap.TreeExplainer(rf); I=ex_rf_raw.shap_interaction_values(X); I=I[...,1] if np.ndim(I)==4 else (I[1] if isinstance(I,list) else I)
inter=[]
for i in range(6):
    for j in range(i+1,6): inter.append({"a":names[i],"b":names[j],"fuerza":round(float(np.abs(I[:,i,j]).mean()),4)})
inter=sorted(inter,key=lambda d:-d["fuerza"])[:5]
# ---------- permutación ----------
pi_lr=permutation_importance(lr,X,y,scoring="roc_auc",n_repeats=100,random_state=0); pi_rf=permutation_importance(rf,X,y,scoring="roc_auc",n_repeats=100,random_state=0)
# ---------- dependencia parcial edad ----------
ages=np.arange(19,70,3); pd_lr=[]; pd_rf=[]
for a in ages:
    Xa=X.copy(); Xa["edad"]=a; pd_lr.append(float(lr.predict_proba(Xa)[:,1].mean())); pd_rf.append(float(rf.predict_proba(Xa)[:,1].mean()))
# ---------- ejemplos individuales ----------
order=np.argsort(p_lr); idx={"A · riesgo alto":int(order[-1]),"B · riesgo intermedio":int(order[len(order)//2]),"C · riesgo bajo":int(order[0])}
def ficha(i):
    r=X.iloc[i]; return {"Trastorno de personalidad":"Sí" if r.cp_personalidad else "No","Policonsumo activo":"Sí" if r.policonsumo else "No",
      "Síntomas psicóticos al ingreso":"Sí" if r.sx_psicotico else "No","Hospitalización previa por TUS":"Sí" if r.hosp_previa_tus else "No",
      "Ingreso programado a CETA":"Sí" if r.motivo_hosp else "No","Edad (años)":int(r.edad)}
ejemplos=[]
for lab,i in idx.items():
    ejemplos.append({"etiqueta":lab,"caracteristicas":ficha(i),"riesgo_logistica":round(float(p_lr[i]),3),"riesgo_bosque":round(float(p_rf[i]),3),
        "abandono_real":"Sí" if y[i] else "No","contribuciones_logodds":{n:round(float(v),3) for n,v in zip(names,S_lr[i])},
        "contribuciones_prob_bosque":{n:round(float(v),3) for n,v in zip(names,S_rf[i])}})
# ---------- contrafactuales para el ejemplo A ----------
iA=idx["A · riesgo alto"]; cf=[]
for c,n in V.items():
    if c=="edad": continue
    Xc=X.iloc[[iA]].copy(); Xc[c]=1-Xc[c].values; cf.append({"cambio":f"{n}: {'Sí→No' if X.iloc[iA][c] else 'No→Sí'}","riesgo":round(float(lr.predict_proba(Xc)[0,1]),3)})
cf=sorted(cf,key=lambda d:d["riesgo"])

R={"base_logodds":round(base_lr,3),"base_prob_logistica":round(float(1/(1+np.exp(-base_lr))),3),"base_prob_bosque":round(base_rf,3),
   "coef_logistica":{"intercepto":round(float(lr.intercept_[0]),4),**{n:round(float(b),4) for n,b in zip(names,lr.coef_[0])}},
   "medias":{n:round(float(m),3) for n,m in zip(names,X.mean())},
   "importancia":[{"variable":n,"shap_logistica":round(float(a),3),"shap_bosque":round(float(b),3),"perm_logistica":round(float(c),3),"perm_bosque":round(float(d),3)}
                  for n,a,b,c,d in zip(names,imp_lr,imp_rf,pi_lr.importances_mean,pi_rf.importances_mean)],
   "beeswarm_logistica":[{"variable":n,"valores":[[round(float(X.iloc[k,j]),1),round(float(S_lr[k,j]),3)] for k in range(len(X))]} for j,n in enumerate(names)],
   "interacciones_bosque":inter,"pd_edad":{"edad":ages.tolist(),"logistica":[round(v,3) for v in pd_lr],"bosque":[round(v,3) for v in pd_rf]},
   "ejemplos":ejemplos,"contrafactuales_A":cf,"AUC_aparente":{"logistica":round(roc_auc_score(y,p_lr),3),"bosque":round(roc_auc_score(y,p_rf),3)},
   "concordancia_modelos_spearman":round(float(pd.Series(p_lr).corr(pd.Series(p_rf),method="spearman")),3)}
json.dump(R,open("xai_resultados.json","w"),ensure_ascii=False,indent=1,default=float)

# ---------- gráficas ----------
fig,ax=plt.subplots(figsize=(8,3.4)); yy=np.arange(6); o=np.argsort(imp_lr)[::-1]
ax.barh(yy-0.18,imp_lr[o]/imp_lr.sum(),0.36,color=C1,label="Logística (SHAP, log-odds)"); ax.barh(yy+0.18,imp_rf[o]/imp_rf.sum(),0.36,color=C2,label="Bosque (SHAP, probabilidad)")
ax.set_yticks(yy); ax.set_yticklabels([names[i] for i in o]); ax.invert_yaxis(); ax.set_xlabel("Importancia relativa (|SHAP| medio normalizado)"); ax.legend(fontsize=8); ax.grid(axis="y",visible=False)
ax.set_title("Importancia global de cada variable en los dos modelos",loc="left",fontweight="bold",fontsize=10); fig.tight_layout(); fig.savefig("graficas/24_xai_importancia.png"); plt.close(fig)
shap.summary_plot(S_lr,X,feature_names=names,show=False,plot_size=(8,4)); plt.title("SHAP por episodio, regresión logística (log-odds)",loc="left",fontweight="bold",fontsize=10); plt.tight_layout(); plt.savefig("graficas/25_xai_beeswarm_logistica.png"); plt.close()
shap.summary_plot(S_rf,X,feature_names=names,show=False,plot_size=(8,4)); plt.title("SHAP por episodio, bosque aleatorio (probabilidad)",loc="left",fontweight="bold",fontsize=10); plt.tight_layout(); plt.savefig("graficas/26_xai_beeswarm_bosque.png"); plt.close()
fig,axs=plt.subplots(1,3,figsize=(11,3.6),sharey=True)
for ax,e in zip(axs,ejemplos):
    c=e["contribuciones_logodds"]; ks=sorted(c,key=lambda k:-abs(c[k])); vals=[c[k] for k in ks]
    ax.barh(range(len(ks)),vals,color=[C3 if v>0 else C4 for v in vals]); ax.set_yticks(range(len(ks))); ax.set_yticklabels(ks,fontsize=7.5); ax.invert_yaxis(); ax.axvline(0,color="#9a95b3")
    ax.set_title(f"{e['etiqueta']}\nriesgo {e['riesgo_logistica']*100:.0f}% · real: {e['abandono_real']}",fontsize=9,loc="left",fontweight="bold"); ax.set_xlabel("contribución (log-odds)"); ax.grid(axis="y",visible=False)
fig.tight_layout(); fig.savefig("graficas/27_xai_ejemplos.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(6,3)); ax.plot(ages,np.array(pd_lr)*100,"o-",color=C1,label="Logística"); ax.plot(ages,np.array(pd_rf)*100,"s--",color=C2,label="Bosque"); ax.set_xlabel("Edad (años)"); ax.set_ylabel("Riesgo medio de abandono (%)"); ax.legend(fontsize=8)
ax.set_title("Dependencia parcial de la edad",loc="left",fontweight="bold",fontsize=10); fig.tight_layout(); fig.savefig("graficas/28_xai_pd_edad.png"); plt.close(fig)
print(json.dumps({k:R[k] for k in ["base_prob_logistica","base_prob_bosque","importancia","interacciones_bosque","ejemplos","contrafactuales_A","AUC_aparente","concordancia_modelos_spearman","pd_edad"]},ensure_ascii=False,indent=1))
