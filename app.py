import os, sqlite3, csv, io
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, Response
from werkzeug.security import generate_password_hash, check_password_hash

app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY','solo-desarrollo-cambiar-esta-clave')
DB=os.getenv('DB_PATH','motogestion.sqlite3')

def conn():
    c=sqlite3.connect(DB,timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with conn() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, precio INTEGER NOT NULL CHECK(precio>=0), stock INTEGER NOT NULL CHECK(stock>=0), activo INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, documento TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, telefono TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, tipo TEXT NOT NULL CHECK(tipo IN ('CONTADO','CREDITO')), customer_id INTEGER REFERENCES customers(id), total INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES sales(id), product_id INTEGER NOT NULL REFERENCES products(id), cantidad INTEGER NOT NULL, precio INTEGER NOT NULL, subtotal INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS receivables(id INTEGER PRIMARY KEY, sale_id INTEGER UNIQUE REFERENCES sales(id), customer_id INTEGER REFERENCES customers(id), saldo_inicial INTEGER NOT NULL, saldo_actual INTEGER NOT NULL CHECK(saldo_actual>=0));
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, receivable_id INTEGER REFERENCES receivables(id), fecha TEXT NOT NULL, monto INTEGER NOT NULL CHECK(monto>0));''')
        if not c.execute('SELECT id FROM users LIMIT 1').fetchone():
            c.execute('INSERT INTO users(username,password_hash) VALUES(?,?)',(os.getenv('ADMIN_USER','admin'),generate_password_hash(os.getenv('ADMIN_PASSWORD','Moto2026!'))))
        # Datos exclusivamente ficticios, inicializados una sola vez por base de datos.
        # Nunca modifica los registros existentes ni restaura datos borrados por el usuario.
        c.execute("CREATE TABLE IF NOT EXISTS demo_seed_meta (id INTEGER PRIMARY KEY CHECK(id=1), seeded_at TEXT NOT NULL)")
        has_seed = c.execute('SELECT 1 FROM demo_seed_meta WHERE id=1').fetchone()
        if not has_seed:
            tables = ('products', 'customers', 'sales', 'sale_items', 'receivables', 'payments')
            is_empty = all(c.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone() is None for table in tables)
            if is_empty:
                catalog = [
                    ('LL-001', 'Llanta Michelin (DEMO)', 80000, 5),
                    ('FI-002', 'Filtro de aceite (DEMO)', 25000, 12),
                    ('BU-003', 'Bujía para moto (DEMO)', 18000, 20),
                ]
                product_ids = {}
                for code, name, price, stock in catalog:
                    product_ids[code] = c.execute(
                        'INSERT INTO products(codigo,nombre,precio,stock) VALUES (?,?,?,?)',
                        (code, name, price, stock)
                    ).lastrowid
                client_ids = []
                for document, name, phone, email in [
                    ('DEMO-001', 'Juan Pérez (DEMO)', '3000000001', 'juan.demo@example.com'),
                    ('DEMO-002', 'María Gómez (DEMO)', '3000000002', 'maria.demo@example.com'),
                ]:
                    client_ids.append(c.execute(
                        'INSERT INTO customers(documento,nombre,telefono,email) VALUES (?,?,?,?)',
                        (document, name, phone, email)
                    ).lastrowid)
                stamp = datetime.now().isoformat(timespec='seconds')
                # Venta a crédito: 2 llantas por 160.000; abono de 60.000; saldo 100.000.
                credit_sale = c.execute(
                    'INSERT INTO sales(fecha,tipo,customer_id,total) VALUES (?,?,?,?)',
                    (stamp, 'CREDITO', client_ids[0], 160000)
                ).lastrowid
                c.execute('INSERT INTO sale_items(sale_id,product_id,cantidad,precio,subtotal) VALUES (?,?,?,?,?)',
                          (credit_sale, product_ids['LL-001'], 2, 80000, 160000))
                c.execute('UPDATE products SET stock=stock-2 WHERE id=?', (product_ids['LL-001'],))
                account_id = c.execute(
                    'INSERT INTO receivables(sale_id,customer_id,saldo_inicial,saldo_actual) VALUES (?,?,?,?)',
                    (credit_sale, client_ids[0], 160000, 100000)
                ).lastrowid
                c.execute('INSERT INTO payments(receivable_id,fecha,monto) VALUES (?,?,?)',
                          (account_id, stamp, 60000))
                # Venta de contado: 1 filtro por 25.000.
                cash_sale = c.execute(
                    'INSERT INTO sales(fecha,tipo,customer_id,total) VALUES (?,?,?,?)',
                    (stamp, 'CONTADO', client_ids[1], 25000)
                ).lastrowid
                c.execute('INSERT INTO sale_items(sale_id,product_id,cantidad,precio,subtotal) VALUES (?,?,?,?,?)',
                          (cash_sale, product_ids['FI-002'], 1, 25000, 25000))
                c.execute('UPDATE products SET stock=stock-1 WHERE id=?', (product_ids['FI-002'],))
            c.execute('INSERT INTO demo_seed_meta(id,seeded_at) VALUES (1,?)',
                      (datetime.now().isoformat(timespec='seconds'),))
init_db()

def login_required(fn):
    @wraps(fn)
    def inner(*args,**kwargs):
        if not session.get('username'): return redirect(url_for('login'))
        return fn(*args,**kwargs)
    return inner

BASE='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MotoGestión | {{title}}</title><style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#183044;background:#f2f6fa}*{box-sizing:border-box}body{margin:0}header{background:#0b2239;color:white;padding:18px 5%;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}header strong{font-size:22px}nav{display:flex;gap:7px;flex-wrap:wrap}nav a{color:#dce8f3;text-decoration:none;padding:8px 11px;border-radius:7px}nav a:hover{background:#214362}main{max-width:1150px;margin:28px auto;padding:0 20px}h1{margin:0 0 7px}p.lead{color:#526679;margin:0 0 24px}.box{background:#fff;border:1px solid #dce5ee;border-radius:13px;padding:22px;margin-bottom:20px;box-shadow:0 2px 8px #172d3b09}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px}.metric{font-size:29px;font-weight:750;color:#087e81}table{width:100%;border-collapse:collapse;display:block;overflow-x:auto}th,td{padding:11px 13px;border-bottom:1px solid #e3eaf0;text-align:left;white-space:nowrap}th{background:#eef4f7}form{display:flex;gap:12px;flex-wrap:wrap;align-items:end}label{display:flex;flex-direction:column;gap:5px;font-weight:600;font-size:14px}input,select{padding:10px;border:1px solid #bccbd5;border-radius:7px;background:white;min-width:120px}button,.btn{padding:10px 14px;border:0;background:#087e81;color:white;font-weight:650;border-radius:7px;cursor:pointer;text-decoration:none;display:inline-block}.btn.secondary{background:#35546c}.danger{background:#9e3246}.notice{background:#e1f4ed;border-left:4px solid #2a9067;padding:12px;margin-bottom:15px}.error{background:#ffe5e5;border-left:4px solid #cb3f45;padding:12px;margin-bottom:15px}.muted{color:#6e7d8a;font-size:13px}footer{padding:25px;text-align:center;color:#789} @media(max-width:680px){header{padding:16px}main{padding:0 12px}input{max-width:100%}}
</style></head><body><header><strong>🏍 MotoGestión</strong>{% if session.get('username') %}<nav><a href="{{url_for('dashboard')}}">Inicio</a><a href="{{url_for('products')}}">Productos</a><a href="{{url_for('customers')}}">Clientes</a><a href="{{url_for('sales')}}">Ventas</a><a href="{{url_for('receivables')}}">CxC / Abonos</a><a href="{{url_for('reports')}}">Informes</a><a href="{{url_for('logout')}}">Salir</a></nav>{% endif %}</header><main><h1>{{title}}</h1><p class="lead">{{subtitle}}</p>{% with messages=get_flashed_messages(with_categories=true) %}{% for category,msg in messages %}<div class="{{'error' if category=='error' else 'notice'}}">{{msg}}</div>{% endfor %}{% endwith %}{{content|safe}}</main><footer>Proyecto académico • MotoGestión • COP</footer></body></html>'''

def page(title,subtitle,body,**data):
    return render_template_string(BASE,title=title,subtitle=subtitle,content=render_template_string(body,**data))

def positive_int(value,name,allow_zero=False):
    try: n=int(value)
    except (ValueError,TypeError): raise ValueError(f'{name} debe ser un número entero.')
    if n<0 or (n==0 and not allow_zero): raise ValueError(f'{name} debe ser positivo.')
    return n

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        with conn() as c: u=c.execute('SELECT * FROM users WHERE username=?',(request.form.get('username',''),)).fetchone()
        if u and check_password_hash(u['password_hash'],request.form.get('password','')):
            session.clear();session['username']=u['username'];return redirect(url_for('dashboard'))
        flash('Credenciales incorrectas','error')
    return page('Acceso al sistema','Ingresa con las credenciales de demostración o las asignadas por el administrador.','''<section class="box"><form method="post"><label>Usuario<input name="username" required autocomplete="username"></label><label>Contraseña<input name="password" type="password" required autocomplete="current-password"></label><button>Iniciar sesión</button></form></section>''')

@app.route('/logout')
def logout(): session.clear();return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    with conn() as c:
        items=c.execute('SELECT COUNT(*) n,COALESCE(SUM(stock),0) stock,COALESCE(SUM(stock*precio),0) valor FROM products WHERE activo=1').fetchone()
        sales=c.execute('SELECT COUNT(*) n,COALESCE(SUM(total),0) total FROM sales').fetchone()
        debt=c.execute('SELECT COALESCE(SUM(saldo_actual),0) total FROM receivables').fetchone()['total']
        customer_count=c.execute('SELECT COUNT(*) n FROM customers').fetchone()['n']
    return page('Panel de control','Resumen general del negocio de repuestos y accesorios para motocicletas.','''<div class="grid"><div class="box">Productos activos<div class="metric">{{items.n}}</div><span class="muted">Unidades en existencia: {{items.stock}}</span></div><div class="box">Ventas registradas<div class="metric">{{sales.n}}</div><span class="muted">Valor total: $ {{"{:,.0f}".format(sales.total)}}</span></div><div class="box">Saldo por cobrar<div class="metric">$ {{"{:,.0f}".format(debt)}}</div></div><div class="box">Clientes registrados<div class="metric">{{customer_count}}</div></div><section class="box"><h2>Operaciones rápidas</h2><a class="btn" href="{{url_for('sales')}}">Registrar venta</a> <a class="btn secondary" href="{{url_for('products')}}">Gestionar inventario</a> <a class="btn secondary" href="{{url_for('receivables')}}">Registrar abono</a></section>''',items=items,sales=sales,debt=debt,customer_count=customer_count)

@app.route('/products',methods=['GET','POST'])
@login_required
def products():
    if request.method=='POST':
        try:
            code=request.form.get('codigo','').strip();name=request.form.get('nombre','').strip()
            if not code or not name:raise ValueError('Código y nombre son obligatorios.')
            price=positive_int(request.form.get('precio'),'Precio',True);stock=positive_int(request.form.get('stock'),'Stock',True)
            with conn() as c: c.execute('INSERT INTO products(codigo,nombre,precio,stock) VALUES (?,?,?,?)',(code,name,price,stock))
            flash('Producto registrado correctamente.','ok')
        except (ValueError,sqlite3.IntegrityError) as e:flash(f'No se pudo registrar: {e}','error')
        return redirect(url_for('products'))
    with conn() as c:rows=c.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    return page('Productos e inventario','Registra, edita y consulta productos. No se permiten existencias negativas.','''<section class="box"><h2>Nuevo producto</h2><form method="post"><label>Código<input name="codigo" required></label><label>Nombre<input name="nombre" required></label><label>Precio (COP)<input name="precio" type="number" min="0" required></label><label>Stock inicial<input name="stock" type="number" min="0" required></label><button>Agregar</button></form></section><section class="box"><h2>Listado</h2><table><tr><th>Código</th><th>Nombre</th><th>Precio</th><th>Stock</th><th>Estado</th><th>Acciones</th></tr>{% for r in rows %}<tr><td>{{r.codigo}}</td><td>{{r.nombre}}</td><td>$ {{"{:,.0f}".format(r.precio)}}</td><td>{{r.stock}}</td><td>{{'Activo' if r.activo else 'Inactivo'}}</td><td><a class="btn secondary" href="{{url_for('edit_product',pid=r.id)}}">Editar</a></td></tr>{% endfor %}</table></section>''',rows=rows)

@app.route('/products/<int:pid>',methods=['GET','POST'])
@login_required
def edit_product(pid):
    with conn() as c:p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if not p:return 'Producto no encontrado',404
    if request.method=='POST':
        try:
            with conn() as c:c.execute('UPDATE products SET nombre=?,precio=?,stock=?,activo=? WHERE id=?',(request.form['nombre'].strip(),positive_int(request.form['precio'],'Precio',True),positive_int(request.form['stock'],'Stock',True),1 if request.form.get('activo')=='1' else 0,pid))
            flash('Producto actualizado.','ok');return redirect(url_for('products'))
        except ValueError as e:flash(str(e),'error')
    return page('Editar producto',p['codigo'],'''<section class="box"><form method="post"><label>Nombre<input name="nombre" value="{{p.nombre}}" required></label><label>Precio<input name="precio" type="number" min="0" value="{{p.precio}}" required></label><label>Stock<input name="stock" type="number" min="0" value="{{p.stock}}" required></label><label>Estado<select name="activo"><option value="1" {{'selected' if p.activo else ''}}>Activo</option><option value="0" {{'selected' if not p.activo else ''}}>Inactivo</option></select></label><button>Guardar cambios</button></form></section>''',p=p)

@app.route('/customers',methods=['GET','POST'])
@login_required
def customers():
    if request.method=='POST':
        try:
            doc=request.form.get('documento','').strip();name=request.form.get('nombre','').strip()
            if not doc or not name:raise ValueError('Documento y nombre son obligatorios.')
            with conn() as c:c.execute('INSERT INTO customers(documento,nombre,telefono,email) VALUES (?,?,?,?)',(doc,name,request.form.get('telefono','').strip(),request.form.get('email','').strip()))
            flash('Cliente registrado.','ok')
        except (ValueError,sqlite3.IntegrityError) as e:flash(f'No se pudo registrar: {e}','error')
        return redirect(url_for('customers'))
    with conn() as c:rows=c.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
    return page('Clientes','Directorio e información de contacto de clientes.','''<section class="box"><h2>Nuevo cliente</h2><form method="post"><label>Documento<input name="documento" required></label><label>Nombre<input name="nombre" required></label><label>Teléfono<input name="telefono"></label><label>Correo<input name="email" type="email"></label><button>Agregar</button></form></section><section class="box"><table><tr><th>Documento</th><th>Nombre</th><th>Teléfono</th><th>Email</th><th>Acciones</th></tr>{% for r in rows %}<tr><td>{{r.documento}}</td><td>{{r.nombre}}</td><td>{{r.telefono}}</td><td>{{r.email}}</td><td><a class="btn secondary" href="{{url_for('edit_customer',cid=r.id)}}">Editar</a></td></tr>{% endfor %}</table></section>''',rows=rows)

@app.route('/customers/<int:cid>',methods=['GET','POST'])
@login_required
def edit_customer(cid):
    with conn() as c:p=c.execute('SELECT * FROM customers WHERE id=?',(cid,)).fetchone()
    if not p:return 'Cliente no encontrado',404
    if request.method=='POST':
        try:
            if not request.form.get('nombre','').strip():raise ValueError('El nombre es obligatorio.')
            with conn() as c:c.execute('UPDATE customers SET nombre=?,telefono=?,email=? WHERE id=?',(request.form['nombre'].strip(),request.form.get('telefono','').strip(),request.form.get('email','').strip(),cid))
            flash('Cliente actualizado.','ok');return redirect(url_for('customers'))
        except ValueError as e:flash(str(e),'error')
    return page('Editar cliente',p['documento'],'''<section class="box"><form method="post"><label>Nombre<input name="nombre" required value="{{p.nombre}}"></label><label>Teléfono<input name="telefono" value="{{p.telefono}}"></label><label>Correo<input name="email" value="{{p.email}}"></label><button>Guardar</button></form></section>''',p=p)

@app.route('/sales',methods=['GET','POST'])
@login_required
def sales():
    if request.method=='POST':
        try:
            pid=positive_int(request.form.get('product_id'),'Producto');qty=positive_int(request.form.get('cantidad'),'Cantidad');tipo=request.form.get('tipo');cid=request.form.get('customer_id') or None
            if tipo not in ('CONTADO','CREDITO'):raise ValueError('Tipo de venta inválido.')
            if tipo=='CREDITO' and not cid:raise ValueError('Una venta a crédito requiere cliente.')
            with conn() as c:
                c.execute('BEGIN IMMEDIATE')
                p=c.execute('SELECT * FROM products WHERE id=? AND activo=1',(pid,)).fetchone()
                if not p:raise ValueError('Producto inexistente o inactivo.')
                if p['stock']<qty:raise ValueError(f'Stock insuficiente. Disponibles: {p["stock"]}.')
                if cid and not c.execute('SELECT 1 FROM customers WHERE id=?',(cid,)).fetchone():raise ValueError('Cliente no encontrado.')
                total=p['precio']*qty
                sale=c.execute('INSERT INTO sales(fecha,tipo,customer_id,total) VALUES (?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),tipo,cid,total)).lastrowid
                c.execute('INSERT INTO sale_items(sale_id,product_id,cantidad,precio,subtotal) VALUES (?,?,?,?,?)',(sale,pid,qty,p['precio'],total))
                c.execute('UPDATE products SET stock=stock-? WHERE id=?',(qty,pid))
                if tipo=='CREDITO':c.execute('INSERT INTO receivables(sale_id,customer_id,saldo_inicial,saldo_actual) VALUES (?,?,?,?)',(sale,cid,total,total))
            flash(f'Venta #{sale} registrada. Total: $ {total:,} COP.','ok')
        except (ValueError,sqlite3.Error) as e:flash(f'No se registró la venta: {e}','error')
        return redirect(url_for('sales'))
    with conn() as c:
        products=c.execute('SELECT * FROM products WHERE activo=1 ORDER BY nombre').fetchall();customers=c.execute('SELECT * FROM customers ORDER BY nombre').fetchall()
        rows=c.execute('SELECT s.*,c.nombre cliente FROM sales s LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id DESC LIMIT 60').fetchall()
    return page('Ventas','Registra ventas de contado o a crédito y descuenta existencias automáticamente.','''<section class="box"><h2>Nueva venta</h2><form method="post"><label>Producto<select name="product_id" required>{% for p in products %}<option value="{{p.id}}">{{p.nombre}} — $ {{p.precio}} (stock {{p.stock}})</option>{% endfor %}</select></label><label>Cantidad<input name="cantidad" type="number" min="1" value="1" required></label><label>Tipo<select name="tipo"><option value="CONTADO">Contado</option><option value="CREDITO">Crédito</option></select></label><label>Cliente (obligatorio para crédito)<select name="customer_id"><option value="">Sin cliente</option>{% for c in customers %}<option value="{{c.id}}">{{c.nombre}} ({{c.documento}})</option>{% endfor %}</select></label><button>Confirmar venta</button></form><p class="muted">Cada registro contempla un producto por venta; puedes hacer registros adicionales para otros productos.</p></section><section class="box"><h2>Historial</h2><table><tr><th>#</th><th>Fecha</th><th>Tipo</th><th>Cliente</th><th>Total COP</th></tr>{% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.fecha[:16]}}</td><td>{{r.tipo}}</td><td>{{r.cliente or 'Consumidor final'}}</td><td>$ {{"{:,.0f}".format(r.total)}}</td></tr>{% endfor %}</table></section>''',products=products,customers=customers,rows=rows)

@app.route('/receivables',methods=['GET','POST'])
@login_required
def receivables():
    if request.method=='POST':
        try:
            rid=positive_int(request.form.get('receivable_id'),'Cuenta');amount=positive_int(request.form.get('monto'),'Monto')
            with conn() as c:
                c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM receivables WHERE id=?',(rid,)).fetchone()
                if not r:raise ValueError('Cuenta no encontrada.')
                if amount>r['saldo_actual']:raise ValueError('El abono supera el saldo pendiente.')
                c.execute('INSERT INTO payments(receivable_id,fecha,monto) VALUES (?,?,?)',(rid,datetime.now().isoformat(timespec='seconds'),amount))
                c.execute('UPDATE receivables SET saldo_actual=saldo_actual-? WHERE id=?',(amount,rid))
            flash('Abono aplicado correctamente.','ok')
        except (ValueError,sqlite3.Error) as e:flash(f'No se pudo registrar el abono: {e}','error')
        return redirect(url_for('receivables'))
    with conn() as c:
        rows=c.execute('SELECT r.*,c.nombre cliente FROM receivables r JOIN customers c ON c.id=r.customer_id ORDER BY r.id DESC').fetchall()
        pays=c.execute('SELECT p.*,c.nombre cliente FROM payments p JOIN receivables r ON r.id=p.receivable_id JOIN customers c ON c.id=r.customer_id ORDER BY p.id DESC LIMIT 40').fetchall()
    return page('Cuentas por cobrar y abonos','Consulta saldos; registra abonos que no superen la deuda.','''<section class="box"><h2>Registrar abono</h2><form method="post"><label>Cuenta pendiente<select name="receivable_id" required>{% for r in rows if r.saldo_actual>0 %}<option value="{{r.id}}">Cuenta #{{r.id}} • {{r.cliente}} • $ {{r.saldo_actual}}</option>{% endfor %}</select></label><label>Monto COP<input type="number" name="monto" min="1" required></label><button>Aplicar abono</button></form></section><section class="box"><h2>Estado de cuentas</h2><table><tr><th>Cuenta</th><th>Cliente</th><th>Venta</th><th>Saldo inicial</th><th>Saldo actual</th><th>Estado</th></tr>{% for r in rows %}<tr><td>#{{r.id}}</td><td>{{r.cliente}}</td><td>#{{r.sale_id}}</td><td>$ {{r.saldo_inicial}}</td><td>$ {{r.saldo_actual}}</td><td>{{'PAGADA' if r.saldo_actual==0 else 'PENDIENTE'}}</td></tr>{% endfor %}</table></section><section class="box"><h2>Historial de abonos</h2><table><tr><th>Fecha</th><th>Cliente</th><th>Cuenta</th><th>Monto</th></tr>{% for p in pays %}<tr><td>{{p.fecha[:16]}}</td><td>{{p.cliente}}</td><td>#{{p.receivable_id}}</td><td>$ {{p.monto}}</td></tr>{% endfor %}</table></section>''',rows=rows,pays=pays)

@app.route('/reports')
@login_required
def reports():
    start=request.args.get('desde',date.today().replace(day=1).isoformat());end=request.args.get('hasta',date.today().isoformat())
    with conn() as c:
        rows=c.execute('SELECT s.*,c.nombre cliente FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE DATE(s.fecha) BETWEEN ? AND ? ORDER BY s.id DESC',(start,end)).fetchall()
        inv=c.execute('SELECT *,precio*stock valor FROM products WHERE activo=1 ORDER BY nombre').fetchall()
        debts=c.execute('SELECT c.nombre,SUM(r.saldo_actual) saldo FROM receivables r JOIN customers c ON c.id=r.customer_id WHERE r.saldo_actual>0 GROUP BY c.id ORDER BY saldo DESC').fetchall()
    return page('Informes operativos','Reporte de ventas por fechas, inventario valorizado y deudas pendientes.','''<section class="box"><h2>Ventas por fecha</h2><form method="get"><label>Desde<input type="date" name="desde" value="{{start}}" required></label><label>Hasta<input type="date" name="hasta" value="{{end}}" required></label><button>Filtrar</button></form><p><b>Total del período:</b> $ {{"{:,.0f}".format(rows|sum(attribute='total'))}} COP</p><table><tr><th>#</th><th>Fecha</th><th>Tipo</th><th>Cliente</th><th>Total</th></tr>{% for r in rows %}<tr><td>{{r.id}}</td><td>{{r.fecha[:10]}}</td><td>{{r.tipo}}</td><td>{{r.cliente or 'Consumidor final'}}</td><td>$ {{r.total}}</td></tr>{% endfor %}</table></section><section class="box"><h2>Inventario valorizado</h2><p><b>Valor en existencias: $ {{"{:,.0f}".format(inv|sum(attribute='valor'))}} COP</b></p><table><tr><th>Código</th><th>Producto</th><th>Unidades</th><th>Valor COP</th></tr>{% for p in inv %}<tr><td>{{p.codigo}}</td><td>{{p.nombre}}</td><td>{{p.stock}}</td><td>{{p.valor}}</td></tr>{% endfor %}</table></section><section class="box"><h2>Deudas pendientes</h2><table><tr><th>Cliente</th><th>Saldo COP</th></tr>{% for d in debts %}<tr><td>{{d.nombre}}</td><td>$ {{d.saldo}}</td></tr>{% endfor %}</table></section>''',start=start,end=end,rows=rows,inv=inv,debts=debts)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=os.getenv('FLASK_DEBUG')=='1')
