-- Esquema relacional del modelo de clases de la clinica veterinaria.
-- Compatible con PostgreSQL 14+.

BEGIN;

CREATE SCHEMA IF NOT EXISTS clinica_veterinaria;
SET search_path TO clinica_veterinaria, public;

-- Tipos enumerados
CREATE TYPE tipo_usuario AS ENUM (
  'cliente',
  'veterinario',
  'cajero',
  'administrador'
);

CREATE TYPE estado_cita AS ENUM (
  'pendiente',
  'confirmada',
  'reprogramada',
  'atendida',
  'cancelada',
  'no_asistio'
);

CREATE TYPE tipo_atencion_medica AS ENUM (
  'consulta_general',
  'cirugia',
  'vacunacion',
  'desparasitacion',
  'laboratorio_e_imagen'
);

CREATE TYPE tipo_estetica AS ENUM (
  'bano_simple',
  'bano_medicado',
  'corte_y_estilizado',
  'corte_de_unas_y_limpieza_oidos'
);

CREATE TYPE tipo_proceso_atencion AS ENUM ('medica', 'estetica');

CREATE TYPE estado_pago AS ENUM (
  'pendiente',
  'pago_enviado',
  'validado_confirmado',
  'anulado'
);

-- Usuarios y subtipos
CREATE TABLE usuarios (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre VARCHAR(150) NOT NULL,
  correo VARCHAR(254) NOT NULL,
  contrasena VARCHAR(255) NOT NULL,
  tipo tipo_usuario NOT NULL,
  CONSTRAINT uq_usuarios_correo UNIQUE (correo)
);

CREATE UNIQUE INDEX uq_usuarios_correo_lower ON usuarios (LOWER(correo));

CREATE TABLE clientes (
  usuario_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  telefono VARCHAR(30),
  direccion VARCHAR(255)
);

CREATE TABLE veterinarios (
  usuario_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  colegiatura VARCHAR(50) NOT NULL UNIQUE,
  especialidad VARCHAR(100)
);

CREATE TABLE cajeros (
  usuario_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE administradores (
  usuario_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE permisos (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  administrador_id BIGINT NOT NULL
    REFERENCES administradores(usuario_id) ON DELETE RESTRICT,
  modulo VARCHAR(100) NOT NULL,
  puede_ver BOOLEAN NOT NULL DEFAULT FALSE,
  puede_editar BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT uq_permisos_administrador_modulo
    UNIQUE (administrador_id, modulo)
);

CREATE TABLE auditoria_acciones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  administrador_id BIGINT NOT NULL
    REFERENCES administradores(usuario_id) ON DELETE RESTRICT,
  accion_critica VARCHAR(255) NOT NULL,
  fecha_hora TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Mascotas y servicios
CREATE TABLE mascotas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cliente_id BIGINT NOT NULL REFERENCES clientes(usuario_id) ON DELETE RESTRICT,
  nombre VARCHAR(100) NOT NULL,
  especie VARCHAR(80) NOT NULL,
  raza VARCHAR(100)
);

CREATE TABLE servicios (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo VARCHAR(50) NOT NULL UNIQUE,
  nombre VARCHAR(150) NOT NULL,
  descripcion TEXT,
  precio_referencial NUMERIC(12,2) NOT NULL,
  duracion_estimada_min INTEGER NOT NULL,
  CONSTRAINT ck_servicios_precio CHECK (precio_referencial >= 0),
  CONSTRAINT ck_servicios_duracion CHECK (duracion_estimada_min > 0)
);

CREATE TABLE servicios_medicos (
  servicio_id BIGINT PRIMARY KEY REFERENCES servicios(id) ON DELETE CASCADE,
  requiere_receta BOOLEAN NOT NULL DEFAULT FALSE,
  incluye_laboratorio BOOLEAN NOT NULL DEFAULT FALSE,
  tipo_atencion_medica tipo_atencion_medica NOT NULL
);

CREATE TABLE servicios_estetica (
  servicio_id BIGINT PRIMARY KEY REFERENCES servicios(id) ON DELETE CASCADE,
  incluye_corte_pelo BOOLEAN NOT NULL DEFAULT FALSE,
  incluye_bano_especial BOOLEAN NOT NULL DEFAULT FALSE,
  tipo_estetica tipo_estetica NOT NULL
);

-- Citas y procesos de atencion
CREATE TABLE citas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  mascota_id BIGINT NOT NULL REFERENCES mascotas(id) ON DELETE RESTRICT,
  servicio_id BIGINT NOT NULL REFERENCES servicios(id) ON DELETE RESTRICT,
  fecha_hora_programada TIMESTAMPTZ NOT NULL,
  estado estado_cita NOT NULL DEFAULT 'pendiente',
  es_urgente BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_citas_mascota ON citas (mascota_id);
CREATE INDEX idx_citas_servicio ON citas (servicio_id);
CREATE INDEX idx_citas_fecha ON citas (fecha_hora_programada);

CREATE TABLE procesos_atencion (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cita_id BIGINT NOT NULL UNIQUE REFERENCES citas(id) ON DELETE RESTRICT,
  mascota_id BIGINT NOT NULL REFERENCES mascotas(id) ON DELETE RESTRICT,
  tipo tipo_proceso_atencion NOT NULL,
  fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_fin TIMESTAMPTZ,
  observaciones TEXT,
  CONSTRAINT ck_procesos_fechas
    CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);

CREATE INDEX idx_procesos_mascota ON procesos_atencion (mascota_id);

CREATE TABLE procesos_atencion_medica (
  proceso_id BIGINT PRIMARY KEY REFERENCES procesos_atencion(id) ON DELETE CASCADE,
  veterinario_id BIGINT NOT NULL
    REFERENCES veterinarios(usuario_id) ON DELETE RESTRICT,
  diagnostico TEXT,
  tratamiento TEXT
);

CREATE TABLE procesos_atencion_estetica (
  proceso_id BIGINT PRIMARY KEY REFERENCES procesos_atencion(id) ON DELETE CASCADE,
  notas_especiales_estilista TEXT,
  productos_utilizados TEXT
);

CREATE TABLE fichas_clinicas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proceso_medico_id BIGINT NOT NULL UNIQUE
    REFERENCES procesos_atencion_medica(proceso_id) ON DELETE CASCADE,
  peso NUMERIC(7,2),
  temperatura NUMERIC(5,2),
  historial_alergias TEXT,
  CONSTRAINT ck_fichas_peso CHECK (peso IS NULL OR peso >= 0),
  CONSTRAINT ck_fichas_temperatura CHECK (
    temperatura IS NULL OR temperatura > 0
  )
);

CREATE TABLE examenes_medicos_adjuntos (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ficha_clinica_id BIGINT NOT NULL
    REFERENCES fichas_clinicas(id) ON DELETE CASCADE,
  tipo_examen VARCHAR(100) NOT NULL,
  archivo_ruta VARCHAR(500) NOT NULL
);

CREATE INDEX idx_examenes_ficha
  ON examenes_medicos_adjuntos (ficha_clinica_id);

-- Inventario y tienda
CREATE TABLE categorias_producto (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE proveedores (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  razon_social VARCHAR(180) NOT NULL
);

CREATE TABLE productos (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  categoria_id BIGINT NOT NULL
    REFERENCES categorias_producto(id) ON DELETE RESTRICT,
  proveedor_id BIGINT NOT NULL REFERENCES proveedores(id) ON DELETE RESTRICT,
  sku VARCHAR(50) NOT NULL UNIQUE,
  nombre VARCHAR(150) NOT NULL,
  precio_venta NUMERIC(12,2) NOT NULL,
  stock_actual INTEGER NOT NULL DEFAULT 0,
  stock_minimo INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT ck_productos_precio CHECK (precio_venta >= 0),
  CONSTRAINT ck_productos_stock_actual CHECK (stock_actual >= 0),
  CONSTRAINT ck_productos_stock_minimo CHECK (stock_minimo >= 0)
);

CREATE INDEX idx_productos_categoria ON productos (categoria_id);
CREATE INDEX idx_productos_proveedor ON productos (proveedor_id);

-- Caja, ordenes y comprobantes
CREATE TABLE cajas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cajero_id BIGINT NOT NULL REFERENCES cajeros(usuario_id) ON DELETE RESTRICT,
  fondo_inicial NUMERIC(12,2) NOT NULL,
  total_ingresos_validados NUMERIC(12,2) NOT NULL DEFAULT 0,
  estado_caja VARCHAR(20) NOT NULL,
  CONSTRAINT ck_cajas_fondo CHECK (fondo_inicial >= 0),
  CONSTRAINT ck_cajas_ingresos CHECK (total_ingresos_validados >= 0),
  CONSTRAINT ck_cajas_estado CHECK (estado_caja IN ('abierta', 'cerrada'))
);

CREATE INDEX idx_cajas_cajero ON cajas (cajero_id);

CREATE TABLE ordenes_cobro (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo_orden VARCHAR(50) NOT NULL UNIQUE,
  cajero_id BIGINT NOT NULL REFERENCES cajeros(usuario_id) ON DELETE RESTRICT,
  cliente_id BIGINT NOT NULL REFERENCES clientes(usuario_id) ON DELETE RESTRICT,
  caja_id BIGINT NOT NULL REFERENCES cajas(id) ON DELETE RESTRICT,
  proceso_atencion_id BIGINT
    REFERENCES procesos_atencion(id) ON DELETE SET NULL,
  monto_total NUMERIC(12,2) NOT NULL,
  estado_pago estado_pago NOT NULL DEFAULT 'pendiente',
  CONSTRAINT ck_ordenes_monto CHECK (monto_total >= 0)
);

CREATE INDEX idx_ordenes_cajero ON ordenes_cobro (cajero_id);
CREATE INDEX idx_ordenes_cliente ON ordenes_cobro (cliente_id);
CREATE INDEX idx_ordenes_caja ON ordenes_cobro (caja_id);

CREATE TABLE comprobantes_pago_whatsapp (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  orden_cobro_id BIGINT NOT NULL UNIQUE
    REFERENCES ordenes_cobro(id) ON DELETE CASCADE,
  medio_pago VARCHAR(80) NOT NULL,
  codigo_operacion VARCHAR(100) NOT NULL,
  captura_imagen VARCHAR(500) NOT NULL
);

CREATE TABLE comprobantes_venta (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  orden_cobro_id BIGINT NOT NULL UNIQUE
    REFERENCES ordenes_cobro(id) ON DELETE RESTRICT,
  serie_correlativo VARCHAR(50) NOT NULL UNIQUE,
  total_pagar NUMERIC(12,2) NOT NULL,
  CONSTRAINT ck_comprobantes_total CHECK (total_pagar >= 0)
);

COMMIT;
