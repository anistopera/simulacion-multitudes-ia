"""Calibracion de DBSCAN sobre las posiciones del motor de agentes (5.4)."""
import csv, glob, os
from modulos.dbscan_deteccion import calibrar, cargar_instantes_csv

SALIDA = "capturas_dbscan"
campos = ["escenario", "eps", "min_samples", "clusters_prom", "ruido_pct",
          "silhouette", "davies_bouldin", "instantes_con_2_clusters", "instantes"]
with open(f"{SALIDA}/calibracion_dbscan.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=campos); w.writeheader()
    for esc in ("S1", "S2", "S3"):
        instantes = []
        for ruta in sorted(glob.glob(f"{SALIDA}/datos/posiciones_{esc}_semilla*.csv")):
            instantes += [X for X in cargar_instantes_csv(ruta) if len(X) >= 3]
        for f in calibrar(instantes):
            f["escenario"] = esc
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in f.items() if k in campos})
        print(esc, "instantes:", len(instantes))
