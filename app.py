# ED.03.03
# Práctica 12 a Dashboard - TMDB (The Movie Database)
# Herramientas de Visualización - IDIA222 - Unidad III
#
#     pip install -r requirements.txt
#     streamlit run app.py
#

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import datos_tmdb as tm

GRIS = "#B9C3D1"
AZUL = "#1C4C9A"
NARANJA = "#E69F00"
TEXTO_NARANJA = "#7A5300"
FUENTE = "Fuente: TMDB (themoviedb.org)"

st.set_page_config(page_title="Dashboard TMDB · IDIA222", page_icon="🎬",
                   layout="wide")


def estilo(fig, titulo, x, y, alto=430):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16)),
        xaxis_title=x, yaxis_title=y, height=alto, template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=60), showlegend=False,
        annotations=list(fig.layout.annotations) + [dict(
            text=FUENTE, xref="paper", yref="paper", x=1, y=-0.18,
            showarrow=False, font=dict(size=10, color="#666666"),
            xanchor="right")])
    return fig


# Carga de datos (archivo guardado o API en vivo)
@st.cache_data(show_spinner=False)
def preparar(marca_archivo):
    """marca_archivo (fecha de modificación) invalida la caché al refrescar."""
    datos = tm.cargar_guardado()
    if datos is None:
        return None, None, None
    df, log = tm.limpiar(datos)
    return df, log, {k: datos.get(k) for k in
                     ("descargado", "total_results", "endpoint", "paginas")}


st.sidebar.title("TMDB - IDIA222")
st.sidebar.caption("Las 400 películas más votadas estrenadas de 2015 a 2024")

with st.sidebar.expander("Fuente de datos", expanded=not os.path.exists(tm.ARCHIVO)):
    st.write("Por defecto se usa **respuesta.json** (0 peticiones). "
             "El botón vuelve a consultar la API con tu token.")
    if st.button("（￣︶￣）↗　 Actualizar desde la API", use_container_width=True):
        barra = st.progress(0.0, text="Consultando TMDB…")
        try:
            tm.descargar(avance=lambda i, n: barra.progress(
                i / n, text=f"Página {i} de {n}"))
            st.cache_data.clear()
            st.success("respuesta.json actualizado")
        except tm.ErrorTMDB as e:
            st.error(str(e))
        barra.empty()
    try:
        _, origen = tm.leer_token()
        st.caption(f" Token válido leído desde {origen}")
    except tm.ErrorTMDB as e:
        st.caption(f" （︶^︶） {e}")

if not os.path.exists(tm.ARCHIVO):
    st.warning("Aún no hay respuesta.json. Pon tu token en token.txt y pulsa "
               "«Actualizar desde la API» en la barra lateral.")
    st.stop()

df_total, bitacora, meta = preparar(os.path.getmtime(tm.ARCHIVO))

# Filtros
st.sidebar.subheader("Filtros")
a_min, a_max = int(df_total["anio"].min()), int(df_total["anio"].max())
anios = st.sidebar.slider("Año de estreno", a_min, a_max, (a_min, a_max))
grupos = sorted(df_total["genero_grupo"].unique())
sel_generos = st.sidebar.multiselect("Género principal", grupos, default=grupos)
v_min, v_max = int(df_total["votos"].min()), int(df_total["votos"].max())
min_votos = st.sidebar.number_input("Mínimo de votos", v_min, v_max, v_min,
                                    step=500)
idiomas = df_total["idioma"].value_counts()
sel_idioma = st.sidebar.selectbox(
    "Idioma original", ["Todos"] + [f"{i} ({n})" for i, n in idiomas.items()])

df = df_total[df_total["anio"].between(*anios)
              & df_total["genero_grupo"].isin(sel_generos)
              & (df_total["votos"] >= min_votos)]
if sel_idioma != "Todos":
    df = df[df["idioma"] == sel_idioma.split(" ")[0]]

st.sidebar.caption(f"Descargado el {meta['descargado']} · "
                   "Este producto usa la API de TMDB, pero no está avalado "
                   "ni certificado por TMDB.")

# Encabezado y KPIs
st.title("¿Cómo califica el público a las películas más vistas?")
st.caption(f"{len(df)} de {len(df_total)} películas con los filtros actuales · "
           f"TMDB reporta {meta['total_results']:,} películas en 2015–2024")

if len(df) < 5:
    st.info("Con estos filtros quedan menos de 5 películas; amplía la "
            "selección para ver las gráficas.")
    st.stop()

cal = df["calificacion"]
mediana = cal.median()
rel = df[df["votos"] > 0].copy()
rel["log_votos"] = np.log10(rel["votos"])
r = rel["log_votos"].corr(rel["calificacion"]) if len(rel) > 2 else np.nan

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Películas", f"{len(df)}")
k2.metric("Calificación mediana", f"{mediana:.2f}",
          f"{mediana - df_total['calificacion'].median():+.2f} vs. total"
          if len(df) != len(df_total) else None)
k3.metric("Bajo 6", f"{(cal < 6).mean() * 100:.1f} %")
k4.metric("8 o más", f"{(cal >= 8).mean() * 100:.1f} %")
k5.metric("r (votos vs. calificación)", f"{r:.2f}")

t1, t2, t3, t4, t5, t6 = st.tabs([
    " Distribución", " Comparación", " Relación", " Evolución",
    " Explorar datos", " Buscar en TMDB"])

# 1.- DISTRIBUCIÓN

with t1:
    fig = go.Figure(go.Histogram(
        x=cal, xbins=dict(start=np.floor(cal.min() * 4) / 4, end=10, size=0.25),
        marker=dict(color=GRIS, line=dict(color="white", width=1)),
        hovertemplate="%{x}: %{y} películas<extra></extra>"))
    fig.add_vline(x=mediana, line=dict(color=AZUL, width=3),
                  annotation_text=f"<b>Mediana: {mediana:.1f}</b>",
                  annotation_font_color=AZUL)
    estilo(fig, f"La mitad tiene {mediana:.1f} o más; "
           f"{(cal < 6).mean() * 100:.0f} % baja de 6 y "
           f"{(cal >= 8).mean() * 100:.0f} % llega a 8",
           "Calificación promedio de los usuarios de TMDB (0 a 10)",
           "Número de películas")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    q1, q3 = cal.quantile([0.25, 0.75])
    c1.markdown(f"**Mitad central:** de {q1:.1f} a {q3:.1f}. Entre las "
                "películas que mucha gente vio el público casi no reprueba: "
                "un 6.5 ya es una calificación baja en este grupo.")
    extremos = pd.concat([df.nsmallest(3, "calificacion"),
                          df.nlargest(3, "calificacion")])
    c2.dataframe(extremos[["titulo", "anio", "calificacion", "votos"]]
                 .rename(columns=str.capitalize), hide_index=True,
                 use_container_width=True)

# 2.- COMPARACIÓN

with t2:
    conteo = df["genero_grupo"].value_counts()
    validos = conteo[conteo >= 10].index               # mínimo 10 por grupo
    comp = df[df["genero_grupo"].isin(validos)]
    if comp.empty:
        st.info("Ningún género tiene al menos 10 películas con estos filtros.")
    else:
        orden = comp.groupby("genero_grupo")["calificacion"].median() \
                    .sort_values()                     # abajo - arriba
        mejor, peor = orden.index[-1], orden.index[0]
        fig = go.Figure()
        for g in orden.index:
            sub = comp[comp["genero_grupo"] == g]
            color = AZUL if g == mejor else GRIS
            fig.add_trace(go.Box(
                x=sub["calificacion"], name=f"{g} (n={conteo[g]})",
                marker_color=color, fillcolor=color,
                line=dict(color="#333333", width=1), boxpoints="outliers",
                text=sub["titulo"], orientation="h",
                hovertemplate="%{text}: %{x}<extra></extra>"))
        estilo(fig, f"{mejor} es el género mejor calificado (mediana "
               f"{orden[mejor]:.1f}); {peor}, el más bajo ({orden[peor]:.1f})",
               "Calificación promedio (0 a 10)", "Género principal", alto=480)
        st.plotly_chart(fig, use_container_width=True)

        resumen = comp.groupby("genero_grupo").agg(
            peliculas=("id", "size"), mediana=("calificacion", "median"),
            rango_intercuartil=("calificacion",
                                lambda s: s.quantile(.75) - s.quantile(.25)),
            votos_medianos=("votos", "median")
        ).sort_values("mediana", ascending=False).round(2)
        st.dataframe(resumen, use_container_width=True)
        st.caption("Rango intercuartil = ancho de la caja: entre más grande, "
                   "más irregular es el género. Los grupos con menos de 10 "
                   "películas no se comparan.")

# 3.- RELACIÓN

with t3:
    if len(rel) < 5 or rel["log_votos"].nunique() < 2:
        st.info("Se necesitan más películas para estimar la relación.")
    else:
        pend, inter = np.polyfit(rel["log_votos"], rel["calificacion"], 1)
        rel["diferencia"] = rel["calificacion"] - (pend * rel["log_votos"]
                                                   + inter)
        n_fuera = st.slider("Películas a resaltar (las más alejadas de la "
                            "tendencia)", 0, 10, 4)
        fuera = rel.loc[rel["diferencia"].abs().nlargest(n_fuera).index]

        if abs(r) < 0.2:
            lectura = "Tener más votos casi no dice nada de la calificación"
        elif r > 0:
            lectura = ("Las más votadas tienden a estar mejor calificadas"
                       if r >= 0.4 else
                       "Más votos van con calificación un poco más alta")
        else:
            lectura = "Las más votadas tienden a calificarse más bajo"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rel["votos"], y=rel["calificacion"], mode="markers",
            marker=dict(color=GRIS, size=8, opacity=0.85),
            customdata=np.stack([rel["titulo"], rel["anio"],
                                 rel["genero"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                          "%{customdata[2]}<br>%{x:,} votos · %{y}"
                          "<extra></extra>"))
        xs = np.linspace(rel["log_votos"].min(), rel["log_votos"].max(), 50)
        fig.add_trace(go.Scatter(x=10 ** xs, y=pend * xs + inter, mode="lines",
                                 line=dict(color=AZUL, width=3),
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=fuera["votos"], y=fuera["calificacion"], mode="markers+text",
            marker=dict(color=NARANJA, size=11), text=fuera["titulo"],
            textposition="top right", textfont=dict(color=TEXTO_NARANJA,
                                                    size=11),
            hovertemplate="<b>%{text}</b><br>%{x:,} votos · %{y}"
                          "<extra></extra>"))
        fig.update_xaxes(type="log")
        estilo(fig, f"{lectura} (r = {r:.2f}); en naranja, las más alejadas "
               "de la tendencia", "Número de votos (escala logarítmica)",
               "Calificación promedio (0 a 10)", alto=520)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"Cada vez que los votos se multiplican por 10, la "
                    f"calificación sube en promedio **{pend:.2f} puntos**. "
                    "La dispersión es grande: la fama atrae votos, no "
                    "necesariamente buena calificación.")

# 4.- EVOLUCIÓN

with t4:
    por_anio = df.groupby("anio")["calificacion"].agg(
        mediana="median", p25=lambda s: s.quantile(0.25),
        p75=lambda s: s.quantile(0.75), n="size")
    por_anio = por_anio[por_anio["n"] >= 5]           # años con pocas fuera
    if len(por_anio) < 2:
        st.info("Se necesitan al menos 2 años con 5 películas o más.")
    else:
        k = min(3, len(por_anio) // 2)
        ini, fin = por_anio.index[:k], por_anio.index[-k:]
        m0 = df[df["anio"].isin(ini)]["calificacion"].median()
        m1 = df[df["anio"].isin(fin)]["calificacion"].median()
        rango = lambda a: f"{a[0]}–{a[-1]}" if len(a) > 1 else f"{a[0]}"
        if abs(m1 - m0) < 0.15:
            titulo4 = (f"La calificación típica casi no cambió: {m0:.1f} en "
                       f"{rango(ini)} contra {m1:.1f} en {rango(fin)}")
        else:
            titulo4 = (f"La calificación típica {'bajó' if m1 < m0 else 'subió'}"
                       f" de {m0:.1f} ({rango(ini)}) a {m1:.1f} ({rango(fin)})")

        x = list(por_anio.index)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=list(por_anio["p75"]) + list(por_anio["p25"])[::-1],
            fill="toself", fillcolor="rgba(185,195,209,0.55)",
            line=dict(width=0), hoverinfo="skip", name="Mitad central"))
        fig.add_trace(go.Scatter(
            x=x, y=por_anio["mediana"], mode="lines+markers",
            line=dict(color=AZUL, width=3), marker=dict(size=9),
            customdata=por_anio["n"],
            hovertemplate="%{x}: mediana %{y:.2f} (%{customdata} películas)"
                          "<extra></extra>"))
        fig.add_annotation(x=x[0], y=por_anio["p75"].iloc[0], xanchor="left",
                           yanchor="bottom", showarrow=False,
                           text="franja: la mitad central de las películas",
                           font=dict(size=11, color="#555555"))
        fig.update_xaxes(dtick=1)
        estilo(fig, titulo4, "Año de estreno", "Calificación promedio (0 a 10)")
        st.plotly_chart(fig, use_container_width=True)

        fig_n = go.Figure(go.Bar(x=x, y=por_anio["n"], marker_color=GRIS,
                                 text=por_anio["n"], textposition="outside"))
        fig_n.update_xaxes(dtick=1)
        estilo(fig_n, "Cuántas películas de cada año entran al top 400",
               "Año de estreno", "Películas", alto=300)
        st.plotly_chart(fig_n, use_container_width=True)
        st.warning("**Ojo con el sesgo de selección:** como se tomaron las "
                    "más votadas, de los años recientes solo entran las muy "
                    "exitosas (las demás aún no juntan votos). La subida es "
                    "en buena parte efecto de esa selección.")

# 5.- EXPLORAR DATOS

with t5:
    orden_por = st.radio("Ordenar por", ["votos", "calificacion",
                                         "popularidad", "estreno"],
                         horizontal=True)
    tabla = df.sort_values(orden_por, ascending=False).assign(
        poster=lambda d: d["poster"].map(
            lambda p: f"{tm.POSTER}{p}" if isinstance(p, str) and p else None),
        estreno=lambda d: d["estreno"].dt.date)
    st.dataframe(
        tabla[["poster", "titulo", "estreno", "genero", "generos",
               "calificacion", "votos", "popularidad", "idioma"]],
        hide_index=True, use_container_width=True, height=520,
        column_config={
            "poster": st.column_config.ImageColumn("Póster", width="small"),
            "titulo": "Título", "estreno": "Estreno",
            "genero": "Género principal", "generos": "Todos los géneros",
            "calificacion": st.column_config.ProgressColumn(
                "Calificación", min_value=0, max_value=10, format="%.1f"),
            "votos": st.column_config.NumberColumn("Votos", format="%d"),
            "popularidad": st.column_config.NumberColumn("Popularidad",
                                                         format="%.1f"),
            "idioma": "Idioma"})
    st.download_button("⬇️ Descargar CSV filtrado",
                       df.drop(columns=["poster", "sinopsis"])
                       .to_csv(index=False).encode("utf-8-sig"),
                       "peliculas_tmdb_filtrado.csv", "text/csv")
    with st.expander("Bitácora de limpieza"):
        for linea in bitacora:
            st.write("• " + linea)
        st.code(f"GET {meta['endpoint']}\n" + "\n".join(
            f"  {k} = {v}" for k, v in tm.PARAMETROS.items())
            + f"\n  page = 1 … {meta['paginas']}", language="text")

# 6.- BÚSQUEDA EN VIVO 
with t6:
    st.write("Consulta en vivo al endpoint **/search/movie** con tu token "
             "(1 petición por búsqueda).")
    consulta = st.text_input("Título de la película", placeholder="Dune")
    if consulta:
        try:
            resultados = tm.buscar_pelicula(consulta)
        except tm.ErrorTMDB as e:
            st.error(str(e))
            resultados = []
        if not resultados:
            st.info("Sin resultados.")
        mediana_total = df_total["calificacion"].median()
        for p in resultados[:8]:
            c_img, c_txt = st.columns([1, 6])
            if p.get("poster_path"):
                c_img.image(f"{tm.POSTER}{p['poster_path']}")
            votos, calif = p.get("vote_count", 0), p.get("vote_average", 0)
            en_top = p.get("id") in set(df_total["id"])
            c_txt.markdown(
                f"**{p.get('title')}** ({(p.get('release_date') or '')[:4]})"
                + (" · 🏆 está en el top 400" if en_top else ""))
            if votos:
                c_txt.caption(f"⭐ {calif:.1f} con {votos:,} votos · "
                              f"{calif - mediana_total:+.1f} vs. la mediana "
                              f"del top 400 ({mediana_total:.1f})")
            else:
                c_txt.caption("Sin votos todavía")
            c_txt.write((p.get("overview") or "")[:300])
            st.divider()
