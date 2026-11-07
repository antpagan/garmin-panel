"""Descarga tus actividades de Garmin (API personal) y genera panel.html.

No guarda datos en el repositorio: el archivo se crea en el servidor de GitHub
Actions, se cifra con tu contraseña y solo se publica la versión cifrada.
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DIAS_ATRAS = 730      # cuántos días de historial descargar (2 años)
POR_PAGINA = 100      # actividades por petición
MAX_PAGINAS = 50      # tope de seguridad


def descargar():
    desde = (date.today() - timedelta(days=DIAS_ATRAS)).isoformat()
    todas = []
    inicio = 0
    for _ in range(MAX_PAGINAS):
        r = subprocess.run(
            ["gc-personal", "activities",
             "--start", str(inicio), "--limit", str(POR_PAGINA),
             "--start-date", desde],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # Solo mostramos el código de error y los mensajes técnicos del cliente
            print("Error al pedir actividades a Garmin. Código:", r.returncode)
            print(r.stderr[-1500:])
            sys.exit(1)
        try:
            pagina = json.loads(r.stdout)
        except json.JSONDecodeError:
            print("Garmin devolvió algo que no es JSON.")
            sys.exit(1)
        if not pagina:
            break
        todas.extend(pagina)
        inicio += POR_PAGINA
    return todas


def num(valor, defecto=0.0):
    try:
        return float(valor) if valor is not None else defecto
    except (TypeError, ValueError):
        return defecto


def reducir(a):
    """Se queda solo con lo necesario para el panel (sin datos de perfil)."""
    tipo = (a.get("activityType") or {}).get("typeKey") or "other"
    zonas = [round(num(a.get(f"hrTimeInZone_{i}")) / 60, 1) for i in range(1, 6)]
    return {
        "id": a.get("activityId"),
        "fecha": (a.get("startTimeLocal") or "")[:19],
        "nombre": a.get("activityName") or "",
        "tipo": tipo,
        "km": round(num(a.get("distance")) / 1000, 3),
        "min": round(num(a.get("duration")) / 60, 2),
        "fc": round(num(a.get("averageHR"))) or None,
        "fcmax": round(num(a.get("maxHR"))) or None,
        "kcal": round(num(a.get("calories"))) or None,
        "carga": round(num(a.get("activityTrainingLoad"))) or None,
        "zonas": zonas,
    }


def construir(actividades, salida="panel.html"):
    reducidas = [reducir(a) for a in actividades if a.get("startTimeLocal")]
    datos = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "actividades": reducidas,
    }
    texto = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    plantilla = Path(__file__).with_name("plantilla.html").read_text(encoding="utf-8")
    Path(salida).write_text(plantilla.replace("__DATOS__", texto), encoding="utf-8")
    print(f"Panel creado con {len(reducidas)} actividades.")


if __name__ == "__main__":
    construir(descargar())
