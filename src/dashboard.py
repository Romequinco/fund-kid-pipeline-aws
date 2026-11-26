"""Cuadro de mando de los KID. Streamlit en ECS Express Mode que solo lee de la API (D-4.1)."""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Fund KID", layout="wide")


@st.cache_data(ttl=600)
def get(ruta: str, **params) -> list | dict:
    r = requests.get(f"{API_URL}{ruta}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


st.title("Datos fundamentales de fondos")
st.caption("Extraídos de los KID publicados por cada gestora. Fuente y fecha de descarga en cada fila.")

with st.sidebar:
    sri = st.slider("Indicador de riesgo (SRI)", 1, 7, (1, 7))
    gestora = st.selectbox("Gestora", ["Todas", "bestinver", "azvalor", "cobas"])

filtros = {"sri_min": sri[0], "sri_max": sri[1]} | ({} if gestora == "Todas" else {"gestora": gestora})
df = pd.DataFrame(get("/fondos", **filtros))
for col in ("sri", "periodo_mantenimiento_anios", "gastos_corrientes_pct", "costes_entrada_pct", "costes_salida_pct"):
    if col in df:
        df[col] = pd.to_numeric(df[col], errors="coerce")  # por si la API devuelve decimales como texto

if df.empty:
    st.info("No hay fondos con esos filtros.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Clases", len(df))
c2.metric("SRI medio", f"{df['sri'].mean():.1f}")
c3.metric("Gastos corrientes medios", f"{df['gastos_corrientes_pct'].mean():.2f} %")

columnas = ["isin", "nombre_producto", "nombre_clase", "gestora", "sri", "periodo_mantenimiento_anios",
            "gastos_corrientes_pct", "costes_entrada_pct", "costes_salida_pct", "fecha_documento", "url_pdf"]
st.dataframe(df[columnas], hide_index=True, use_container_width=True,
             column_config={"url_pdf": st.column_config.LinkColumn("KID")})

st.subheader("Gastos corrientes frente a riesgo")
st.scatter_chart(df, x="sri", y="gastos_corrientes_pct", color="gestora_fuente")
