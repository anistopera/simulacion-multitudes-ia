"""Figuras de 5.4 con posiciones reales del motor de agentes (capturas/datos).

Version 3: sin pandas (solo numpy, matplotlib y csv) y con distincion visual entre
puntos nucleo (relleno), frontera (hueco) y ruido (x gris).
"""

import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DPI = 300


def cargar_posiciones(ruta):
    """CSV t,id,x,y,vx,vy -> {t: array (n, 4) con x, y, vx, vy}."""
    import numpy as np
    por_t = {}
    with open(ruta, newline="", encoding="utf-8") as fh:
        for f in csv.DictReader(fh):
            por_t.setdefault(float(f["t"]), []).append(
                (float(f["x"]), float(f["y"]), float(f["vx"]), float(f["vy"])))
    return {t: np.array(v) for t, v in por_t.items()}


def main():
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D
    from modulos.entorno import Entorno
    from modulos.dbscan_deteccion import (clasificar_puntos, proporcion_ruido,
                                          TIPO_NUCLEO, TIPO_FRONTERA)

    SAL = RAIZ / "capturas"
    ent = Entorno(configuracion=str(RAIZ / "configuracion.json"))
    COL = ["#2a7ab0", "#d4602a", "#3a9a5b", "#8a5bb5", "#c9a227", "#2aa5a5"]
    MAR = ["o", "s", "^", "D", "v", "P"]
    GRIS, TINTA = "#8a8f98", "#222222"
    datos = {e: cargar_posiciones(SAL / "datos" / f"posiciones_{e}_semilla42.csv")
             for e in ("S1", "S2", "S3")}

    def XY(esc, t):
        d = datos[esc][float(t)]
        return d[:, :2], d

    def recinto(ax):
        ax.imshow(ent.mapa, origin="lower", extent=(0, ent.ancho, 0, ent.alto),
                  cmap=ListedColormap(["#ffffff", "#5b6573"]), vmin=0, vmax=1, interpolation="nearest")
        ax.scatter(*ent.entrada, color="#1f4fd8", marker=">", s=50, zorder=3)
        ax.scatter(*ent.salida, color="#e08a00", marker="*", s=80, zorder=3)
        ax.set(xlim=(0, ent.ancho), ylim=(0, ent.alto), aspect="equal")
        ax.set_xticks(range(0, 31, 5)); ax.set_yticks(range(0, 21, 5)); ax.tick_params(labelsize=7, colors="#555")
        for s in ax.spines.values(): s.set_color(TINTA)

    def panel(ax, X, eps, mp, titulo):
        et, tipos, cl = clasificar_puntos(X, eps, mp)
        recinto(ax)
        r = et == -1
        ax.scatter(X[r, 0], X[r, 1], s=12, c=GRIS, marker="x", linewidths=0.8)
        for i, c in enumerate(cl):
            col, mar = COL[i % 6], MAR[i % 6]
            nuc = (et == c["id"]) & (tipos == TIPO_NUCLEO)
            fro = (et == c["id"]) & (tipos == TIPO_FRONTERA)
            ax.scatter(X[nuc, 0], X[nuc, 1], s=16, c=col, marker=mar, edgecolors="white", linewidths=0.3,
                       label=f"Grupo {i + 1} ({c['tamano']}: {c['n_nucleo']} núcleo, {c['n_frontera']} frontera)")
            if fro.any():
                ax.scatter(X[fro, 0], X[fro, 1], s=18, facecolors="none", edgecolors=col, marker=mar, linewidths=1.0)
            ax.plot(c["centro_x"], c["centro_y"], "+", c=TINTA, ms=9, mew=1.4)
        ax.set_title((f"{titulo}\n{len(cl)} {'grupo' if len(cl) == 1 else 'grupos'}, {100 * proporcion_ruido(et):.0f}% ruido")
                     .replace(".", ","), fontsize=9, color=TINTA)
        return et, cl

    # Fig 1: instante congestionado S3, con leyenda y tipos de punto
    X, _ = XY("S3", 20)
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    et, cl = panel(ax, X, 1.2, 5, "DBSCAN, eps = 1,2 m, min_samples = 5 (S3, 120 agentes, t = 20 s)")
    h, l = ax.get_legend_handles_labels()
    h += [Line2D([], [], marker="o", ls="", mfc="#555", mec="white", label="Relleno: núcleo"),
          Line2D([], [], marker="o", ls="", mfc="none", mec="#555", label="Hueco: frontera"),
          Line2D([], [], marker="x", ls="", c=GRIS, label="Ruido")]
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(SAL / "fig_clusters_120.png", dpi=DPI); plt.close(fig)
    print("FIG1", len(X), [(c["tamano"], c["n_nucleo"], c["n_frontera"]) for c in cl], "ruido", int((et == -1).sum()))

    # Fig 2: efecto de eps en ese instante
    fig, axs = plt.subplots(2, 2, figsize=(9, 6.4))
    for ax, eps in zip(axs.ravel(), (0.8, 1.2, 1.5, 2.0)):
        e2, c2 = panel(ax, X, eps, 5, f"eps = {str(eps).replace('.', ',')} m")
        print("FIG2", eps, len(c2), int((e2 == -1).sum()), [c["tamano"] for c in c2])
    fig.suptitle("Efecto de eps sobre el mismo instante (S3, t = 20 s, min_samples = 5)", fontsize=10)
    fig.tight_layout(); fig.savefig(SAL / "fig_efecto_eps.png", dpi=DPI); plt.close(fig)

    # Fig 3: evolucion en el tiempo en S3
    fig, axs = plt.subplots(1, 4, figsize=(14, 3.4))
    for ax, t in zip(axs, (1, 10, 20, 60)):
        Xt, _ = XY("S3", t); e3, c3 = panel(ax, Xt, 1.2, 5, f"t = {t} s ({len(Xt)} agentes)")
        print("FIG3", t, len(c3), [c["tamano"] for c in c3])
    fig.tight_layout(); fig.savefig(SAL / "fig_evolucion_S3.png", dpi=DPI); plt.close(fig)

    # Fig 4: tamano del grupo principal y velocidad media de sus miembros
    estilos = {"S1": ("#2a7ab0", "-", "S1 (40 agentes)"), "S2": ("#d4602a", "--", "S2 (80 agentes)"),
               "S3": ("#3a9a5b", ":", "S3 (120 agentes)")}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for esc, por_t in datos.items():
        ts, tam, vel = [], [], []
        for t in sorted(por_t):
            g = por_t[t]
            et, cl = clasificar_puntos(g[:, :2], 1.2, 5)[0::2]
            if not cl: continue
            k = cl[0]["id"]; v = np.hypot(g[:, 2], g[:, 3])[et == k]
            ts.append(t); tam.append(cl[0]["tamano"]); vel.append(v.mean())
        c_, ls, nom = estilos[esc]
        a1.plot(ts, tam, color=c_, ls=ls, lw=2, label=nom); a2.plot(ts, vel, color=c_, ls=ls, lw=2, label=nom)
        print("FIG4", esc, "tam final", tam[-1], "vel final", round(vel[-1], 2), "tam max", max(tam))
    a1.set(xlabel="Tiempo (s)", ylabel="Agentes en el grupo principal", title="Tamaño del grupo principal")
    a2.set(xlabel="Tiempo (s)", ylabel="Velocidad media (m/s)", title="Velocidad media de sus miembros")
    for a in (a1, a2):
        a.grid(alpha=0.25); a.spines[["top", "right"]].set_visible(False); a.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(SAL / "fig_grupo_principal_tiempo.png", dpi=DPI); plt.close(fig)


if __name__ == "__main__":
    main()
