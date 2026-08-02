-- ==========================================
-- 1. TABLA DE USUARIOS
-- ==========================================
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL, 
    correo TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL, -- Aquí se guardará el hash
    rol TEXT DEFAULT 'Vendedor' -- 'Super admin' o 'Vendedor'
);

-- ==========================================
-- 2. TABLA DE CLIENTES
-- ==========================================
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente TEXT PRIMARY KEY, -- Formato: C0119, C0120...
    nombre_completo TEXT NOT NULL,
    rfc TEXT,
    direccion TEXT,
    colonia TEXT,
    poblacion TEXT,
    cp TEXT,
    telefono TEXT,
    correo TEXT,
    cfdi TEXT,
    regimen TEXT,
    contacto TEXT
);

-- ==========================================
-- 3. TABLA DE PROVEEDORES
-- ==========================================
CREATE TABLE IF NOT EXISTS proveedores (
    id_prov TEXT PRIMARY KEY, -- Formato: PE01, PE02...
    nombre_empresa TEXT NOT NULL,
    vendedor_contacto TEXT,
    num_telefono TEXT,
    correo TEXT,
    direccion TEXT,
    tel_tienda_fisica TEXT
);

-- ==========================================
-- 4. TABLA DE INVENTARIO
-- ==========================================
CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_producto TEXT UNIQUE NOT NULL, -- Ej: 20226, 695596
    descripcion TEXT NOT NULL,
    stock REAL DEFAULT 0,
    um TEXT NOT NULL, -- Unidad de Medida (Ej: m, pza, rollo)
    proveedor_id TEXT, -- Referencia al proveedor
    marca TEXT,
    precio_compra REAL DEFAULT 0.0,
    precio_venta REAL DEFAULT 0.0,
    clave_sat_producto TEXT, -- Clave SAT c_ClaveProdServ (Ej: 26121600)
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id_prov)
);

-- ==========================================
-- 5. TABLAS DE COTIZACIÓN (Encabezado y Detalle)
-- ==========================================
-- 5.1 Encabezado de la Cotización
CREATE TABLE IF NOT EXISTS cotizaciones (
    id_cotizacion INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT UNIQUE NOT NULL, -- Formato: F-00123
    fecha TEXT NOT NULL,
    cliente_id TEXT NOT NULL,
    vendedor TEXT NOT NULL,
    oc TEXT, -- Orden de Compra
    obra TEXT,
    estado TEXT DEFAULT 'Pendiente', -- Puede ser: Pendiente, Aceptada, Rechazada
    monto_total REAL DEFAULT 0.0,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id_cliente)
);

-- 5.2 Detalle de Productos por Cotización
CREATE TABLE IF NOT EXISTS cotizaciones_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotizacion_id INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    cantidad REAL NOT NULL,
    um TEXT NOT NULL,
    precio_unitario REAL NOT NULL,
    monto REAL NOT NULL,
    disponibilidad TEXT DEFAULT 'Disponible', -- 'Disponible' o 'Sobrepedido'
    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id_cotizacion),
    FOREIGN KEY (codigo_producto) REFERENCES inventario(codigo_producto)
);

-- ==========================================
-- 6. TABLA DE DATOS FISCALES (Estática)
-- ==========================================
CREATE TABLE IF NOT EXISTS datos_fiscales (
    id INTEGER PRIMARY KEY CHECK (id = 1), 
    nombre_empresa TEXT DEFAULT 'PRO ELECTRO MONTERREY',
    telefono TEXT DEFAULT '(81) 1634 7681',
    ubicacion TEXT DEFAULT 'Monterrey, Nuevo León',
    rfc TEXT,
    representante_legal TEXT DEFAULT 'EDWIN GUERRERO GARCÍA',
    terminos_condiciones TEXT,
    facturacion_todos_usuarios INTEGER DEFAULT 0, -- 0=solo Super admin, 1=todos pueden facturar
    regimen_fiscal TEXT, -- Clave SAT del régimen fiscal del emisor (Ej: 601)
    cp_fiscal TEXT -- Código postal fiscal del emisor (Ej: 64560)
);

-- ==========================================
-- 7. TABLA DE COLA DE SINCRONIZACIÓN (Task Scheduler)
-- ==========================================
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla_afectada TEXT NOT NULL, -- Ej: 'clientes', 'inventario'
    operacion TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
    registro_id TEXT NOT NULL, -- El ID del registro modificado (Ej: 'C0119')
    datos_json TEXT, -- Toda la fila convertida a JSON para mandar al Cloudflare Worker
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 8. TABLAS DE COTIZACIÓN EXTERNA (OFFLINE)
-- ==========================================
-- 8.1 Encabezado Offline
CREATE TABLE IF NOT EXISTS cotizaciones_ext (
    id_cotizacion INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT UNIQUE NOT NULL, -- Formato: CTE-00123
    fecha TEXT NOT NULL,
    cliente_id TEXT NOT NULL,
    vendedor TEXT NOT NULL,
    oc TEXT,
    obra TEXT,
    estado TEXT DEFAULT 'Pendiente',
    monto_total REAL DEFAULT 0.0
);

-- 8.2 Detalle Offline
CREATE TABLE IF NOT EXISTS cotizaciones_detalle_ext (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotizacion_id INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    cantidad REAL NOT NULL,
    um TEXT NOT NULL,
    precio_unitario REAL NOT NULL,
    monto REAL NOT NULL,
    disponibilidad TEXT DEFAULT 'Disponible',
    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones_ext(id_cotizacion)
);

-- ==========================================
-- 9. CATÁLOGO DE UNIDADES DE MEDIDA
-- ==========================================
CREATE TABLE IF NOT EXISTS catalogo_um (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sigla TEXT UNIQUE NOT NULL, -- Ej: 'm', 'pza', 'caja', 'rollo'
    descripcion TEXT, -- Ej: 'Metro', 'Pieza', 'Caja', 'Rollo'
    clave_sat_unidad TEXT -- Clave SAT c_ClaveUnidad (Ej: MTR, H87, E48)
);

-- ==========================================
-- 10. TABLAS DE ÓRDENES DE COMPRA
-- ==========================================
CREATE TABLE IF NOT EXISTS ordenes_compra (
    id_orden INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT UNIQUE NOT NULL, -- Formato: OC0001
    fecha TEXT NOT NULL,
    proveedor_id TEXT NOT NULL,
    representante TEXT NOT NULL,
    referencia TEXT,
    direccion_envio TEXT,
    telefono_envio TEXT,
    monto_total REAL DEFAULT 0.0,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id_prov)
);

CREATE TABLE IF NOT EXISTS ordenes_compra_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id INTEGER NOT NULL,
    codigo_producto TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    um TEXT NOT NULL,
    precio_unitario REAL NOT NULL,
    monto REAL NOT NULL,
    FOREIGN KEY (orden_id) REFERENCES ordenes_compra(id_orden),
    FOREIGN KEY (codigo_producto) REFERENCES inventario(codigo_producto)
);

-- ==========================================
-- 11. TABLA HISTORIAL DE COMPRAS (INVENTARIO)
-- ==========================================
CREATE TABLE IF NOT EXISTS historial_compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_producto TEXT NOT NULL,
    proveedor_id TEXT NOT NULL,
    proveedor_nombre TEXT NOT NULL,
    precio_compra REAL NOT NULL,
    cantidad REAL NOT NULL,
    fecha TEXT NOT NULL,
    monto_total REAL NOT NULL,
    usuario TEXT NOT NULL,
    FOREIGN KEY (codigo_producto) REFERENCES inventario(codigo_producto)
);

-- ==========================================
-- 12. TABLA DE FACTURAS (CFDI 4.0)
-- ==========================================
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cfdi_id TEXT NOT NULL,              -- ID interno de Facturama
    uuid TEXT,                          -- UUID del timbre fiscal
    folio_fiscal TEXT,                  -- Folio de la factura
    cotizacion_id INTEGER,              -- Cotización asociada
    cliente_id TEXT NOT NULL,
    fecha_timbrado TEXT NOT NULL,
    monto_total REAL NOT NULL,
    estado TEXT DEFAULT 'Activa',       -- Activa, Cancelada
    motivo_cancelacion TEXT,
    -- Datos fiscales del timbre (para PDF personalizado y QR)
    cert_numero TEXT,                   -- Número de certificado del emisor
    sello_cfdi TEXT,                    -- Sello digital del CFDI
    sello_sat TEXT,                     -- Sello digital del SAT
    cert_sat_numero TEXT,               -- Número de certificado del SAT
    rfc_pac TEXT,                       -- RFC del PAC (ej: SPR190613I52)
    cadena_original TEXT,               -- Cadena original del complemento de certificación
    forma_pago TEXT,                    -- Código forma de pago (ej: 03)
    metodo_pago TEXT,                   -- PUE o PPD
    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id_cotizacion),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id_cliente)
);
