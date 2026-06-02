"""
TécnicoFlow UY — Dashboard del dueño (versión todo-en-uno)
Ejecutar: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import altair as alt
import sqlite3, os, random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ═══════════════════════════════════════════════════════ CONFIG
st.set_page_config(page_title="TécnicoFlow UY", page_icon="🔧", layout="wide")
DB = "tecnicoflow.db"
random.seed(42)
LABOR_COST_RATIO = 0.65
INK, BLUE, AMBER, GREEN = "#191510", "#2347E5", "#E8820C", "#1FA85A"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@700;800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
html,body,[class*="css"],.stMarkdown{font-family:'Hanken Grotesk',sans-serif;}
h1,h2,h3,h4{font-family:'Bricolage Grotesque',sans-serif !important;letter-spacing:-.02em;}
.stApp{background:#F4F0E8;}
[data-testid="stMetric"]{background:#fff;border:1px solid #E0D9CC;border-radius:16px;
    padding:16px 18px;box-shadow:0 6px 16px -10px rgba(25,21,16,.25);}
[data-testid="stMetricLabel"] p{font-weight:600;color:#5C554A;}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #E0D9CC;}
</style>
""", unsafe_allow_html=True)

fmt = lambda n: f"$ {n:,.0f}".replace(",", ".")

# ═══════════════════════════════════════════════════════ SCHEMA
SCHEMA = """
DROP TABLE IF EXISTS os_materiales;
DROP TABLE IF EXISTS ordenes_servicio;
DROP TABLE IF EXISTS materiales;
DROP TABLE IF EXISTS direcciones;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS empresas;
CREATE TABLE empresas(id INTEGER PRIMARY KEY,razon_social TEXT,nombre_fantasia TEXT,rut TEXT,rubro TEXT,plan TEXT);
CREATE TABLE usuarios(id INTEGER PRIMARY KEY,empresa_id INTEGER,nombre TEXT,rol TEXT,telefono TEXT,activo INTEGER);
CREATE TABLE clientes(id INTEGER PRIMARY KEY,empresa_id INTEGER,nombre TEXT,tipo_doc TEXT,documento TEXT,telefono TEXT,email TEXT);
CREATE TABLE direcciones(id INTEGER PRIMARY KEY,cliente_id INTEGER,calle TEXT,numero TEXT,zona TEXT,departamento TEXT);
CREATE TABLE materiales(id INTEGER PRIMARY KEY,empresa_id INTEGER,nombre TEXT,unidad TEXT,costo REAL,precio REAL);
CREATE TABLE ordenes_servicio(id INTEGER PRIMARY KEY,empresa_id INTEGER,cliente_id INTEGER,direccion_id INTEGER,tecnico_id INTEGER,tipo_servicio TEXT,estado TEXT,prioridad TEXT,agendada_para TEXT,iniciada_en TEXT,finalizada_en TEXT,descripcion TEXT,mano_obra REAL,total REAL,facturada INTEGER,creado_en TEXT);
CREATE TABLE os_materiales(id INTEGER PRIMARY KEY,os_id INTEGER,material_id INTEGER,cantidad REAL,precio_unit REAL,costo_unit REAL);
"""

# ═══════════════════════════════════════════════════════ SEED
def crear_base():
    TECNICOS=[("Richard",0.45),("Marcelo",0.34),("Diego",0.21)]
    ZONAS=["Pocitos","Cordón","Malvín","Buceo","Carrasco","La Blanqueada",
           "Centro","Punta Carretas","Cerro","Sayago","Prado","Parque Rodó"]
    ZONAS_INT=[("Las Piedras","Canelones"),("Pando","Canelones"),("Maldonado","Maldonado")]
    TIPOS=[("Reparación de canilla",1200,1),("Destape de cámara",2400,1),
           ("Cambio de flexible",1100,2),("Revisión de cañería",1600,1),
           ("Instalación de calefón",4800,3),("Reparación de pérdida",1900,2),
           ("Instalación de sanitarios",6500,3),("Mantenimiento preventivo",2200,2)]
    TIPOS_GRANDES={"Instalación de calefón","Instalación de sanitarios","Destape de cámara"}
    MATS=[("Flexible 1/2\"","unidad",230,420),("Teflón","unidad",35,60),
          ("Llave de paso","unidad",210,380),("Caño PVC 40mm","metro",90,165),
          ("Codo PVC","unidad",25,55),("Sellador silicona","unidad",140,250),
          ("Sifón","unidad",180,340),("Membrana de inodoro","unidad",95,180),
          ("Cuerito / junta","unidad",12,35),("Mezcladora","unidad",1200,2100)]
    NOMBRES_M=["Juan","Diego","Martín","Sebastián","Gabriel","Federico","Andrés",
               "Rodrigo","Gonzalo","Pablo","Nicolás","Matías","Santiago","Joaquín"]
    NOMBRES_F=["María","Laura","Andrea","Valeria","Mónica","Lucía","Sofía",
               "Camila","Patricia","Beatriz","Rosa","Elena","Carolina","Florencia"]
    APELLIDOS=["Rodríguez","Fernández","González","Pérez","Sosa","Méndez","Píriz",
               "Castro","Bentancor","Núñez","Ferreira","Olivera","Techera","Bermúdez",
               "Vázquez","Cabrera","Suárez","Lemos","Acosta","Cardozo","Da Silva"]
    EMPRESAS_CLI=["Edificio Las Acacias","Consorcio Río Branco","Club La Blanqueada",
        "Inmobiliaria Sur","Estudio Jurídico Lema","Colegio San Pablo",
        "Ferretería El Tornillo","Gimnasio FitClub","Restó La Pasiva","Bar El Ancla",
        "Panadería La Espiga","Edicampo SRL","Edificio Torre del Puerto",
        "Consorcio Pocitos Plaza","Hotel Mirador","Cooperativa COVISA",
        "Administración Delfino","Edificio Brisas","Farmacia San Roque",
        "Clínica Dental Sonrisas","Lavadero El Sol","Edificio Aurora",
        "Inmobiliaria Costa","Café Brasilero","Residencial Los Pinos",
        "Edificio Mar y Sol","Consorcio Buceo","Pizzería Nápoli",
        "Almacén Doña Pepa","Hostal del Centro"]
    CALLES=["Av. Rivera","Av. Italia","18 de Julio","Bvar. Artigas","Av. Brasil","Comercio"]

    con=sqlite3.connect(DB); cur=con.cursor(); cur.executescript(SCHEMA)
    cur.execute("INSERT INTO empresas VALUES(?,?,?,?,?,?)",
                (1,"El Águila Servicios SRL","Sanitaria El Águila","21 555 1234 0012","sanitaria","pro"))
    cur.execute("INSERT INTO usuarios VALUES(?,?,?,?,?,?)",(1,1,"Fernando Aguirre","dueno","+59899100200",1))
    tec_ids=[]
    for i,(nom,_) in enumerate(TECNICOS,start=2):
        cur.execute("INSERT INTO usuarios VALUES(?,?,?,?,?,?)",(i,1,nom,"tecnico",f"+5989910{i:04d}",1))
        tec_ids.append(i)
    tec_w=[w for _,w in TECNICOS]
    for i,(nom,uni,c,p) in enumerate(MATS,start=1):
        cur.execute("INSERT INTO materiales VALUES(?,?,?,?,?,?)",(i,1,nom,uni,c,p))

    clientes=[]
    cid=0
    for nombre in EMPRESAS_CLI:
        cid+=1; clientes.append((cid,random.randint(5,11)))
        cur.execute("INSERT INTO clientes VALUES(?,?,?,?,?,?,?)",
            (cid,1,nombre,"RUT",f"21{random.randint(100000,999999)}001{random.randint(0,9)}",
             f"+5989{random.randint(1000000,9999999)}",f"cli{cid}@mail.com"))
        z,d=random.choice(ZONAS),"Montevideo"
        cur.execute("INSERT INTO direcciones VALUES(?,?,?,?,?,?)",
            (cid,cid,random.choice(CALLES),str(random.randint(800,6500)),z,d))
    for _ in range(90):
        cid+=1; clientes.append((cid,random.randint(2,5)))
        nm=random.choice(NOMBRES_M+NOMBRES_F)+" "+random.choice(APELLIDOS)
        cur.execute("INSERT INTO clientes VALUES(?,?,?,?,?,?,?)",
            (cid,1,nm,"CI",f"{random.randint(1,5)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(0,9)}",
             f"+5989{random.randint(1000000,9999999)}",f"cli{cid}@mail.com"))
        if random.random()<0.82: z,dp=random.choice(ZONAS),"Montevideo"
        else: z,dp=random.choice(ZONAS_INT)
        cur.execute("INSERT INTO direcciones VALUES(?,?,?,?,?,?)",
            (cid,cid,random.choice(CALLES),str(random.randint(800,6500)),z,dp))
    for _ in range(140):
        cid+=1; clientes.append((cid,1))
        nm=random.choice(NOMBRES_M+NOMBRES_F)+" "+random.choice(APELLIDOS)
        cur.execute("INSERT INTO clientes VALUES(?,?,?,?,?,?,?)",
            (cid,1,nm,"CI",f"{random.randint(1,5)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(0,9)}",
             f"+5989{random.randint(1000000,9999999)}",f"cli{cid}@mail.com"))
        if random.random()<0.82: z,dp=random.choice(ZONAS),"Montevideo"
        else: z,dp=random.choice(ZONAS_INT)
        cur.execute("INSERT INTO direcciones VALUES(?,?,?,?,?,?)",
            (cid,cid,random.choice(CALLES),str(random.randint(800,6500)),z,dp))

    order_clients=[]
    for c,n in clientes: order_clients+=[c]*n
    random.shuffle(order_clients)

    hoy=datetime.now()
    primer_mes=hoy.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    fin=primer_mes-timedelta(days=1)
    ult_mes=primer_mes-relativedelta(months=1)
    meses=[ult_mes-relativedelta(months=k) for k in range(5,-1,-1)]
    mes_w=[0.80,0.88,0.95,1.04,1.20,1.48]
    reciente=fin-timedelta(days=35)

    ordenes=[]
    for cl in order_clients:
        m=random.choices(meses,weights=mes_w)[0]
        d=m.replace(day=random.randint(1,28),hour=random.randint(8,17),minute=random.choice([0,30]))
        tipo=random.choice(TIPOS)
        ordenes.append({"cli":cl,"fecha":d,"tipo":tipo,
                        "tec":random.choices(tec_ids,weights=tec_w)[0],
                        "mo":round(tipo[1]*random.uniform(.85,1.25),-1),"estado":"facturada"})
    ordenes.sort(key=lambda o:o["fecha"])
    for o in random.sample(ordenes,k=int(len(ordenes)*0.03)): o["estado"]="cancelada"
    recientes=[o for o in ordenes if o["fecha"]>=reciente and o["estado"]=="facturada"]
    recientes.sort(key=lambda o:o["fecha"])
    for o in recientes[-6:]: o["estado"]=random.choice(["en_curso","agendada"])
    cands=[o for o in recientes[:-6] if o["tipo"][0] in TIPOS_GRANDES] or recientes[:-6]
    cands.sort(key=lambda o:o["mo"],reverse=True)
    for o in cands[:8]: o["estado"]="finalizada"

    osid=0; osmid=0
    for o in ordenes:
        osid+=1
        cerrada=o["estado"] in ("facturada","finalizada")
        tn,_,nm=o["tipo"]
        mats=random.sample(range(1,len(MATS)+1),k=min(nm+random.randint(0,1),len(MATS)))
        mp=0.0
        for mid in mats:
            osmid+=1; _,_,costo,precio=MATS[mid-1]; cant=random.choice([1,1,1,2,3])
            mp+=precio*cant
            cur.execute("INSERT INTO os_materiales VALUES(?,?,?,?,?,?)",(osmid,osid,mid,cant,precio,costo))
        total=round(o["mo"]+mp,-1)
        ini=o["fecha"]; fin2=ini+timedelta(hours=random.choice([1,1,2,3]))
        cur.execute("INSERT INTO ordenes_servicio VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (osid,1,o["cli"],o["cli"],o["tec"],tn,o["estado"],
             random.choice(["normal","normal","alta"]),ini.isoformat(),
             ini.isoformat() if o["estado"]!="agendada" else None,
             fin2.isoformat() if cerrada else None,tn,o["mo"],
             total if cerrada else None,1 if o["estado"]=="facturada" else 0,ini.isoformat()))
    con.commit(); con.close()

# ═══════════════════════════════════════════════════════ DATOS
@st.cache_data
def cargar_todo():
    if not os.path.exists(DB):
        crear_base()
    con=sqlite3.connect(DB)
    empresa=pd.read_sql("SELECT * FROM empresas WHERE id=1",con).iloc[0]
    df=pd.read_sql("""
        SELECT os.id,os.estado,os.tipo_servicio,os.mano_obra,os.total,os.facturada,
               os.finalizada_en,os.creado_en,
               c.id AS cliente_id,c.nombre AS cliente,d.zona,u.nombre AS tecnico,
               COALESCE(m.mp,0) AS mat_precio,COALESCE(m.mc,0) AS mat_costo
        FROM ordenes_servicio os
        JOIN clientes c ON c.id=os.cliente_id
        LEFT JOIN direcciones d ON d.id=os.direccion_id
        JOIN usuarios u ON u.id=os.tecnico_id
        LEFT JOIN(SELECT os_id,SUM(cantidad*precio_unit) mp,SUM(cantidad*costo_unit) mc
                  FROM os_materiales GROUP BY os_id) m ON m.os_id=os.id
        WHERE os.empresa_id=1""",con)
    con.close()
    df["finalizada_en"]=pd.to_datetime(df["finalizada_en"])
    df["creado_en"]=pd.to_datetime(df["creado_en"])
    df["mes"]=df["finalizada_en"].dt.to_period("M").astype(str)
    df.loc[df["mes"]=="NaT","mes"]=pd.NA
    df["costo_total"]=df["mat_costo"]+LABOR_COST_RATIO*df["mano_obra"]
    df["margen"]=df["total"]-df["costo_total"]
    return df, empresa

df_all, empresa = cargar_todo()

def periodos(df):
    meses=sorted([m for m in df["mes"].dropna().unique() if m not in (None,"NaT")])
    return (meses[-1],meses[-2]) if len(meses)>=2 else (meses[-1] if meses else None,None)

mes,mes_prev=periodos(df_all)

# ═══════════════════════════════════════════════════════ SIDEBAR
with st.sidebar:
    st.markdown("### 🔧 Técnico**Flow**")
    st.caption(f"{empresa['nombre_fantasia']}\nRUT {empresa['rut']} · plan {empresa['plan'].upper()}")
    st.divider()
    tecnicos=sorted(df_all["tecnico"].dropna().unique().tolist())
    sel=st.multiselect("Filtrar por técnico",tecnicos,default=tecnicos)
    st.divider()
    st.caption("Datos de ejemplo · prototipo de validación.")

df=df_all[df_all["tecnico"].isin(sel)] if sel else df_all
mes_nom=pd.Period(mes,"M").strftime("%B %Y").capitalize() if mes else "—"

# ═══════════════════════════════════════════════════════ HEADER
st.markdown("## Hola, Fernando 👋")
st.markdown(f"**{empresa['nombre_fantasia']}** · resumen de **{mes_nom}**")
st.write("")

# ═══════════════════════════════════════════════════════ HERO
sc=df[(df["estado"]=="finalizada")&(df["facturada"]==0)]
monto_sc,n_sc=float(sc["total"].sum()),len(sc)
st.markdown(f"""
<div style="background:linear-gradient(160deg,#FDF4E6,#FBEAD2);border:1px solid #F2D9AE;
     border-radius:18px;padding:20px 22px;box-shadow:0 12px 28px -12px rgba(25,21,16,.22);">
  <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{AMBER};">● Plata sin cobrar</div>
  <div style="font-weight:700;font-size:42px;color:{INK};margin:4px 0 2px;">{fmt(monto_sc)}</div>
  <div style="font-size:14px;color:#9A6410;font-weight:600;">{n_sc} trabajos terminados que todavía no facturaste</div>
</div>""",unsafe_allow_html=True)

with st.expander(f"Ver los {n_sc} trabajos sin facturar →"):
    t=sc[["cliente","tipo_servicio","tecnico","total","finalizada_en"]].copy()
    t["finalizada_en"]=pd.to_datetime(t["finalizada_en"]).dt.strftime("%d/%m")
    t["total"]=t["total"].apply(fmt)
    t.columns=["Cliente","Servicio","Técnico","Monto","Terminado"]
    st.dataframe(t,hide_index=True,use_container_width=True)

st.write("")

# ═══════════════════════════════════════════════════════ KPIs
fact=df[(df["estado"]=="facturada")&(df["mes"]==mes)]
fact_prev=df[(df["estado"]=="facturada")&(df["mes"]==mes_prev)]
facturacion=float(fact["total"].sum())
facturacion_prev=float(fact_prev["total"].sum())
margen_pct=(float(fact["margen"].sum()/fact["total"].sum()*100) if fact["total"].sum() else 0)
ticket=float(fact["total"].mean()) if len(fact) else 0
cerradas=df[df["estado"].isin(["facturada","finalizada"])]
cnt=cerradas.groupby("cliente_id").size()
rec_pct=(int((cnt>=2).sum())/len(cnt)*100) if len(cnt) else 0
delta_f=((facturacion/facturacion_prev-1)*100) if facturacion_prev else 0

c1,c2,c3,c4=st.columns(4)
c1.metric("Facturación del mes",fmt(facturacion),f"{delta_f:+.1f}% vs. mes anterior")
c2.metric("Margen estimado",f"{margen_pct:.0f}%")
c3.metric("Ticket promedio",fmt(ticket),f"{len(fact)} órdenes")
c4.metric("Clientes que repiten",f"{rec_pct:.0f}%")
st.write("")

# ═══════════════════════════════════════════════════════ GRÁFICOS
g1,g2=st.columns([1.3,1])
with g1:
    st.markdown("#### Facturación · últimos 6 meses")
    serie=(df[df["estado"]=="facturada"].groupby("mes")["total"].sum()
           .sort_index().tail(6).reset_index().rename(columns={"total":"facturacion"}))
    serie["Mes"]=serie["mes"].apply(lambda m:pd.Period(m,"M").strftime("%b %y"))
    st.altair_chart(alt.Chart(serie).mark_bar(size=34,cornerRadiusTopLeft=6,cornerRadiusTopRight=6,color=BLUE)
        .encode(x=alt.X("Mes:N",sort=None,axis=alt.Axis(labelAngle=0,title=None)),
                y=alt.Y("facturacion:Q",axis=alt.Axis(title=None,format="~s")),
                tooltip=["Mes:N",alt.Tooltip("facturacion:Q",title="Facturación",format=",.0f")])
        .properties(height=260),use_container_width=True)

with g2:
    st.markdown("#### Órdenes por técnico")
    pt=(df[df["estado"].isin(["facturada","finalizada"])&(df["mes"]==mes)]
        .groupby("tecnico").agg(ordenes=("id","count"),facturacion=("total","sum"))
        .reset_index().sort_values("ordenes",ascending=False))
    st.altair_chart(alt.Chart(pt).mark_bar(cornerRadiusEnd=6,color=AMBER)
        .encode(y=alt.Y("tecnico:N",sort="-x",axis=alt.Axis(title=None)),
                x=alt.X("ordenes:Q",axis=alt.Axis(title=None)),
                tooltip=["tecnico:N",alt.Tooltip("ordenes:Q",title="Órdenes"),
                         alt.Tooltip("facturacion:Q",title="Facturación",format=",.0f")])
        .properties(height=260),use_container_width=True)

g3,g4=st.columns([1,1.3])
with g3:
    st.markdown("#### Por tipo de servicio")
    pti=(df[(df["estado"]=="facturada")&(df["mes"]==mes)]
         .groupby("tipo_servicio")["total"].sum().reset_index()
         .sort_values("total",ascending=False))
    st.altair_chart(alt.Chart(pti).mark_bar(cornerRadiusEnd=6,color=GREEN)
        .encode(y=alt.Y("tipo_servicio:N",sort="-x",axis=alt.Axis(title=None)),
                x=alt.X("total:Q",axis=alt.Axis(title=None,format="~s")),
                tooltip=["tipo_servicio:N",alt.Tooltip("total:Q",title="Facturación",format=",.0f")])
        .properties(height=300),use_container_width=True)

with g4:
    st.markdown("#### Últimas órdenes")
    ult=(df.dropna(subset=["creado_en"]).sort_values("creado_en",ascending=False).head(12)
         [["cliente","zona","tipo_servicio","tecnico","estado","total"]].copy())
    badge={"facturada":"🟢 Facturada","finalizada":"🟠 Sin facturar",
           "en_curso":"🔵 En curso","agendada":"⚪ Agendada","cancelada":"⚫ Cancelada"}
    ult["estado"]=ult["estado"].map(badge)
    ult["total"]=ult["total"].apply(lambda x:fmt(x) if pd.notna(x) else "—")
    ult.columns=["Cliente","Zona","Servicio","Técnico","Estado","Monto"]
    st.dataframe(ult,hide_index=True,use_container_width=True,height=300)

st.caption("TécnicoFlow UY · dashboard del dueño · datos de ejemplo (Sanitaria El Águila)")
