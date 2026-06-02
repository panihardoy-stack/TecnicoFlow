"""
data.py — Capa de datos de TécnicoFlow UY.

Lee de 'tecnicoflow.db' y devuelve los DataFrames / KPIs que consume el
dashboard. No depende de Streamlit, así que se puede testear sola.

Para migrar a Supabase/PostgreSQL en el futuro, basta con reemplazar
get_orders() por una consulta sobre la nueva conexión: la lógica de KPIs
(que trabaja sobre el DataFrame) no cambia.
"""
import sqlite3
import pandas as pd

DB = "tecnicoflow.db"
LABOR_COST_RATIO = 0.65  # del 'mano_obra', cuánto es costo (pago al técnico)


def get_conn():
    return sqlite3.connect(DB)


def get_empresa(empresa_id=1):
    con = get_conn()
    row = pd.read_sql(
        "SELECT * FROM empresas WHERE id = ?", con, params=(empresa_id,)).iloc[0]
    con.close()
    return row


def get_orders(empresa_id=1):
    """Órdenes con cliente, técnico, zona y costo de materiales agregado."""
    con = get_conn()
    q = """
    SELECT os.id, os.estado, os.tipo_servicio, os.prioridad,
           os.mano_obra, os.total, os.facturada,
           os.finalizada_en, os.creado_en,
           c.id AS cliente_id, c.nombre AS cliente,
           d.zona, u.nombre AS tecnico,
           COALESCE(m.mat_precio, 0) AS mat_precio,
           COALESCE(m.mat_costo, 0)  AS mat_costo
    FROM ordenes_servicio os
    JOIN clientes  c ON c.id = os.cliente_id
    LEFT JOIN direcciones d ON d.id = os.direccion_id
    JOIN usuarios  u ON u.id = os.tecnico_id
    LEFT JOIN (
        SELECT os_id,
               SUM(cantidad * precio_unit) AS mat_precio,
               SUM(cantidad * costo_unit)  AS mat_costo
        FROM os_materiales GROUP BY os_id
    ) m ON m.os_id = os.id
    WHERE os.empresa_id = ?
    """
    df = pd.read_sql(q, con, params=(empresa_id,))
    con.close()

    df["finalizada_en"] = pd.to_datetime(df["finalizada_en"])
    df["creado_en"] = pd.to_datetime(df["creado_en"])
    df["mes"] = df["finalizada_en"].dt.to_period("M").astype(str)
    # costo total = materiales + parte del mano de obra (pago al técnico)
    df["costo_total"] = df["mat_costo"] + LABOR_COST_RATIO * df["mano_obra"]
    df["margen_$"] = df["total"] - df["costo_total"]
    return df


# ---------------------------------------------------------------- KPIs
def periodos(df):
    """Devuelve (mes_actual, mes_anterior) como strings 'YYYY-MM'."""
    meses = sorted([m for m in df["mes"].dropna().unique()
                    if m not in (None, "NaT")])
    if not meses:
        return None, None
    actual = meses[-1]
    anterior = meses[-2] if len(meses) > 1 else None
    return actual, anterior


def facturado_mes(df, mes):
    f = df[(df["estado"] == "facturada") & (df["mes"] == mes)]
    return float(f["total"].sum())


def kpis_mes(df, mes, mes_prev):
    fact = df[(df["estado"] == "facturada") & (df["mes"] == mes)]
    return {
        "facturacion": float(fact["total"].sum()),
        "facturacion_prev": facturado_mes(df, mes_prev) if mes_prev else 0.0,
        "ordenes_facturadas": int(len(fact)),
        "ticket_promedio": float(fact["total"].mean()) if len(fact) else 0.0,
        "margen_pct": (float(fact["margen_$"].sum() / fact["total"].sum() * 100)
                       if fact["total"].sum() else 0.0),
    }


def plata_sin_cobrar(df):
    """Trabajos terminados que todavía no se facturaron (la métrica estrella)."""
    sc = df[(df["estado"] == "finalizada") & (df["facturada"] == 0)]
    return float(sc["total"].sum()), int(len(sc)), sc


def recurrentes_pct(df, meses=6):
    cerradas = df[df["estado"].isin(["facturada", "finalizada"])]
    if cerradas.empty:
        return 0.0, 0
    cnt = cerradas.groupby("cliente_id").size()
    repiten = int((cnt >= 2).sum())
    return (repiten / len(cnt) * 100), repiten


def serie_mensual(df, n=6):
    s = (df[df["estado"] == "facturada"]
         .groupby("mes")["total"].sum().sort_index().tail(n))
    return s.reset_index().rename(columns={"total": "facturacion"})


def por_tecnico(df, mes):
    d = df[(df["estado"].isin(["facturada", "finalizada"])) & (df["mes"] == mes)]
    g = (d.groupby("tecnico")
         .agg(ordenes=("id", "count"), facturacion=("total", "sum"))
         .reset_index().sort_values("ordenes", ascending=False))
    return g


def por_tipo(df, mes):
    d = df[(df["estado"] == "facturada") & (df["mes"] == mes)]
    g = (d.groupby("tipo_servicio")["total"].sum()
         .reset_index().sort_values("total", ascending=False))
    return g


def ultimas_ordenes(df, n=12):
    d = df.dropna(subset=["creado_en"]).sort_values("creado_en", ascending=False).head(n)
    return d[["cliente", "zona", "tipo_servicio", "tecnico", "estado", "total"]]


if __name__ == "__main__":
    df = get_orders()
    a, p = periodos(df)
    print("Mes actual:", a, "| anterior:", p)
    print("KPIs:", kpis_mes(df, a, p))
    monto, cnt, _ = plata_sin_cobrar(df)
    print(f"Sin cobrar: ${monto:,.0f} en {cnt} órdenes")
    print("Recurrentes:", recurrentes_pct(df))
