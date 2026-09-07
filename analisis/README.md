# Análisis — Tesis Dra. Eliany Luzcando (INSAM, oct 2022 – oct 2025)

Pipeline reproducible en Python (protocolo v2.0, plan de análisis).

| Archivo | Qué es |
|---|---|
| `01_limpieza.py` | Limpia, unifica categorías, deriva variables y **anonimiza** (códigos F-edad-nnn). |
| `02_eda.py` | Descriptivo + bivariado (χ², Fisher, OR, Mann-Whitney, Kruskal-Wallis) + cribado con FDR + V de Cramér. |
| `03_clustering.py` | Clustering no supervisado: distancia de Gower, PAM y jerárquico, silueta/codo, bootstrap. |
| `05_modelo.py` | Modelos predictivos: abandono del tratamiento (logística con EE robustos por paciente, VC agrupada, bootstrap, puntaje), conducta parasuicida y reingreso. |
| `06_xai.py` | Explicabilidad: SHAP (logística exacta y TreeSHAP), permutación, ejemplos, contrafactuales, dependencia parcial. |
| `04_informe.py` | Genera `informe.html` (página de resultados, modelo y contraste con la literatura) a partir de los JSON. |
| `pacientes_limpio.csv` / `episodios_limpio.csv` | Bases anónimas (118 pacientes / 173 episodios). |
| `pacientes_cluster.csv` | Asignación de clúster por paciente. |
| `llave_identificacion.csv` | **Nombre/cédula ↔ código. NO compartir. Mover a USB institucional y borrar de aquí.** |
| `reporte_limpieza.json`, `eda_resultados.json`, `cluster_resultados.json`, `modelo_resultados.json`, `xai_resultados.json` | Resultados numéricos. |
| `graficas/` | PNG a 150 dpi listos para el documento Word. |
| `informe.html` | Informe web (versión para el artifact de Claude). |
| `../docs/index.html` | **Versión autónoma para hospedar** (GitHub Pages la sirve desde `/docs`). Solo resultados agregados. |
| `.gitignore` | Bloquea CSV, Excel, Word y la llave: nunca deben subirse a un repositorio. |

Ejecutar en orden:
```
python3 01_limpieza.py && python3 02_eda.py && python3 03_clustering.py && python3 05_modelo.py && python3 06_xai.py && python3 04_informe.py
```
