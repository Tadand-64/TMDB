# datos_tmdb.py · Capa de datos del dashboard (Práctica 12 · TMDB)
# Herramientas de Visualización · IDIA222
#
# Aquí vive todo lo que NO es interfaz: leer el token, consultar la API,
# guardar/leer respuesta.json y limpiar los datos. app.py solo dibuja.
#
# Este producto usa la API de TMDB, pero no está avalado ni certificado
# por TMDB.

import json
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests

BASE = "https://api.themoviedb.org/3"
ENDPOINT = f"{BASE}/discover/movie"
PARAMETROS = {
    "primary_release_date.gte": "2015-01-01",
    "primary_release_date.lte": "2024-12-31",
    "sort_by": "vote_count.desc",
    "include_adult": "false",
    "language": "es-MX",
}
PAGINAS = 20
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(CARPETA, "respuesta.json")
ARCHIVO_TOKEN = os.path.join(CARPETA, "token.txt")
POSTER = "https://image.tmdb.org/t/p/w185"


class ErrorTMDB(Exception):
    """Error con un mensaje listo para mostrarse en el dashboard."""


# ─── Condición 1 · El token vive fuera del código y se valida ──────────
def leer_token():
    token = os.environ.get("TMDB_TOKEN", "").strip()
    origen = "variable de entorno TMDB_TOKEN"
    if not token and os.path.exists(ARCHIVO_TOKEN):
        with open(ARCHIVO_TOKEN, encoding="utf-8") as f:
            token = f.read().strip().strip('"').strip("'")
        origen = "token.txt"

    if not token:
        raise ErrorTMDB(
            "No encontré el token de TMDB. Ponlo en token.txt (un solo "
            f"renglón) en la carpeta {CARPETA}, o en la variable de entorno "
            "TMDB_TOKEN.")

    # El token de lectura de TMDB es un JWT: "eyJ...", tres partes, >100 car.
    if not (token.startswith("eyJ") and token.count(".") == 2
            and len(token) > 100):
        if len(token) == 32:
            raise ErrorTMDB(
                f"El token en {origen} parece ser la «Clave de la API» (32 "
                "caracteres). Se necesita el «Token de acceso de lectura a la "
                "API», el largo que empieza con eyJ.")
        raise ErrorTMDB(
            f"El token en {origen} no tiene el formato esperado "
            f"({len(token)} caracteres). Debe empezar con eyJ y estar completo.")
    return token, origen


# ─── Condiciones 2 y 3 · Revisar estado y tipo de contenido ────────────
def pedir(url, params, token):
    try:
        respuesta = requests.get(
            url, params=params, timeout=60,
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/json",
                     "User-Agent": "UPQ-IDIA222/1.0"})
    except requests.RequestException as e:
        raise ErrorTMDB(f"No se pudo conectar con TMDB: {e.__class__.__name__}")

    estado = respuesta.status_code
    mensajes = {
        401: "401: TMDB rechazó el token. Revisa que sea el «Token de acceso "
             "de lectura» completo.",
        400: "400: la petición está mal armada (revisa los parámetros).",
        404: "404: ese recurso no existe; revisa la URL del endpoint.",
        429: "429: demasiadas peticiones seguidas. Espera unos segundos y "
             "usa respuesta.json.",
    }
    if estado in mensajes:
        raise ErrorTMDB(mensajes[estado])
    if estado >= 400:
        raise ErrorTMDB(f"TMDB respondió con estado {estado}.")

    # Un 200 no garantiza JSON: puede llegar una página de error en HTML
    if "json" not in (respuesta.headers.get("Content-Type") or ""):
        raise ErrorTMDB("La respuesta de TMDB no es JSON: "
                        + respuesta.text[:200])
    return respuesta.json()


# ─── Condición 4 · Descargar, guardar y reutilizar ─────────────────────
def descargar(paginas=PAGINAS, avance=None):
    """Consulta la API y guarda respuesta.json. `avance(i, n)` es opcional
    para que el dashboard muestre una barra de progreso."""
    token, _ = leer_token()
    generos = pedir(f"{BASE}/genre/movie/list", {"language": "es-MX"},
                    token)["genres"]
    peliculas, total = [], None
    for pagina in range(1, paginas + 1):
        datos = pedir(ENDPOINT, {**PARAMETROS, "page": pagina}, token)
        total = datos.get("total_results", total)
        peliculas.extend(datos["results"])
        if avance:
            avance(pagina, paginas)
        if pagina >= datos.get("total_pages", paginas):
            break
        time.sleep(0.3)                       # no saturar el servidor

    paquete = {
        "fuente": "TMDB API · https://developer.themoviedb.org",
        "endpoint": ENDPOINT,
        "parametros": PARAMETROS,
        "paginas": paginas,
        "descargado": datetime.now().isoformat(timespec="seconds"),
        "total_results": total,
        "genres": generos,
        "results": peliculas,
    }
    texto = json.dumps(paquete, ensure_ascii=False, indent=1)
    texto = texto.replace(token, "TOKEN_OCULTO")   # el archivo sí se entrega
    assert token not in texto
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(texto)
    return paquete


def cargar_guardado():
    if not os.path.exists(ARCHIVO):
        return None
    with open(ARCHIVO, encoding="utf-8") as f:
        return json.load(f)


def buscar_pelicula(texto):
    """Búsqueda en vivo (endpoint /search/movie) para la pestaña de consulta."""
    token, _ = leer_token()
    datos = pedir(f"{BASE}/search/movie",
                  {"query": texto, "language": "es-MX",
                   "include_adult": "false", "page": 1}, token)
    return datos.get("results", [])


# ─── Condición 5 · Estructura y limpieza documentada ───────────────────
def limpiar(datos):
    """Devuelve (df limpio, bitácora de limpieza como lista de textos)."""
    nombre_genero = {g["id"]: g["name"] for g in datos["genres"]}
    filas = []
    for p in datos["results"]:
        ids = p.get("genre_ids") or []
        filas.append({
            "id": p.get("id"),
            "titulo": p.get("title"),
            "titulo_original": p.get("original_title"),
            "estreno": p.get("release_date"),
            "calificacion": p.get("vote_average"),
            "votos": p.get("vote_count"),
            "popularidad": p.get("popularity"),
            "idioma": p.get("original_language"),
            "genero": nombre_genero.get(ids[0]) if ids else None,
            "generos": ", ".join(nombre_genero.get(i, str(i)) for i in ids),
            "poster": p.get("poster_path"),
            "sinopsis": p.get("overview"),
        })
    df = pd.DataFrame(filas)
    log = []
    n_inicial = len(df)
    log.append(f"Registros al cargar: {n_inicial}")
    faltantes = df[["titulo", "estreno", "calificacion", "votos",
                    "popularidad", "genero"]].isna().sum()
    log.append("Faltantes al cargar: " + (
        ", ".join(f"{c}={v}" for c, v in faltantes.items() if v) or "ninguno"))

    dup = int(df.duplicated(subset="id").sum())
    df = df.drop_duplicates(subset="id")
    log.append(f"Duplicados eliminados (mismo id): {dup}")

    antes = df["estreno"].notna().sum()
    df["estreno"] = pd.to_datetime(df["estreno"], format="%Y-%m-%d",
                                   errors="coerce")
    log.append("estreno: texto → fecha; perdidos al convertir: "
               f"{antes - df['estreno'].notna().sum()}")

    for col in ["calificacion", "votos", "popularidad"]:
        antes = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        log.append(f"{col}: a número; perdidos al convertir: "
                   f"{antes - df[col].notna().sum()}")

    sin_votos = int((df["votos"] == 0).sum())
    df.loc[df["votos"] == 0, "calificacion"] = np.nan
    log.append(f"Calificación con 0 votos tratada como faltante: {sin_votos}")

    df = df.dropna(subset=["estreno", "genero", "calificacion"]
                   ).reset_index(drop=True)
    df["anio"] = df["estreno"].dt.year.astype(int)

    principales = df["genero"].value_counts().head(7).index
    df["genero_grupo"] = df["genero"].where(df["genero"].isin(principales),
                                            "Otros")
    log.append(f"Registros utilizables (con fecha, género y calificación): "
               f"{len(df)}")
    log.append(f"Géneros: 7 principales + «Otros» "
               f"({df['genero_grupo'].nunique()} grupos)")
    return df, log
