"""
seed_data.py — Genera la base de datos de ejemplo de TécnicoFlow UY.

Crea 'tecnicoflow.db' (SQLite) con el esquema relacional del diseño
(empresas, usuarios, clientes, direcciones, materiales, ordenes_servicio,
os_materiales) y la llena con 6 meses completos de operación realista de una
sanitaria de Montevideo. El "mes actual" del dashboard = último mes cerrado.

Uso:  python seed_data.py
"""
import sqlite3, random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

random.seed(42)
DB = "tecnicoflow.db"

SCHEMA = """
DROP TABLE IF EXISTS os_materiales;
DROP TABLE IF EXISTS ordenes_servicio;
DROP TABLE IF EXISTS materiales;
DROP TABLE IF EXISTS direcciones;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS empresas;
CREATE TABLE empresas(id INTEGER PRIMARY KEY, razon_social TEXT, nombre_fantasia TEXT, rut TEXT, rubro TEXT, plan TEXT);
CREATE TABLE usuarios(id INTEGER PRIMARY KEY, empresa_id INTEGER, nombre TEXT, rol TEXT, telefono TEXT, activo INTEGER);
CREATE TABLE clientes(id INTEGER PRIMARY KEY, empresa_id INTEGER, nombre TEXT, tipo_doc TEXT, documento TEXT, telefono TEXT, email TEXT);
CREATE TABLE direcciones(id INTEGER PRIMARY KEY, cliente_id INTEGER, calle TEXT, numero TEXT, zona TEXT, departamento TEXT);
CREATE TABLE materiales(id INTEGER PRIMARY KEY, empresa_id INTEGER, nombre TEXT, unidad TEXT, costo REAL, precio REAL);
CREATE TABLE ordenes_servicio(id INTEGER PRIMARY KEY, empresa_id INTEGER, cliente_id INTEGER, direccion_id INTEGER, tecnico_id INTEGER, tipo_servicio TEXT, estado TEXT, prioridad TEXT, agendada_para TEXT, iniciada_en TEXT, finalizada_en TEXT, descripcion TEXT, mano_obra REAL, total REAL, facturada INTEGER, creado_en TEXT);
CREATE TABLE os_materiales(id INTEGER PRIMARY KEY, os_id INTEGER, material_id INTEGER, cantidad REAL, precio_unit REAL, costo_unit REAL);
"""

TECNICOS = [("Richard", 0.45), ("Marcelo", 0.34), ("Diego", 0.21)]
ZONAS = ["Pocitos","Cordón","Malvín","Buceo","Carrasco","La Blanqueada","Centro",
         "Punta Carretas","Cerro","Sayago","Prado","Parque Rodó"]
ZONAS_INT = [("Las Piedras","Canelones"),("Pando","Canelones"),("Maldonado","Maldonado")]
TIPOS = [("Reparación de canilla",1200,1),("Destape de cámara",2400,1),
    ("Cambio de flexible",1100,2),("Revisión de cañería",1600,1),
    ("Instalación de calefón",4800,3),("Reparación de pérdida",1900,2),
    ("Instalación de sanitarios",6500,3),("Mantenimiento preventivo",2200,2)]
TIPOS_GRANDES = {"Instalación de calefón","Instalación de sanitarios","Destape de cámara"}
MATERIALES = [("Flexible 1/2\"","unidad",230,420),("Teflón","unidad",35,60),
    ("Llave de paso","unidad",210,380),("Caño PVC 40mm","metro",90,165),
    ("Codo PVC","unidad",25,55),("Sellador silicona","unidad",140,250),
    ("Sifón","unidad",180,340),("Membrana de inodoro","unidad",95,180),
    ("Cuerito / junta","unidad",12,35),("Mezcladora","unidad",1200,2100)]

NOMBRES_M = ["Juan","Diego","Martín","Sebastián","Gabriel","Federico","Andrés","Rodrigo",
    "Gonzalo","Pablo","Nicolás","Matías","Santiago","Joaquín","Bruno","Agustín","Mauricio","Leandro"]
NOMBRES_F = ["María","Laura","Andrea","Valeria","Mónica","Lucía","Sofía","Camila","Patricia",
    "Beatriz","Rosa","Elena","Carolina","Florencia","Natalia","Verónica","Daniela","Romina"]
APELLIDOS = ["Rodríguez","Fernández","González","Pérez","Sosa","Méndez","Píriz","Castro",
    "Bentancor","Núñez","Ferreira","Olivera","Techera","Bermúdez","Vázquez","Cabrera",
    "Suárez","Lemos","Olmos","Quintana","Acosta","Cardozo","Rivero","Silveira","Da Silva"]
EMPRESAS_CLI = ["Edificio Las Acacias","Consorcio Río Branco","Club La Blanqueada",
    "Inmobiliaria Sur","Estudio Jurídico Lema","Colegio San Pablo","Ferretería El Tornillo",
    "Gimnasio FitClub","Restó La Pasiva","Bar El Ancla","Panadería La Espiga","Edicampo SRL",
    "Edificio Torre del Puerto","Consorcio Pocitos Plaza","Hotel Mirador","Cooperativa COVISA",
    "Administración Delfino","Edificio Brisas","Farmacia San Roque","Clínica Dental Sonrisas",
    "Lavadero El Sol","Edificio Aurora","Inmobiliaria Costa","Café Brasilero",
    "Residencial Los Pinos","Edificio Mar y Sol","Consorcio Buceo","Pizzería Nápoli",
    "Almacén Doña Pepa","Hostal del Centro"]

CALLES = ["Av. Rivera","Av. Italia","18 de Julio","Bvar. Artigas","Av. Brasil","Comercio","Propios","Av. 8 de Octubre"]


def main():
    con = sqlite3.connect(DB); cur = con.cursor(); cur.executescript(SCHEMA)
    cur.execute("INSERT INTO empresas VALUES(?,?,?,?,?,?)",
                (1,"El Águila Servicios SRL","Sanitaria El Águila","21 555 1234 0012","sanitaria","pro"))
    cur.execute("INSERT INTO usuarios VALUES(?,?,?,?,?,?)",
                (1,1,"Fernando Aguirre","dueno","+59899100200",1))
    tec_ids=[]
    for i,(nom,_) in enumerate(TECNICOS,start=2):
        cur.execute("INSERT INTO usuarios VALUES(?,?,?,?,?,?)",(i,1,nom,"tecnico",f"+5989910{i:04d}",1))
        tec_ids.append(i)
    tec_w=[w for _,w in TECNICOS]
    for i,(nom,uni,c,p) in enumerate(MATERIALES,start=1):
        cur.execute("INSERT INTO materiales VALUES(?,?,?,?,?,?)",(i,1,nom,uni,c,p))

    # ---- clientes: 30 empresas (recurrentes), 90 individuos recurrentes, 140 ocasionales
    clientes=[]   # (id, n_orders objetivo)
    cid=0
    for nombre in EMPRESAS_CLI:
        cid+=1; clientes.append((cid, random.randint(5,11)))
        _ins_cliente(cur,cid,nombre,True)
    for _ in range(90):
        cid+=1; clientes.append((cid, random.randint(2,5)))
        _ins_cliente(cur,cid,_persona(),False)
    for _ in range(140):
        cid+=1; clientes.append((cid, 1))
        _ins_cliente(cur,cid,_persona(),False)

    recurrentes_reales = sum(1 for _,n in clientes if n>=2)
    # flat list de cliente_ids según objetivo
    order_clients=[]
    for c,n in clientes: order_clients += [c]*n
    random.shuffle(order_clients)

    # ---- ventana: 6 meses completos terminando en el último mes cerrado
    primer_mes_actual = datetime.now().replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    fin = primer_mes_actual - timedelta(days=1)              # último día del último mes cerrado
    ult_mes = primer_mes_actual - relativedelta(months=1)
    meses=[ult_mes - relativedelta(months=k) for k in range(5,-1,-1)]
    mes_w=[0.80,0.88,0.95,1.04,1.20,1.48]                    # leve crecimiento
    reciente = fin - timedelta(days=35)

    # asignar fecha a cada orden
    ordenes=[]
    for cl in order_clients:
        m=random.choices(meses,weights=mes_w)[0]
        d=m.replace(day=random.randint(1,28),hour=random.randint(8,17),minute=random.choice([0,30]))
        tipo=random.choice(TIPOS)
        ordenes.append({"cli":cl,"fecha":d,"tipo":tipo,
                        "tec":random.choices(tec_ids,weights=tec_w)[0],
                        "mo":round(tipo[1]*random.uniform(.85,1.25),-1),
                        "estado":"facturada"})
    ordenes.sort(key=lambda o:o["fecha"])

    # canceladas dispersas (~3%)
    for o in random.sample(ordenes,k=int(len(ordenes)*0.03)): o["estado"]="cancelada"

    # ventana reciente -> fuga de cobros + algunas en curso/agendadas
    recientes=[o for o in ordenes if o["fecha"]>=reciente and o["estado"]=="facturada"]
    recientes.sort(key=lambda o:o["fecha"])
    for o in recientes[-6:]:                                  # últimas: aún abiertas
        o["estado"]=random.choice(["en_curso","agendada"])
    candidatas=[o for o in recientes[:-6] if o["tipo"][0] in TIPOS_GRANDES] or recientes[:-6]
    candidatas.sort(key=lambda o:o["mo"],reverse=True)
    for o in candidatas[:8]:                                  # terminadas SIN facturar (leakage)
        o["estado"]="finalizada"

    # persistir
    osid=0; osmid=0
    for o in ordenes:
        osid+=1
        cerrada=o["estado"] in ("facturada","finalizada")
        tipo_nom,_,_=o["tipo"]
        mats=random.sample(range(1,len(MATERIALES)+1),k=min(o["tipo"][2]+random.randint(0,1),len(MATERIALES)))
        mat_precio=0.0
        for mid in mats:
            osmid+=1; _,_,costo,precio=MATERIALES[mid-1]; cant=random.choice([1,1,1,2,3])
            mat_precio+=precio*cant
            cur.execute("INSERT INTO os_materiales VALUES(?,?,?,?,?,?)",(osmid,osid,mid,cant,precio,costo))
        total=round(o["mo"]+mat_precio,-1)
        ini=o["fecha"]; finh=ini+timedelta(hours=random.choice([1,1,2,3]))
        cur.execute("INSERT INTO ordenes_servicio VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (osid,1,o["cli"],o["cli"],o["tec"],tipo_nom,o["estado"],
             random.choice(["normal","normal","alta"]),ini.isoformat(),
             ini.isoformat() if o["estado"]!="agendada" else None,
             finh.isoformat() if cerrada else None,tipo_nom,o["mo"],
             total if cerrada else None,1 if o["estado"]=="facturada" else 0,ini.isoformat()))
    con.commit()
    n=cur.execute("SELECT COUNT(*) FROM ordenes_servicio").fetchone()[0]
    con.close()
    print(f"Base creada: {DB} · {n} órdenes · {len(clientes)} clientes · {recurrentes_reales} recurrentes")


def _persona():
    n=random.choice(NOMBRES_M+NOMBRES_F)
    return f"{n} {random.choice(APELLIDOS)}"

def _ins_cliente(cur,cid,nombre,es_empresa):
    tipo_doc="RUT" if es_empresa else "CI"
    doc=(f"21{random.randint(100000,999999)}001{random.randint(0,9)}" if es_empresa
         else f"{random.randint(1,5)}.{random.randint(100,999)}.{random.randint(100,999)}-{random.randint(0,9)}")
    cur.execute("INSERT INTO clientes VALUES(?,?,?,?,?,?,?)",
                (cid,1,nombre,tipo_doc,doc,f"+5989{random.randint(1000000,9999999)}",f"cli{cid}@mail.com"))
    if random.random()<0.82: zona,depto=random.choice(ZONAS),"Montevideo"
    else: zona,depto=random.choice(ZONAS_INT)
    cur.execute("INSERT INTO direcciones VALUES(?,?,?,?,?,?)",
                (cid,cid,random.choice(CALLES),str(random.randint(800,6500)),zona,depto))


if __name__=="__main__":
    main()
