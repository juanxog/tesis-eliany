# Mujeres hospitalizadas por trastornos por uso de sustancias en el INSAM (Panamá), 2022–2025

Código de análisis y página de resultados del trabajo de graduación
**«Características sociodemográficas y clínicas de mujeres hospitalizadas por trastornos por uso de sustancias en el Instituto Nacional de Salud Mental (octubre 2022 – octubre 2025): estudio retrospectivo»**.

- Investigadora principal: Dra. Eliany Luzcando A. (Residencia de Psiquiatría, INSAM)
- Asesora clínica: Dra. Juana Herrera
- Asesor metodológico: Ing. Juan Andrés Girón
- Protocolo v2.0 aprobado por el Comité de Bioética en Investigación del Hospital Dr. José Renán Esquivel (CBIHN-2026020002) y registrado en RESEGIS (5054).

**Informe interactivo:** https://juanxog.github.io/tesis-eliany/

## Qué hay aquí

| Carpeta / archivo | Contenido |
|---|---|
| `analisis/01_limpieza.py` | Limpieza, unificación de categorías, variables derivadas y anonimización. |
| `analisis/02_eda.py` | Descriptivo, bivariado (χ², Fisher, OR, Mann-Whitney, Kruskal-Wallis), cribado con FDR, V de Cramér. |
| `analisis/03_clustering.py` | Perfiles clínicos: distancia de Gower, PAM y jerárquico, silueta, bootstrap, sensibilidad. |
| `analisis/05_modelo.py` | Modelo de abandono del tratamiento: logística con EE robustos por paciente, validación cruzada agrupada, bootstrap, puntaje. |
| `analisis/06_xai.py` | Explicabilidad: SHAP, permutación, contrafactuales, dependencia parcial. |
| `analisis/04_informe.py` | Genera la página de resultados a partir de los JSON. |
| `analisis/graficas/` | Figuras PNG a 150 dpi. |
| `analisis/*.json` | Resultados agregados (sin datos individuales). |
| `docs/index.html` | Página de resultados servida por GitHub Pages. |

## Datos

**Este repositorio no contiene datos de pacientes.** La base anonimizada y la llave de identificación se custodian en el INSAM según el protocolo aprobado. Los archivos `.csv`, `.xlsx`, `.docx` y `.pdf` están excluidos por `.gitignore`. Todo lo publicado son agregados (frecuencias, medianas, coeficientes, figuras).

## Reproducir

Requiere Python 3.11 con pandas, numpy, scipy, scikit-learn, matplotlib y shap. Con la base anonimizada en la carpeta raíz:

```bash
cd analisis
python3 01_limpieza.py && python3 02_eda.py && python3 03_clustering.py && python3 05_modelo.py && python3 06_xai.py && python3 04_informe.py
```

## Estado

Trabajo en revisión previo a la sustentación. Los resultados son preliminares hasta la defensa de la tesis; la página lleva la etiqueta `noindex` para no ser indexada por buscadores mientras tanto.
