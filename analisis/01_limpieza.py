"""
Paso 1: limpieza y anonimización de la base de datos.
Entrada : ../Gráficas-Trabajo Graduación (4).xlsx (hojas PACIENTES y EPISODIOS)
Salidas : pacientes_limpio.csv, episodios_limpio.csv (SIN nombre ni cédula)
          llave_identificacion.csv (nombre/cédula -> código; guardar aparte, NO compartir)
          reporte_limpieza.json
"""
import pandas as pd, numpy as np, json, re, unicodedata, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SRC = "../Gráficas-Trabajo Graduación (4).xlsx"

COLS = ["nombre","cedula","edad","nivel_educativo","estado_civil","nacionalidad","provincia","ocupacion",
 "convivencia","ingreso_familiar","n_hijos","religion","antec_legales","violencia_intrafamiliar","abuso_sexual",
 "atencion_previa_sm","hosp_previa_tus","rehab_previa","grupos_autoayuda","intento_suicida_previo","n_intentos_suicidas",
 "conducta_autolesiva","comorb_psiq","n_comorb_psiq","cp_depresivo","cp_ansiedad","cp_personalidad","cp_bipolar",
 "cp_esquizoafectivo","cp_esquizofrenia","cp_tdah","cp_discap_intelectual","cp_tea","cp_otros","comorb_medica",
 "comorb_medica_tipo","sx_heteroagresion","sx_sensoperceptual","sx_delirante","sx_insomnio","sx_humor",
 "motivo_hosp","n_sustancias","droga_eleccion","edad_inicio_consumo","ultimo_consumo","metabolitos_positivos",
 "policonsumo","tx_antipsicotico","tx_benzodiacepina","tx_estabilizador","tx_antidepresivo","tx_antiextrapiramidal",
 "tx_lai","tx_lai_tipo","tx_med_urgencia","ic_trabajo_social","ic_psicologia","ic_psiq_adicciones","ekg","eeg",
 "laboratorios","dias_hosp","dx_egreso","motivo_egreso","reingreso_90d"]

def load(sheet):
    df = pd.read_excel(SRC, sheet_name=sheet, header=0)
    df = df.iloc[:, :66]; df.columns = COLS
    df = df.dropna(how="all")
    return df

pac = load("PACIENTES"); epi = load("EPISODIOS")
rep = {"filas_originales": {"pacientes": len(pac), "episodios": len(epi)}, "cambios": []}

def norm_txt(s):
    if pd.isna(s): return np.nan
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

# ---------- 1. Clave de identificación ----------
def key(c):  # normaliza cédulas para detectar la misma persona
    c = norm_txt(c); c = c.split("/")[0].strip()
    c = re.sub(r"^(P\.|P-|PAX|P)", "", c, flags=re.I) if not re.match(r"^PE-", c, re.I) else c
    return c.upper().replace(".", "").replace(" ", "")
pac["_key"] = pac["cedula"].map(key); epi["_key"] = epi["cedula"].map(key)

# duplicado detectado: misma cédula, dos nombres (misma edad) -> se consolida como una paciente
dup = pac[pac["_key"].duplicated(keep=False)]
rep["cambios"].append(f"Cédulas duplicadas en PACIENTES: {dup['_key'].nunique()} (filas {len(dup)}); se conservó la primera fila de cada una.")
pac = pac.drop_duplicates(subset="_key", keep="first").reset_index(drop=True)

# episodios cuya cédula no está en pacientes
faltan = set(epi["_key"]) - set(pac["_key"])
rep["cambios"].append(f"Cédulas en EPISODIOS sin fila en PACIENTES: {len(faltan)}")
if faltan:  # se crea la fila de paciente a partir del primer episodio
    extra = epi[epi["_key"].isin(faltan)].drop_duplicates("_key")
    pac = pd.concat([pac, extra], ignore_index=True)

# códigos anónimos tipo F-<edad>-<nnn> como pide el protocolo (Fem-56-001)
pac = pac.sort_values("_key").reset_index(drop=True)
pac["id_paciente"] = [f"F-{int(a):02d}-{i+1:03d}" for i, a in enumerate(pac["edad"])]
mapa = dict(zip(pac["_key"], pac["id_paciente"]))
epi["id_paciente"] = epi["_key"].map(mapa)
epi["n_episodio"] = epi.groupby("id_paciente").cumcount() + 1
epi["id_episodio"] = epi["id_paciente"] + "-E" + epi["n_episodio"].astype(str)

llave = pac[["id_paciente","nombre","cedula"]].copy()
llave.to_csv("llave_identificacion.csv", index=False)
for d in (pac, epi):
    d.drop(columns=["nombre","cedula","_key"], inplace=True)

# ---------- 2. Normalización de categorías ----------
SI_NO = {"si":"Sí","sí":"Sí","no":"No"}
def sino(v):
    v = norm_txt(v)
    if pd.isna(v): return np.nan
    return SI_NO.get(strip_accents(v.lower()), v)

sino_cols = ["antec_legales","violencia_intrafamiliar","abuso_sexual","atencion_previa_sm","hosp_previa_tus",
 "rehab_previa","grupos_autoayuda","intento_suicida_previo","conducta_autolesiva","comorb_psiq",
 "cp_depresivo","cp_ansiedad","cp_personalidad","cp_bipolar","cp_esquizoafectivo","cp_esquizofrenia","cp_tdah",
 "cp_discap_intelectual","cp_tea","cp_otros","comorb_medica","sx_heteroagresion","sx_sensoperceptual","sx_delirante",
 "sx_insomnio","sx_humor","policonsumo","tx_antipsicotico","tx_benzodiacepina","tx_estabilizador","tx_antidepresivo",
 "tx_antiextrapiramidal","tx_lai","tx_med_urgencia","ic_trabajo_social","ic_psicologia","ic_psiq_adicciones",
 "ekg","eeg","laboratorios","reingreso_90d"]

MAPS = {
 "nivel_educativo": {"Tecnico":"Técnica","Universidad":"Universitaria","Postgrado":"Posgrado"},
 "estado_civil": {"Unida":"Unión libre","Separada":"Separada/Divorciada","Divorciada":"Separada/Divorciada"},
 "nacionalidad": {"PANAMEÑA":"Panameña","COLOMBIANA":"Colombiana","VENEZOLANA":"Venezolana","USA":"Estadounidense",
                  "ITALIANA":"Italiana","BÚLGARA":"Búlgara","PUERTO RICO":"Puertorriqueña"},
 "provincia": {"NO APLICA":"No aplica (extranjera)","Chiriqui":"Chiriquí"},
 "ocupacion": {"Empleada":"Empleo formal","Informal":"Empleo informal"},
 "convivencia": {"Con familia extendida":"Familia extensa","Con familia nuclear":"Familia nuclear","Vive sola":"Sola",
                 "PRIVADA DE LIBERTAD":"Privada de libertad","Con amistades u otros":"Amistades u otros"},
 "ingreso_familiar": {"< B/. 500":"<500","> B/. 2000":">2000","No especificada":"No especificado"},
 "religion": {"NO ESPECIFICADO":"No especificado"},
 "n_comorb_psiq": {"Sin comorbilidad psiquiátrica":"0","1 comorbilidad psiquiátrica":"1","2–3 comorbilidades psiquiátricas":"2–3"},
 "motivo_hosp": {"por Crisis":"Crisis","para CETA":"Programa CETA"},
 "n_sustancias": {"1 sustancia":"1","2-3 sustancias":"2–3","4-5 sustancias":"4–5","más de 6 sustancias":"≥6"},
 "droga_eleccion": {"2CBD":"2C-B (tusi)","Crack":"Piedra/crack"},
 "ultimo_consumo": {"En las últimas 24 horas":"<24 h","En la última semana":"≤1 semana","En el último mes":"≤1 mes",
                    "Mas de un mes":">1 mes"},
 "metabolitos_positivos": {"si":"Sí","no":"No","No se realizó":"No se realizó"},
 "tx_lai_tipo": {"NO APLICA":"No aplica","No se aplicó":"No aplica","Decanoato de Flufenazina":"Flufenazina decanoato"},
 "motivo_egreso": {"completó programa de CETA":"Completó programa CETA","EXPULSION DE CETA":"Expulsión de CETA"},
}
def clean(df):
    for c in df.columns:
        if df[c].dtype == object: df[c] = df[c].map(norm_txt)
    for c in sino_cols: df[c] = df[c].map(sino)
    for c, m in MAPS.items(): df[c] = df[c].replace(m)
    # comorbilidad médica: 0 / "0.0" significa ninguna
    df["comorb_medica_tipo"] = df["comorb_medica_tipo"].map(lambda v: np.nan if pd.isna(v) or str(v) in ("0","0.0") else str(v))
    for c in ["edad","n_hijos","n_intentos_suicidas","edad_inicio_consumo","dias_hosp"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["dx_egreso"] = df["dx_egreso"].map(lambda s: re.sub(r"\s+"," ",str(s)).strip() if not pd.isna(s) else s)
    # ---------- 3. Variables derivadas ----------
    df["grupo_edad"] = pd.cut(df["edad"], [17,24,34,44,54,64,200], labels=["18–24","25–34","35–44","45–54","55–64","≥65"])
    df["conducta_parasuicida"] = np.where((df["intento_suicida_previo"]=="Sí")|(df["conducta_autolesiva"]=="Sí"),"Sí","No")
    df["algun_abuso"] = np.where((df["violencia_intrafamiliar"]=="Sí")|(df["abuso_sexual"]=="Sí"),"Sí","No")
    df["inicio_temprano_<15"] = np.where(df["edad_inicio_consumo"]<15,"Sí","No")
    df["anios_consumo"] = df["edad"] - df["edad_inicio_consumo"]
    df["dx_egreso_principal"] = df["dx_egreso"].str.extract(r"(F1\d(?:\.\d+)?)")[0]
    df["dx_egreso_cat"] = df["dx_egreso_principal"].str[:3]
    df["es_extranjera"] = np.where(df["nacionalidad"]=="Panameña","No","Sí")
    cps = ["cp_depresivo","cp_ansiedad","cp_personalidad","cp_bipolar","cp_esquizoafectivo","cp_esquizofrenia","cp_tdah","cp_discap_intelectual","cp_tea","cp_otros"]
    df["n_comorb_psiq_num"] = (df[cps]=="Sí").sum(axis=1)
    sx = ["sx_heteroagresion","sx_sensoperceptual","sx_delirante","sx_insomnio","sx_humor"]
    df["n_sintomas_ingreso"] = (df[sx]=="Sí").sum(axis=1)
    df["sx_psicotico"] = np.where((df["sx_sensoperceptual"]=="Sí")|(df["sx_delirante"]=="Sí"),"Sí","No")
    tx = ["tx_antipsicotico","tx_benzodiacepina","tx_estabilizador","tx_antidepresivo","tx_antiextrapiramidal","tx_lai","tx_med_urgencia"]
    df["n_farmacos"] = (df[tx]=="Sí").sum(axis=1)
    df["estancia_cat"] = pd.cut(df["dias_hosp"], [0,7,14,21,30,999], labels=["1–7","8–14","15–21","22–30",">30"])
    return df

pac = clean(pac); epi = clean(epi)
# episodios por paciente (derivado a nivel paciente)
n_ep = epi.groupby("id_paciente").size().rename("n_episodios")
pac = pac.merge(n_ep, left_on="id_paciente", right_index=True, how="left")
pac["reingreso_alguna_vez"] = pac["id_paciente"].map(epi.groupby("id_paciente")["reingreso_90d"].apply(lambda s: "Sí" if (s=="Sí").any() else "No"))

# ---------- 4. Validaciones ----------
val = {}
val["edad_min"] = float(pac["edad"].min()); val["menores_18"] = int((pac["edad"]<18).sum())
val["edad_inicio_> edad"] = int((pac["edad_inicio_consumo"]>pac["edad"]).sum())
val["egreso_sin_F1x"] = epi.loc[epi["dx_egreso_principal"].isna(), ["id_episodio","dx_egreso"]].to_dict("records")
val["inconsistencia_intentos"] = int(((pac["intento_suicida_previo"]=="Sí")&(pac["n_intentos_suicidas"]==0)).sum() + ((pac["intento_suicida_previo"]=="No")&(pac["n_intentos_suicidas"]>0)).sum())
val["inconsistencia_comorb"] = int(((pac["comorb_psiq"]=="Sí")&(pac["n_comorb_psiq_num"]==0)).sum() + ((pac["comorb_psiq"]=="No")&(pac["n_comorb_psiq_num"]>0)).sum())
val["inconsistencia_policonsumo"] = int(((pac["policonsumo"]=="Sí")&(pac["n_sustancias"]=="1")).sum())
val["inconsistencia_lai"] = int(((epi["tx_lai"]=="Sí")&(epi["tx_lai_tipo"]=="No aplica")).sum() + ((epi["tx_lai"]=="No")&(epi["tx_lai_tipo"]!="No aplica")).sum())
val["celdas_vacias_pac"] = {k:int(v) for k,v in pac.isna().sum().items() if v>0 and k not in ("comorb_medica_tipo","dx_egreso_principal","dx_egreso_cat")}
val["celdas_vacias_epi"] = {k:int(v) for k,v in epi.isna().sum().items() if v>0 and k not in ("comorb_medica_tipo","dx_egreso_principal","dx_egreso_cat")}
rep["validaciones"] = val
rep["filas_finales"] = {"pacientes": len(pac), "episodios": len(epi)}
rep["episodios_por_paciente"] = {str(k):int(v) for k,v in pac["n_episodios"].value_counts().sort_index().items()}
rep["categorias_unificadas"] = {k: list(v.items()) for k,v in MAPS.items()}

pac.to_csv("pacientes_limpio.csv", index=False); epi.to_csv("episodios_limpio.csv", index=False)
json.dump(rep, open("reporte_limpieza.json","w"), ensure_ascii=False, indent=2, default=str)
print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
