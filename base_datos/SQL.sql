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
    disponibilidad TEXT DEFAULT 'Disponible', -- Nuevo campo: 'Disponible' o 'Sobrepedido'
    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id_cotizacion),
    FOREIGN KEY (codigo_producto) REFERENCES inventario(codigo_producto)
);

-- ==========================================
-- 6. TABLA DE DATOS FISCALES (Estática)
-- ==========================================
-- Usamos un CHECK (id=1) para garantizar que siempre haya un solo registro
CREATE TABLE IF NOT EXISTS datos_fiscales (
    id INTEGER PRIMARY KEY CHECK (id = 1), 
    nombre_empresa TEXT DEFAULT 'PRO ELECTRO MONTERREY',
    telefono TEXT DEFAULT '(81) 1634 7681',
    ubicacion TEXT DEFAULT 'Monterrey, Nuevo León',
    rfc TEXT,
    representante_legal TEXT DEFAULT 'EDWIN GUERRERO GARCÍA',
    terminos_condiciones TEXT
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

CREATE TABLE IF NOT EXISTS catalogo_um (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sigla TEXT UNIQUE NOT NULL, -- Ej: 'm', 'pza', 'caja', 'rollo'
    descripcion TEXT -- Ej: 'Metro', 'Pieza', 'Caja', 'Rollo'
);
