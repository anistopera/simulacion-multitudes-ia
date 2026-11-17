"""Figuras de 5.4 con posiciones reales del motor de agentes (capturas_dbscan/datos)."""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from modulos.entorno import Entorno
from modulos.dbscan_deteccion import detectar_grupos, proporcion_ruido

SAL = "capturas_dbscan"
ent = Entorno(configuracion="configuracion.json")
COL = ["#2a7ab0", "#d4602a", "#3a9a5b", "#8a5bb5", "#c9a227", "#2aa5a5"]
MAR = ["o", "s", "^", "D", "v", "P"]
GRIS, TINTA = "#8a8f98", "#222222"
datos = {e: pd.read_csv(f"{SAL}/datos/posiciones_{e}_semilla42.csv") for e in ("S1", "S2", "S3")}


def XY(esc, t):
    d = datos[esc]; d = d[d.t == t]
    return d[["x", "y"]].to_numpy(), d


def recinto(ax):
    ax.imshow(ent.mapa, origin="lower", extent=(0, ent.ancho, 0, ent.alto),
              cmap=ListedColormap(["#ffffff", "#5b6573"]), vmin=0, vmax=1, interpolation="nearest")
    ax.scatter(*ent.entrada, color="#1f4fd8", marker=">", s=50, zorder=3)
    ax.scatter(*ent.salida, color="#e08a00", marker="*", s=80, zorder=3)
    ax.set(xlim=(0, ent.ancho), ylim=(0, ent.alto), aspect="equal")
    ax.set_xticks(range(0, 31, 5)); ax.set_yticks(range(0, 21, 5)); ax.tick_params(labelsize=7, colors="#555")
    for s in ax.spines.values(): s.set_color(TINTA)


def panel(ax, X, eps, mp, titulo):
    et, cl = detectar_grupos(X, eps, mp); recinto(ax)
    r = et == -1
    ax.scatter(X[r, 0], X[r, 1], s=12, c=GRIS, marker="x", linewidths=0.8, label="Ruido")
    for i, c in enumerate(cl):
        m = et == c["id"]
        ax.scatter(X[m, 0], X[m, 1], s=16, c=COL[i % 6], marker=MAR[i % 6], edgecolors="white",
                   linewidths=0.3, label=f"Grupo {i + 1} ({c['tamano']})")
        ax.plot(c["centro_x"], c["centro_y"], "+", c=TINTA, ms=9, mew=1.4)
    ax.set_title((f"{titulo}\n{len(cl)} {'grupo' if len(cl) == 1 else 'grupos'}, {100 * proporcion_ruido(et):.0f}% ruido")
                 .replace(".", ","), fontsize=9, color=TINTA)
    return et, cl


# Fig 1: instante congestionado S3, leyenda
X, _ = XY("S3", 20)
fig, ax = plt.subplots(figsize=(7.5, 5.2))
et, cl = panel(ax, X, 1.2, 5, f"DBSCAN, eps = 1,2 m, min_samples = 5 (S3, 120 agentes, t = 20 s)")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(f"{SAL}/fig_clusters_120.png", dpi=200); plt.close(fig)
print("FIG1", len(X), [(c["tamano"], round(c["centro_x"], 1), round(c["centro_y"], 1)) for c in cl], "ruido", int((et == -1).sum()))

# Fig 2: efecto de eps en ese instante
fig, axs = plt.subplots(2, 2, figsize=(9, 6.4))
for ax, eps in zip(axs.ravel(), (0.8, 1.2, 1.5, 2.0)):
    e2, c2 = panel(ax, X, eps, 5, f"eps = {str(eps).replace('.', ',')} m")
    print("FIG2", eps, len(c2), int((e2 == -1).sum()), [c["tamano"] for c in c2])
fig.suptitle("Efecto de eps sobre el mismo instante (S3, t = 20 s, min_samples = 5)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{SAL}/fig_efecto_eps.png", dpi=200); plt.close(fig)

# Fig 3: evolucion en el tiempo en S3
fig, axs = plt.subplots(1, 4, figsize=(14, 3.4))
for ax, t in zip(axs, (1, 10, 20, 60)):
    Xt, _ = XY("S3", t); e3, c3 = panel(ax, Xt, 1.2, 5, f"t = {t} s ({len(Xt)} agentes)")
    print("FIG3", t, len(c3), [c["tamano"] for c in c3])
fig.tight_layout(); fig.savefig(f"{SAL}/fig_evolucion_S3.png", dpi=200); plt.close(fig)

# Fig 4: tamano del grupo principal y velocidad media de sus miembros
estilos = {"S1": ("#2a7ab0", "-", "S1 (40 agentes)"), "S2": ("#d4602a", "--", "S2 (80 agentes)"), "S3": ("#3a9a5b", ":", "S3 (120 agentes)")}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
for esc, d in datos.items():
    ts, tam, vel = [], [], []
    for t, g in d.groupby("t"):
        X_ = g[["x", "y"]].to_numpy()
        et, cl = detectar_grupos(X_, 1.2, 5)
        if not cl: continue
        k = cl[0]["id"]; v = np.hypot(g.vx.to_numpy(), g.vy.to_numpy())[et == k]
        ts.append(t); tam.append(cl[0]["tamano"]); vel.append(v.mean())
    c_, ls, nom = estilos[esc]
    a1.plot(ts, tam, color=c_, ls=ls, lw=2, label=nom); a2.plot(ts, vel, color=c_, ls=ls, lw=2, label=nom)
    print("FIG4", esc, "tam final", tam[-1], "vel final", round(vel[-1], 2), "tam max", max(tam))
a1.set(xlabel="Tiempo (s)", ylabel="Agentes en el grupo principal", title="Tamaño del grupo principal")
a2.set(xlabel="Tiempo (s)", ylabel="Velocidad media (m/s)", title="Velocidad media de sus miembros")
for a in (a1, a2):
    a.grid(alpha=0.25); a.spines[["top", "right"]].set_visible(False); a.legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(f"{SAL}/fig_grupo_principal_tiempo.png", dpi=200); plt.close(fig)
