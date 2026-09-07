"""Paso 5: modelos predictivos.
 M1 (principal): abandono del tratamiento (alta voluntaria / SSAM / expulsión) por episodio, con predictores disponibles AL INGRESO.
     Regresión logística por máxima verosimilitud con errores estándar robustos agrupados por paciente (sandwich),
     validación cruzada agrupada por paciente (GroupKFold x 20 repeticiones), corrección de optimismo por bootstrap (Harrell),
     comparación con bosque aleatorio, y puntaje de riesgo en puntos.
 M2: conducta parasuicida (nivel paciente).  M3: reingreso a 90 días (nivel paciente; subpotenciado, sólo 2 predictores)."""
import pandas as pd, numpy as np, json, os, warnings
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.metrics import roc_auc_score, brier_score_loss, roc_curve
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore"); rng = np.random.RandomState(42)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
C1,C2,C3,C4="#4a3aa7","#1baf7a","#eb6834","#2a78d6"
plt.rcParams.update({"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":"#e6e4ee","axes.axisbelow":True,"figure.dpi":150})
pac = pd.read_csv("pacientes_limpio.csv"); epi = pd.read_csv("episodios_limpio.csv")
epi["abandono"] = epi["motivo_egreso"].isin(["Alta voluntaria","SSAM","Expulsión de CETA"]).astype(int)
epi["sx_psicotico_b"] = (epi["sx_psicotico"]=="Sí").astype(int)
for d in (pac,epi):
    for c in ["cp_personalidad","cp_bipolar","cp_depresivo","policonsumo","hosp_previa_tus","antec_legales","sx_heteroagresion","violencia_intrafamiliar","abuso_sexual","conducta_parasuicida","reingreso_alguna_vez","intento_suicida_previo"]:
        if c in d: d[c+"_b"] = (d[c]=="Sí").astype(int)
epi["ceta_b"] = (epi["motivo_hosp"]=="Programa CETA").astype(int)
epi["edad_10"] = epi["edad"]/10; pac["edad_10"]=pac["edad"]/10; pac["inicio_5"]=pac["edad_inicio_consumo"]/5

# ---------- logística MLE + sandwich agrupado ----------
def logit_fit(X, y, groups=None):
    X = np.column_stack([np.ones(len(X)), X]); b = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1/(1+np.exp(-X@b)); W = p*(1-p)
        H = X.T@(X*W[:,None]); g = X.T@(y-p)
        step = np.linalg.solve(H+1e-8*np.eye(len(b)), g); b += step
        if np.abs(step).max()<1e-8: break
    p = 1/(1+np.exp(-X@b)); W=p*(1-p); Hinv = np.linalg.inv(X.T@(X*W[:,None]))
    if groups is None: V = Hinv
    else:
        S = X*(y-p)[:,None]; G = pd.DataFrame(S).groupby(groups).sum().values
        m = len(G); V = Hinv@(G.T@G)@Hinv * m/(m-1)
    se = np.sqrt(np.diag(V)); ll = np.sum(y*np.log(p)+(1-y)*np.log(1-p))
    return b, se, ll, p
def summarize(names, b, se, ll0):
    z = b/se; pv = 2*stats.norm.sf(np.abs(z))
    return [{"variable":n,"beta":round(bb,3),"OR":round(np.exp(bb),2),"IC_lo":round(np.exp(bb-1.96*s),2),"IC_hi":round(np.exp(bb+1.96*s),2),"p":round(float(pp),4)} for n,bb,s,pp in zip(names,b,se,pv)]
def auc_boot_optimism(X, y, B=200):
    """Harrell: AUC aparente - promedio(AUC_boot_en_boot - AUC_boot_en_original)"""
    Xa = np.column_stack([np.ones(len(X)), X]); b,_,_,p = logit_fit(X,y); app = roc_auc_score(y,p); opt=[]
    for _ in range(B):
        idx = rng.randint(0,len(y),len(y)); 
        if len(set(y[idx]))<2: continue
        bb,_,_,pb = logit_fit(X[idx],y[idx]); po = 1/(1+np.exp(-Xa@bb))
        opt.append(roc_auc_score(y[idx],pb)-roc_auc_score(y,po))
    return app, app-np.mean(opt), float(np.mean(opt))
def grouped_cv(X, y, groups, model_fn, reps=20, k=5):
    aucs, briers, oof = [], [], np.zeros(len(y))
    for r in range(reps):
        # barajar grupos para repetir GroupKFold
        ug = np.unique(groups); perm = dict(zip(ug, rng.permutation(len(ug)))); gperm = np.array([perm[g] for g in groups])
        pred = np.zeros(len(y))
        for tr,te in GroupKFold(k).split(X,y,gperm):
            m = model_fn(); m.fit(X[tr],y[tr]); pred[te] = m.predict_proba(X[te])[:,1]
        aucs.append(roc_auc_score(y,pred)); briers.append(brier_score_loss(y,pred)); oof += pred/reps
    return {"AUC_media":round(float(np.mean(aucs)),3),"AUC_IC":[round(float(np.percentile(aucs,2.5)),3),round(float(np.percentile(aucs,97.5)),3)],"Brier":round(float(np.mean(briers)),3)}, oof
def calib(y, p, bins=5):
    q = pd.qcut(p, bins, labels=False, duplicates="drop"); out=[]
    for b in sorted(set(q)):
        m = q==b; out.append({"pred":round(float(p[m].mean()),3),"obs":round(float(y[m].mean()),3),"n":int(m.sum())})
    # pendiente de calibración (logit)
    lp = np.log(p/(1-p)); bcal,_,_,_ = logit_fit(lp[:,None], y); return out, round(float(bcal[1]),2)

R = {}
# ================= M1: abandono =================
V1 = {"cp_personalidad_b":"Trastorno de personalidad","policonsumo_b":"Policonsumo activo","sx_psicotico_b":"Síntomas psicóticos al ingreso",
      "hosp_previa_tus_b":"Hospitalización previa por TUS","ceta_b":"Ingreso programado a CETA","edad_10":"Edad (por 10 años)"}
X1 = epi[list(V1)].values.astype(float); y1 = epi["abandono"].values; g1 = epi["id_paciente"].values
b,se,ll,p = logit_fit(X1,y1,groups=g1); ll0 = logit_fit(np.zeros((len(y1),0)),y1)[2]
coef = summarize(["Intercepto"]+list(V1.values()), b, se, ll0)
app, corr, opt = auc_boot_optimism(X1,y1)
cv_lr, oof_lr = grouped_cv(X1,y1,g1,lambda: LogisticRegression(C=1.0,max_iter=1000))
cv_rf, oof_rf = grouped_cv(X1,y1,g1,lambda: RandomForestClassifier(n_estimators=300,min_samples_leaf=5,random_state=0))
cal, slope = calib(y1, np.clip(oof_lr,1e-4,1-1e-4))
lr_test = 1-stats.chi2.cdf(2*(ll-ll0), X1.shape[1])
# puntaje de riesgo (betas / beta mínimo absoluto, redondeado)
bet = b[1:]; unit = np.abs(bet[np.abs(bet)>0.2]).min(); pts = np.round(bet/unit).astype(int)
epi["score"] = (X1*pts).sum(1) if False else (epi[list(V1)].values*pts).sum(1)
# para edad, los puntos por década son pequeños; se deja como puntos por década
sc = epi.groupby(pd.cut(epi["score"],[-99,-3,-1,1,3,99],labels=["≤-3","-2 a -1","0 a 1","2 a 3","≥4"]))["abandono"].agg(["size","mean"])
R["M1"] = {"desenlace":"Abandono del tratamiento (alta voluntaria, SSAM o expulsión)","nivel":"episodio","n":int(len(y1)),"eventos":int(y1.sum()),
           "EPV":round(float(y1.sum()/X1.shape[1]),1),"coeficientes":coef,"LR_test_p":float(lr_test),"pseudoR2_McFadden":round(1-ll/ll0,3),
           "AUC_aparente":round(app,3),"AUC_corregida_optimismo":round(corr,3),"optimismo":round(opt,3),
           "CV_logistica":cv_lr,"CV_bosque":cv_rf,"calibracion":cal,"pendiente_calibracion":slope,
           "puntaje":{"puntos":{v:int(pt) for v,pt in zip(V1.values(),pts)},"estratos":[{"puntaje":str(i),"n":int(r["size"]),"riesgo_pct":round(100*r["mean"],1)} for i,r in sc.iterrows()]}}
# ================= M2: conducta parasuicida (paciente) =================
V2 = {"cp_depresivo_b":"Trastorno depresivo","cp_personalidad_b":"Trastorno de personalidad","cp_bipolar_b":"Trastorno bipolar",
      "violencia_intrafamiliar_b":"Violencia intrafamiliar","abuso_sexual_b":"Abuso sexual","antec_legales_b":"Antecedentes legales","inicio_5":"Edad de inicio (por 5 años)"}
X2 = pac[list(V2)].values.astype(float); y2 = pac["conducta_parasuicida_b"].values
b2,se2,ll2,_ = logit_fit(X2,y2); ll02 = logit_fit(np.zeros((len(y2),0)),y2)[2]
app2,corr2,opt2 = auc_boot_optimism(X2,y2)
aucs=[]; 
for r in range(20):
    pred=np.zeros(len(y2))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=r).split(X2,y2):
        m=LogisticRegression(max_iter=1000).fit(X2[tr],y2[tr]); pred[te]=m.predict_proba(X2[te])[:,1]
    aucs.append(roc_auc_score(y2,pred))
R["M2"] = {"desenlace":"Conducta parasuicida (intento suicida o autolesión)","nivel":"paciente","n":int(len(y2)),"eventos":int(y2.sum()),"EPV":round(float(y2.sum()/X2.shape[1]),1),
           "coeficientes":summarize(["Intercepto"]+list(V2.values()),b2,se2,ll02),"pseudoR2_McFadden":round(1-ll2/ll02,3),
           "AUC_aparente":round(app2,3),"AUC_corregida_optimismo":round(corr2,3),"CV_AUC":round(float(np.mean(aucs)),3)}
# ================= M3: reingreso (paciente, subpotenciado) =================
V3 = {"cp_bipolar_b":"Trastorno bipolar","hosp_previa_tus_b":"Hospitalización previa por TUS"}
X3 = pac[list(V3)].values.astype(float); y3 = pac["reingreso_alguna_vez_b"].values
b3,se3,ll3,_ = logit_fit(X3,y3); ll03 = logit_fit(np.zeros((len(y3),0)),y3)[2]; app3,corr3,_ = auc_boot_optimism(X3,y3)
R["M3"] = {"desenlace":"Reingreso a 90 días en algún episodio","nivel":"paciente","n":int(len(y3)),"eventos":int(y3.sum()),"EPV":round(float(y3.sum()/2),1),
           "coeficientes":summarize(["Intercepto"]+list(V3.values()),b3,se3,ll03),"AUC_aparente":round(app3,3),"AUC_corregida_optimismo":round(corr3,3),
           "nota":f"Sólo {int(y3.sum())} eventos: el modelo se limita a dos predictores y es exploratorio."}
json.dump(R,open("modelo_resultados.json","w"),ensure_ascii=False,indent=1,default=float)

# ---------- gráficas ----------
fig,ax=plt.subplots(1,2,figsize=(9.5,3.9))
for oof,lab,col in ((oof_lr,f"Logística (AUC {cv_lr['AUC_media']})",C1),(oof_rf,f"Bosque aleatorio (AUC {cv_rf['AUC_media']})",C2)):
    fpr,tpr,_=roc_curve(y1,oof); ax[0].plot(fpr,tpr,color=col,lw=2,label=lab)
ax[0].plot([0,1],[0,1],ls="--",color="#9a95b3"); ax[0].set_xlabel("1 − especificidad"); ax[0].set_ylabel("Sensibilidad"); ax[0].legend(fontsize=8); ax[0].set_title("ROC, validación cruzada agrupada por paciente",loc="left",fontweight="bold",fontsize=9.5)
ax[1].plot([0,0.8],[0,0.8],ls="--",color="#9a95b3"); ax[1].plot([c["pred"] for c in cal],[c["obs"] for c in cal],"o-",color=C1)
for c in cal: ax[1].annotate(f"n={c['n']}",(c["pred"],c["obs"]),textcoords="offset points",xytext=(6,-10),fontsize=7,color="#3b3750")
ax[1].set_xlabel("Riesgo predicho"); ax[1].set_ylabel("Abandono observado"); ax[1].set_title(f"Calibración (pendiente {slope})",loc="left",fontweight="bold",fontsize=9.5)
fig.tight_layout(); fig.savefig("graficas/21_modelo_roc_calibracion.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(8.5,3.6)); items=coef[1:]; y=np.arange(len(items))
for yi,i in zip(y,items):
    col=C3 if i["p"]<0.05 else C1; ax.plot([i["IC_lo"],i["IC_hi"]],[yi,yi],color=col,lw=2); ax.plot(i["OR"],yi,"o",color=col)
    ax.text(1.02,yi,f"OR {i['OR']} ({i['IC_lo']}–{i['IC_hi']})  p={i['p']}",transform=ax.get_yaxis_transform(),va="center",fontsize=8,color="#3b3750",clip_on=False)
ax.axvline(1,ls="--",color="#9a95b3"); ax.set_xscale("log"); ax.set_yticks(y); ax.set_yticklabels([i["variable"] for i in items]); ax.invert_yaxis(); ax.set_xlabel("OR ajustado (escala log)")
ax.set_title("Modelo de abandono del tratamiento: OR ajustados con EE robustos por paciente",loc="left",fontweight="bold",fontsize=9.5); ax.grid(axis="y",visible=False); fig.tight_layout(rect=(0,0,0.72,1)); fig.savefig("graficas/22_modelo_or_ajustados.png"); plt.close(fig)
fig,ax=plt.subplots(figsize=(6.5,3.2)); st=R["M1"]["puntaje"]["estratos"]; ax.bar([s["puntaje"] for s in st],[s["riesgo_pct"] for s in st],color=C1)
for i,s in enumerate(st): ax.text(i,s["riesgo_pct"]+1.5,f"{s['riesgo_pct']}%\n(n={s['n']})",ha="center",fontsize=8)
ax.set_xlabel("Puntaje de riesgo al ingreso"); ax.set_ylabel("% de episodios con abandono"); ax.set_ylim(0,max(s["riesgo_pct"] for s in st)+18); ax.set_title("Riesgo observado de abandono por estrato de puntaje",loc="left",fontweight="bold",fontsize=9.5); ax.grid(axis="x",visible=False)
fig.tight_layout(); fig.savefig("graficas/23_puntaje_riesgo.png"); plt.close(fig)
print(json.dumps(R,ensure_ascii=False,indent=1,default=float))
