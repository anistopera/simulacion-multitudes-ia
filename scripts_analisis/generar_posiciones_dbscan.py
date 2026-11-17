"""Corre el motor de agentes (modo A, ruta fija) y guarda las posiciones cada 1 s.

Salida: capturas/datos/posiciones_S{1,2,3}_semilla{N}.csv con t, id, x, y, vx, vy
(solo agentes activos). Es el mismo formato de la telemetria acordada, recortado.
Cuando exista el CSV de telemetria real se puede usar directamente.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main():
    import csv, os
    from modulos.entorno import Entorno
    from modulos.agentes import generar_agentes, MotorAgentes

    SALIDA = RAIZ / "capturas" / "datos"
    os.makedirs(SALIDA, exist_ok=True)
    ent = Entorno(configuracion=str(RAIZ / "configuracion.json"))
    DURACION = 60  # s
    for esc, n in (("S1", 40), ("S2", 80), ("S3", 120)):
        for semilla in (42, 43, 44):
            ag = generar_agentes(ent, cantidad=n, semilla=semilla)
            motor = MotorAgentes(ent, ag)
            with open(f"{SALIDA}/posiciones_{esc}_semilla{semilla}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(["t", "id", "x", "y", "vx", "vy"])
                for seg in range(1, DURACION + 1):
                    for _ in range(10):
                        motor.actualizar(dt=0.1)
                    for a in motor.agentes_activos:
                        w.writerow([seg, a.id, round(a.x, 3), round(a.y, 3), round(a.vx, 3), round(a.vy, 3)])
            print(esc, semilla, "activos al final:", len(motor.agentes_activos), "llegados:", sum(a.llegado for a in ag))


if __name__ == "__main__":
    main()
