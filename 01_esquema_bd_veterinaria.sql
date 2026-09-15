-- ==================================================================
-- ESQUEMA BD: Sistema de Gestión para Clínica Veterinaria
-- PostgreSQL 14+
-- Corresponde 1:1 a diagrama_er_clinica_veterinaria (PlantUML)
-- ==================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- ==================================================================
-- TIPOS ENUM
-- ==================================================================

DO $$ BEGIN
  CREATE TYPE estado_usuario AS ENUM ('activo','inactivo','bloqueado','pendiente_verificacion');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_token AS ENUM ('verificacion_email','recuperacion_password','invitacion');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_general AS ENUM ('activo','inactivo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_catalogo_item AS ENUM ('producto','servicio','paquete','vacuna','examen','cirugia');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_movimiento_inventario AS ENUM ('entrada_compra','salida_venta','ajuste_positivo','ajuste_negativo','devolucion','vencimiento','traslado');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_cita AS ENUM ('pendiente','confirmada','en_curso','atendida','cancelada','no_asistio','reprogramada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE evento_cita AS ENUM ('creada','confirmada','reprogramada','cancelada','atendida','no_asistio');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_imagen_medica AS ENUM ('radiografia','ecografia','tomografia','foto_clinica','otro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_caja_sesion AS ENUM ('abierta','cerrada','arqueo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE canal_venta AS ENUM ('presencial','online','telefono','whatsapp');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_transaccion AS ENUM ('pendiente','pagada','parcial','anulada','reembolsada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_pago AS ENUM ('total','parcial','anticipo','saldo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_pago AS ENUM ('pendiente','validado','rechazado','anulado');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE tipo_movimiento_fidelizacion AS ENUM ('acumulacion','canje','ajuste','vencimiento');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE canal_notificacion AS ENUM ('whatsapp','email','push','sms','interno');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_notificacion AS ENUM ('pendiente','programada','enviada','leida','fallida');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ==================================================================
-- MÓDULO 1 — AUTENTICACIÓN, ROLES Y PERMISOS
-- ==================================================================

CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR(50) NOT NULL UNIQUE,
  descripcion VARCHAR(255),
  es_rol_sistema BOOLEAN NOT NULL DEFAULT FALSE,
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS modulos_sistema (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo VARCHAR(50) NOT NULL UNIQUE,
  nombre VARCHAR(100) NOT NULL,
  orden SMALLINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS permisos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  modulo_id UUID NOT NULL REFERENCES modulos_sistema(id) ON DELETE RESTRICT,
  accion VARCHAR(30) NOT NULL,
  descripcion VARCHAR(255),
  UNIQUE (modulo_id, accion)
);

CREATE TABLE IF NOT EXISTS roles_permisos (
  rol_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permiso_id UUID NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
  PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE IF NOT EXISTS usuarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rol_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  nombres VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  email CITEXT NOT NULL UNIQUE,
  telefono VARCHAR(20),
  password_hash VARCHAR(255) NOT NULL,
  email_verificado BOOLEAN NOT NULL DEFAULT FALSE,
  estado estado_usuario NOT NULL DEFAULT 'pendiente_verificacion',
  intentos_fallidos SMALLINT NOT NULL DEFAULT 0,
  bloqueado_hasta TIMESTAMPTZ,
  foto_url VARCHAR(500),
  creado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_desactivacion TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios(rol_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_estado ON usuarios(estado);

CREATE TABLE IF NOT EXISTS tokens_verificacion (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  tipo tipo_token NOT NULL,
  token VARCHAR(255) NOT NULL UNIQUE,
  usado BOOLEAN NOT NULL DEFAULT FALSE,
  expira_en TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tokens_usuario ON tokens_verificacion(usuario_id);

CREATE TABLE IF NOT EXISTS sesiones_usuario (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  refresh_token VARCHAR(500) NOT NULL UNIQUE,
  ip_origen VARCHAR(45),
  user_agent VARCHAR(255),
  fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_expira TIMESTAMPTZ NOT NULL,
  revocada BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones_usuario(usuario_id);

CREATE TABLE IF NOT EXISTS auditoria_acciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  modulo_id UUID REFERENCES modulos_sistema(id) ON DELETE SET NULL,
  accion VARCHAR(100) NOT NULL,
  entidad_afectada VARCHAR(100),
  entidad_id UUID,
  detalle JSONB,
  ip_origen VARCHAR(45),
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria_acciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_entidad ON auditoria_acciones(entidad_afectada, entidad_id);

-- ==================================================================
-- MÓDULO 6 (base) — SUCURSALES Y CONFIGURACIÓN
-- ==================================================================

CREATE TABLE IF NOT EXISTS sucursales (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR(100) NOT NULL,
  direccion VARCHAR(255),
  telefono VARCHAR(20),
  latitud NUMERIC(10,7),
  longitud NUMERIC(10,7),
  es_principal BOOLEAN NOT NULL DEFAULT FALSE,
  estado estado_general NOT NULL DEFAULT 'activo'
);

CREATE TABLE IF NOT EXISTS horarios_atencion (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sucursal_id UUID NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
  dia_semana SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
  hora_apertura TIME NOT NULL,
  hora_cierre TIME NOT NULL,
  UNIQUE (sucursal_id, dia_semana, hora_apertura)
);

CREATE TABLE IF NOT EXISTS configuraciones_sistema (
  clave VARCHAR(100) PRIMARY KEY,
  valor VARCHAR(255) NOT NULL,
  descripcion VARCHAR(255),
  actualizado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS plantillas_whatsapp (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo_evento VARCHAR(60) NOT NULL UNIQUE,
  contenido TEXT NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS respaldos_sistema (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  archivo_url VARCHAR(500) NOT NULL,
  tipo VARCHAR(30) NOT NULL,
  generado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================================================================
-- MÓDULO 2+8 — CATÁLOGO E INVENTARIO
-- ==================================================================

CREATE TABLE IF NOT EXISTS categorias_catalogo (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo tipo_catalogo_item NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  descripcion VARCHAR(255),
  estado estado_general NOT NULL DEFAULT 'activo',
  UNIQUE (tipo, nombre)
);

CREATE TABLE IF NOT EXISTS unidades_medida (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR(30) NOT NULL UNIQUE,
  abreviatura VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS proveedores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  razon_social VARCHAR(150) NOT NULL,
  ruc VARCHAR(20) UNIQUE,
  contacto VARCHAR(100),
  telefono VARCHAR(20),
  email CITEXT,
  estado estado_general NOT NULL DEFAULT 'activo'
);

CREATE TABLE IF NOT EXISTS catalogo_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo tipo_catalogo_item NOT NULL,
  sku VARCHAR(50) UNIQUE,
  nombre VARCHAR(150) NOT NULL,
  descripcion TEXT,
  categoria_id UUID REFERENCES categorias_catalogo(id) ON DELETE SET NULL,
  unidad_medida_id UUID REFERENCES unidades_medida(id) ON DELETE SET NULL,
  precio NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (precio >= 0),
  duracion_minutos SMALLINT CHECK (duracion_minutos IS NULL OR duracion_minutos >= 0),
  stock_actual NUMERIC(12,2) NOT NULL DEFAULT 0,
  stock_minimo NUMERIC(12,2) NOT NULL DEFAULT 0,
  es_fidelizable BOOLEAN NOT NULL DEFAULT FALSE,
  puntos_otorgados INTEGER NOT NULL DEFAULT 0 CHECK (puntos_otorgados >= 0),
  sucursal_id UUID REFERENCES sucursales(id) ON DELETE SET NULL,
  estado estado_general NOT NULL DEFAULT 'activo'
);
CREATE INDEX IF NOT EXISTS idx_catalogo_tipo ON catalogo_items(tipo);
CREATE INDEX IF NOT EXISTS idx_catalogo_sucursal ON catalogo_items(sucursal_id);

CREATE TABLE IF NOT EXISTS catalogo_proveedores (
  catalogo_item_id UUID NOT NULL REFERENCES catalogo_items(id) ON DELETE CASCADE,
  proveedor_id UUID NOT NULL REFERENCES proveedores(id) ON DELETE CASCADE,
  PRIMARY KEY (catalogo_item_id, proveedor_id)
);

CREATE TABLE IF NOT EXISTS lotes_producto (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  catalogo_item_id UUID NOT NULL REFERENCES catalogo_items(id) ON DELETE CASCADE,
  numero_lote VARCHAR(50) NOT NULL,
  fecha_vencimiento DATE,
  cantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
  proveedor_id UUID REFERENCES proveedores(id) ON DELETE SET NULL,
  fecha_ingreso TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (catalogo_item_id, numero_lote)
);

CREATE TABLE IF NOT EXISTS galeria_fotos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sucursal_id UUID NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
  url VARCHAR(500) NOT NULL,
  descripcion VARCHAR(255),
  orden SMALLINT NOT NULL DEFAULT 0
);

-- ==================================================================
-- ACTORES: CLIENTES, MASCOTAS, PERSONAL
-- ==================================================================

CREATE TABLE IF NOT EXISTS clientes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
  direccion VARCHAR(255),
  fecha_nacimiento DATE,
  puntos_fidelizacion INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS veterinarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
  numero_colegiatura VARCHAR(50) UNIQUE,
  especialidad VARCHAR(100),
  sucursal_id UUID REFERENCES sucursales(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cajeros (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
  sucursal_id UUID REFERENCES sucursales(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS horarios_veterinario (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  veterinario_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE CASCADE,
  dia_semana SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
  hora_inicio TIME NOT NULL,
  hora_fin TIME NOT NULL
);

CREATE TABLE IF NOT EXISTS bloqueos_horario_veterinario (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  veterinario_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE CASCADE,
  fecha_inicio TIMESTAMPTZ NOT NULL,
  fecha_fin TIMESTAMPTZ NOT NULL,
  motivo VARCHAR(255),
  CHECK (fecha_fin > fecha_inicio)
);

CREATE TABLE IF NOT EXISTS mascotas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  nombre VARCHAR(100) NOT NULL,
  especie VARCHAR(50) NOT NULL,
  raza VARCHAR(100),
  sexo VARCHAR(10) CHECK (sexo IN ('macho','hembra','desconocido')),
  fecha_nacimiento DATE,
  peso_actual NUMERIC(6,2) CHECK (peso_actual IS NULL OR peso_actual >= 0),
  alergias TEXT,
  condiciones_especiales TEXT,
  estado estado_general NOT NULL DEFAULT 'activo'
);
CREATE INDEX IF NOT EXISTS idx_mascotas_cliente ON mascotas(cliente_id);

-- ==================================================================
-- MÓDULO 3 — CITAS
-- ==================================================================

CREATE TABLE IF NOT EXISTS citas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
  mascota_id UUID NOT NULL REFERENCES mascotas(id) ON DELETE RESTRICT,
  veterinario_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE RESTRICT,
  catalogo_item_id UUID REFERENCES catalogo_items(id) ON DELETE SET NULL,
  sucursal_id UUID NOT NULL REFERENCES sucursales(id) ON DELETE RESTRICT,
  fecha_hora TIMESTAMPTZ NOT NULL,
  duracion_minutos SMALLINT NOT NULL DEFAULT 30,
  estado estado_cita NOT NULL DEFAULT 'pendiente',
  es_urgente BOOLEAN NOT NULL DEFAULT FALSE,
  motivo_cancelacion VARCHAR(255),
  confirmada_asistencia BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_citas_vet_fecha ON citas(veterinario_id, fecha_hora);

CREATE TABLE IF NOT EXISTS citas_historial (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cita_id UUID NOT NULL REFERENCES citas(id) ON DELETE CASCADE,
  evento evento_cita NOT NULL,
  usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_anterior TIMESTAMPTZ,
  fecha_nueva TIMESTAMPTZ,
  motivo VARCHAR(255),
  fecha_evento TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==================================================================
-- MÓDULO 4 — EXPEDIENTE CLÍNICO
-- ==================================================================

CREATE TABLE IF NOT EXISTS historias_clinicas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mascota_id UUID NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
  cita_id UUID UNIQUE REFERENCES citas(id) ON DELETE SET NULL,
  veterinario_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE RESTRICT,
  fecha_atencion TIMESTAMPTZ NOT NULL DEFAULT now(),
  motivo_consulta TEXT,
  diagnostico TEXT,
  observaciones TEXT,
  notas_internas TEXT,
  peso_registrado NUMERIC(6,2)
);

CREATE TABLE IF NOT EXISTS tratamientos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  descripcion TEXT NOT NULL,
  duracion_dias SMALLINT,
  fecha_inicio DATE,
  fecha_fin DATE
);

CREATE TABLE IF NOT EXISTS recetas_medicas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  indicaciones_generales TEXT,
  fecha_emision TIMESTAMPTZ NOT NULL DEFAULT now(),
  enviado_whatsapp BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS receta_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  receta_id UUID NOT NULL REFERENCES recetas_medicas(id) ON DELETE CASCADE,
  medicamento VARCHAR(150) NOT NULL,
  dosis VARCHAR(100),
  frecuencia VARCHAR(100),
  duracion VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS resultados_laboratorio (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  nombre_examen VARCHAR(150) NOT NULL,
  archivo_url VARCHAR(500),
  fecha_examen DATE NOT NULL,
  notificado_cliente BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS imagenes_medicas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  tipo tipo_imagen_medica NOT NULL,
  archivo_url VARCHAR(500) NOT NULL,
  descripcion VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS vacunas_aplicadas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mascota_id UUID NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
  historia_clinica_id UUID REFERENCES historias_clinicas(id) ON DELETE SET NULL,
  veterinario_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE RESTRICT,
  nombre_vacuna VARCHAR(150) NOT NULL,
  fecha_aplicacion DATE NOT NULL,
  proxima_fecha_estimada DATE
);

CREATE TABLE IF NOT EXISTS desparasitaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mascota_id UUID NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
  historia_clinica_id UUID REFERENCES historias_clinicas(id) ON DELETE SET NULL,
  producto VARCHAR(150) NOT NULL,
  fecha_aplicacion DATE NOT NULL,
  proxima_fecha_estimada DATE
);

CREATE TABLE IF NOT EXISTS cirugias (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  procedimiento VARCHAR(255) NOT NULL,
  anestesia VARCHAR(150),
  observaciones TEXT,
  fecha TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS derivaciones_veterinarias (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  veterinario_origen_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE RESTRICT,
  veterinario_destino_id UUID NOT NULL REFERENCES veterinarios(id) ON DELETE RESTRICT,
  motivo VARCHAR(255),
  CHECK (veterinario_origen_id <> veterinario_destino_id)
);

CREATE TABLE IF NOT EXISTS encuestas_satisfaccion (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  historia_clinica_id UUID NOT NULL REFERENCES historias_clinicas(id) ON DELETE CASCADE,
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  calificacion SMALLINT NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
  comentario TEXT,
  fecha_respuesta TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (historia_clinica_id, cliente_id)
);

-- ==================================================================
-- MÓDULO 5 — CAJA Y PAGOS
-- ==================================================================

CREATE TABLE IF NOT EXISTS metodos_pago (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR(30) NOT NULL UNIQUE,
  requiere_comprobante BOOLEAN NOT NULL DEFAULT FALSE,
  estado estado_general NOT NULL DEFAULT 'activo'
);

CREATE TABLE IF NOT EXISTS caja_sesiones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cajero_id UUID NOT NULL REFERENCES cajeros(id) ON DELETE RESTRICT,
  sucursal_id UUID NOT NULL REFERENCES sucursales(id) ON DELETE RESTRICT,
  fondo_inicial NUMERIC(10,2) NOT NULL DEFAULT 0,
  monto_esperado NUMERIC(10,2) NOT NULL DEFAULT 0,
  monto_real NUMERIC(10,2),
  diferencia NUMERIC(10,2),
  estado estado_caja_sesion NOT NULL DEFAULT 'abierta',
  fecha_apertura TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_cierre TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transacciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  numero_orden VARCHAR(30) NOT NULL UNIQUE,
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
  mascota_id UUID REFERENCES mascotas(id) ON DELETE SET NULL,
  cita_id UUID REFERENCES citas(id) ON DELETE SET NULL,
  historia_clinica_id UUID REFERENCES historias_clinicas(id) ON DELETE SET NULL,
  caja_sesion_id UUID REFERENCES caja_sesiones(id) ON DELETE SET NULL,
  canal canal_venta NOT NULL DEFAULT 'presencial',
  estado estado_transaccion NOT NULL DEFAULT 'pendiente',
  subtotal NUMERIC(10,2) NOT NULL DEFAULT 0,
  descuento_total NUMERIC(10,2) NOT NULL DEFAULT 0,
  total NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
  motivo_anulacion VARCHAR(255),
  anulado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_anulacion TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS transaccion_detalles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaccion_id UUID NOT NULL REFERENCES transacciones(id) ON DELETE CASCADE,
  catalogo_item_id UUID NOT NULL REFERENCES catalogo_items(id) ON DELETE RESTRICT,
  cantidad NUMERIC(10,2) NOT NULL CHECK (cantidad > 0),
  precio_unitario NUMERIC(10,2) NOT NULL CHECK (precio_unitario >= 0),
  subtotal NUMERIC(10,2) NOT NULL CHECK (subtotal >= 0),
  es_fidelizable_snapshot BOOLEAN NOT NULL DEFAULT FALSE,
  puntos_unitarios_snapshot INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS descuentos_aplicados (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaccion_id UUID NOT NULL REFERENCES transacciones(id) ON DELETE CASCADE,
  monto_descuento NUMERIC(10,2) NOT NULL CHECK (monto_descuento >= 0),
  motivo VARCHAR(255),
  autorizado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pagos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaccion_id UUID NOT NULL REFERENCES transacciones(id) ON DELETE CASCADE,
  caja_sesion_id UUID REFERENCES caja_sesiones(id) ON DELETE SET NULL,
  metodo_pago_id UUID NOT NULL REFERENCES metodos_pago(id) ON DELETE RESTRICT,
  tipo tipo_pago NOT NULL DEFAULT 'total',
  monto NUMERIC(10,2) NOT NULL CHECK (monto > 0),
  comprobante_url VARCHAR(500),
  estado estado_pago NOT NULL DEFAULT 'pendiente',
  validado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_pago TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_validacion TIMESTAMPTZ
);

-- Transacción_id referenciado por inventario (se crea después por dependencia circular lógica)
-- inventarios y fidelización dependen de transacciones, así que van después:

CREATE TABLE IF NOT EXISTS inventario_movimientos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  catalogo_item_id UUID NOT NULL REFERENCES catalogo_items(id) ON DELETE RESTRICT,
  tipo_movimiento tipo_movimiento_inventario NOT NULL,
  cantidad NUMERIC(12,2) NOT NULL,
  stock_anterior NUMERIC(12,2) NOT NULL,
  stock_nuevo NUMERIC(12,2) NOT NULL,
  lote_id UUID REFERENCES lotes_producto(id) ON DELETE SET NULL,
  proveedor_id UUID REFERENCES proveedores(id) ON DELETE SET NULL,
  transaccion_id UUID REFERENCES transacciones(id) ON DELETE SET NULL,
  motivo VARCHAR(255),
  usuario_id UUID REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_inv_item ON inventario_movimientos(catalogo_item_id);
CREATE INDEX IF NOT EXISTS idx_inv_trans ON inventario_movimientos(transaccion_id);

-- ==================================================================
-- FIDELIZACIÓN
-- ==================================================================

CREATE TABLE IF NOT EXISTS fidelizacion_movimientos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  transaccion_id UUID REFERENCES transacciones(id) ON DELETE SET NULL,
  tipo tipo_movimiento_fidelizacion NOT NULL,
  puntos INTEGER NOT NULL,
  saldo_resultante INTEGER NOT NULL,
  descripcion VARCHAR(255),
  registrado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ==================================================================
-- MÓDULO 7 — NOTIFICACIONES
-- ==================================================================

CREATE TABLE IF NOT EXISTS notificaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
  canal canal_notificacion NOT NULL,
  codigo_evento VARCHAR(60) NOT NULL,
  entidad_relacionada VARCHAR(60),
  entidad_id UUID,
  contenido TEXT NOT NULL,
  estado estado_notificacion NOT NULL DEFAULT 'pendiente',
  fecha_programada TIMESTAMPTZ,
  fecha_envio TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notif_usuario ON notificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notif_estado ON notificaciones(estado);
