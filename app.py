"""
app.py — Dashboard del dueño · TécnicoFlow UY

Ejecutar:
    python seed_data.py      (una sola vez, crea la base de ejemplo)
    streamlit run app.py

Para producción: reemplazar la conexión en data.py por Supabase/PostgreSQL.
La lógica de KPIs no cambia.
"""
import streamlit as st
import pandas as pd
import altair as alt
import os
import data as d

st.set_page_config(page_title="TécnicoFlow UY — Dashboard",
                   page_icon="🔧", layout="wide")

# ----------------------------------------------------------------- estilos
INK, BLUE, AMBER, GREEN, PAPER = "#191510", "#2347E5", "#E8820C", "#1FA85A", "#F4F0E8"
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@700;800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {{ font-family:'Hanken Grotesk',sans-serif; }}
h1,h2,h3,h4 {{ font-family:'Bricolage Grotesque',sans-serif !important; letter-spacing:-.02em; }}
.stApp {{ background:{PAPER}; }}
[data-testid="stMetric"] {{
    background:#fff; border:1px solid #E0D9CC; border-radius:16px;
    padding:16px 18px; box-shadow:0 6px 16px -10px rgba(25,21,16,.25);
}}
[data-testid="stMetricValue"] {{ font-family:'Hanken Grotesk'; font-weight:700; }}
[data-testid="stMetricLabel"] p {{ font-weight:600; color:#5C554A; }}
section[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid #E0D9CC; }}
</style>
""", unsafe_allow_html=True)

fmt = lambda n: f"$ {n:,.0f}".replace(",", ".")

# ----------------------------------------------------------------- carga
if not os.path.exists("tecnicoflow.db"):
    import seed_data
    seed_data.main()  # crea la base de ejemplo automáticamente la primera vez

@st.cache_data
def cargar():
    return d.get_orders(), d.get_empresa()

df_all, empresa = cargar()

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🔧 Técnico**Flow**")
    st.selectbox("Empresa", [empresa["nombre_fantasia"]], disabled=True)
    st.caption(f"RUT {empresa['rut']} · plan {empresa['plan'].upper()}")
    st.divider()
    tecnicos = sorted(df_all["tecnico"].dropna().unique().tolist())
    sel = st.multiselect("Filtrar por técnico", tecnicos, default=tecnicos)
    st.divider()
    st.caption("Datos de ejemplo · prototipo de validación. "
               "El “mes actual” es el último mes cerrado.")

df = df_all[df_all["tecnico"].isin(sel)] if sel else df_all
mes, mes_prev = d.periodos(df)
mes_nom = pd.Period(mes, "M").strftime("%B %Y").capitalize() if mes else "—"

# ----------------------------------------------------------------- header
st.markdown(f"## Hola, Fernando 👋")
st.markdown(f"**{empresa['nombre_fantasia']}** · resumen de **{mes_nom}**")
st.write("")

# ----------------------------------------------------------------- HERO: plata sin cobrar
monto_sc, n_sc, df_sc = d.plata_sin_cobrar(df)
st.markdown(f"""
<div style="background:linear-gradient(160deg,#FDF4E6,#FBEAD2);border:1px solid #F2D9AE;
     border-radius:18px;padding:20px 22px;box-shadow:0 12px 28px -12px rgba(25,21,16,.22);">
  <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{AMBER};">
     ● Plata sin cobrar</div>
  <div style="font-family:'Hanken Grotesk';font-weight:700;font-size:42px;color:{INK};margin:4px 0 2px;">
     {fmt(monto_sc)}</div>
  <div style="font-size:14px;color:#9A6410;font-weight:600;">
     {n_sc} trabajos terminados que todavía no facturaste</div>
</div>
""", unsafe_allow_html=True)

with st.expander(f"Ver los {n_sc} trabajos sin facturar →"):
    tabla_sc = df_sc[["cliente", "tipo_servicio", "tecnico", "total", "finalizada_en"]].copy()
    tabla_sc["finalizada_en"] = pd.to_datetime(tabla_sc["finalizada_en"]).dt.strftime("%d/%m")
    tabla_sc["total"] = tabla_sc["total"].apply(fmt)
    tabla_sc.columns = ["Cliente", "Servicio", "Técnico", "Monto", "Terminado"]
    st.dataframe(tabla_sc, hide_index=True, use_container_width=True)
    st.caption("En la versión real, un botón arma la factura electrónica (CFE) de todos en un toque.")

st.write("")

# ----------------------------------------------------------------- KPIs (las 5 métricas)
k = d.kpis_mes(df, mes, mes_prev)
rec_pct, rec_n = d.recurrentes_pct(df)
delta_fact = ((k["facturacion"] / k["facturacion_prev"] - 1) * 100) if k["facturacion_prev"] else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Facturación del mes", fmt(k["facturacion"]), f"{delta_fact:+.1f}% vs. mes anterior")
c2.metric("Margen estimado", f"{k['margen_pct']:.0f}%",
          help="Ingresos menos costo de materiales y mano de obra.")
c3.metric("Ticket promedio", fmt(k["ticket_promedio"]),
          help=f"Sobre {k['ordenes_facturadas']} órdenes facturadas.")
c4.metric("Clientes que repiten", f"{rec_pct:.0f}%", f"{rec_n} clientes",
          help="Clientes con 2 o más trabajos en el período.")

st.write("")

# ----------------------------------------------------------------- gráficos
g1, g2 = st.columns([1.3, 1])

with g1:
    st.markdown("#### Facturación · últimos 6 meses")
    serie = d.serie_mensual(df)
    serie["Mes"] = serie["mes"].apply(lambda m: pd.Period(m, "M").strftime("%b %y"))
    chart = (alt.Chart(serie).mark_bar(size=34, cornerRadiusTopLeft=6, cornerRadiusTopRight=6,
                                       color=BLUE)
             .encode(x=alt.X("Mes:N", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
                     y=alt.Y("facturacion:Q", axis=alt.Axis(title=None, format="~s")),
                     tooltip=[alt.Tooltip("Mes:N"),
                              alt.Tooltip("facturacion:Q", title="Facturación", format=",.0f")])
             .properties(height=260))
    st.altair_chart(chart, use_container_width=True)

with g2:
    st.markdown("#### Órdenes por técnico")
    pt = d.por_tecnico(df, mes)
    chart2 = (alt.Chart(pt).mark_bar(cornerRadiusEnd=6, color=AMBER)
              .encode(y=alt.Y("tecnico:N", sort="-x", axis=alt.Axis(title=None)),
                      x=alt.X("ordenes:Q", axis=alt.Axis(title=None)),
                      tooltip=[alt.Tooltip("tecnico:N", title="Técnico"),
                               alt.Tooltip("ordenes:Q", title="Órdenes"),
                               alt.Tooltip("facturacion:Q", title="Facturación", format=",.0f")])
              .properties(height=260))
    st.altair_chart(chart2, use_container_width=True)

# ----------------------------------------------------------------- por tipo + tabla
g3, g4 = st.columns([1, 1.3])

with g3:
    st.markdown("#### Facturación por tipo de servicio")
    pti = d.por_tipo(df, mes)
    chart3 = (alt.Chart(pti).mark_bar(cornerRadiusEnd=6, color=GREEN)
              .encode(y=alt.Y("tipo_servicio:N", sort="-x", axis=alt.Axis(title=None)),
                      x=alt.X("total:Q", axis=alt.Axis(title=None, format="~s")),
                      tooltip=[alt.Tooltip("tipo_servicio:N", title="Servicio"),
                               alt.Tooltip("total:Q", title="Facturación", format=",.0f")])
              .properties(height=300))
    st.altair_chart(chart3, use_container_width=True)

with g4:
    st.markdown("#### Últimas órdenes de servicio")
    ult = d.ultimas_ordenes(df)
    badge = {"facturada": "🟢 Facturada", "finalizada": "🟠 Sin facturar",
             "en_curso": "🔵 En curso", "agendada": "⚪ Agendada", "cancelada": "⚫ Cancelada"}
    ult = ult.copy()
    ult["estado"] = ult["estado"].map(badge)
    ult["total"] = ult["total"].apply(lambda x: fmt(x) if pd.notna(x) else "—")
    ult.columns = ["Cliente", "Zona", "Servicio", "Técnico", "Estado", "Monto"]
    st.dataframe(ult, hide_index=True, use_container_width=True, height=300)

st.write("")
st.caption("TécnicoFlow UY · dashboard del dueño · datos de ejemplo (Sanitaria El Águila)")
