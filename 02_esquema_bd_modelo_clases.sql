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
  'pendiente_contacto',
  'contactando_cliente',
  'esperando_respuesta',
  'requiere_otro_horario',
  'cliente_no_respondio',
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
  raza VARCHAR(100),
  sexo VARCHAR(20),
  fecha_nacimiento DATE,
  peso_actual NUMERIC(7,2),
  caracteristicas TEXT,
  CONSTRAINT ck_mascotas_peso CHECK (peso_actual IS NULL OR peso_actual >= 0)
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

-- Catalogo inicial utilizado por el flujo de reservas.
INSERT INTO servicios
  (codigo, nombre, descripcion, precio_referencial, duracion_estimada_min)
VALUES
  ('consultas-veterinarias', 'Consulta veterinaria', 'Evaluacion clinica integral.', 50.00, 30),
  ('vacunacion', 'Vacunacion', 'Aplicacion y control del calendario de vacunas.', 45.00, 30),
  ('desparasitacion', 'Desparasitacion', 'Prevencion de parasitos internos y externos.', 35.00, 30),
  ('cirugia-general', 'Cirugia general', 'Evaluacion y procedimiento quirurgico programado.', 200.00, 90),
  ('laboratorio-clinico', 'Laboratorio clinico', 'Analisis para apoyo diagnostico.', 80.00, 45),
  ('bano-simple', 'Bano estetico', 'Higiene general para la mascota.', 40.00, 60),
  ('bano-medicado', 'Bano medicado', 'Bano con productos dermatologicos indicados.', 55.00, 60),
  ('corte-y-estilizado', 'Corte y estilizado', 'Corte de pelo y arreglo estetico.', 60.00, 90)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO servicios_medicos
  (servicio_id, requiere_receta, incluye_laboratorio, tipo_atencion_medica)
SELECT id, FALSE, codigo = 'laboratorio-clinico',
  CASE codigo
    WHEN 'vacunacion' THEN 'vacunacion'::tipo_atencion_medica
    WHEN 'desparasitacion' THEN 'desparasitacion'::tipo_atencion_medica
    WHEN 'cirugia-general' THEN 'cirugia'::tipo_atencion_medica
    WHEN 'laboratorio-clinico' THEN 'laboratorio_e_imagen'::tipo_atencion_medica
    ELSE 'consulta_general'::tipo_atencion_medica
  END
FROM servicios
WHERE codigo IN ('consultas-veterinarias', 'vacunacion', 'desparasitacion',
                 'cirugia-general', 'laboratorio-clinico')
ON CONFLICT (servicio_id) DO NOTHING;

INSERT INTO servicios_estetica
  (servicio_id, incluye_corte_pelo, incluye_bano_especial, tipo_estetica)
SELECT id, codigo = 'corte-y-estilizado', codigo = 'bano-medicado',
  CASE codigo
    WHEN 'bano-medicado' THEN 'bano_medicado'::tipo_estetica
    WHEN 'corte-y-estilizado' THEN 'corte_y_estilizado'::tipo_estetica
    ELSE 'bano_simple'::tipo_estetica
  END
FROM servicios
WHERE codigo IN ('bano-simple', 'bano-medicado', 'corte-y-estilizado')
ON CONFLICT (servicio_id) DO NOTHING;

-- Citas y procesos de atencion
CREATE TABLE citas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  mascota_id BIGINT NOT NULL REFERENCES mascotas(id) ON DELETE RESTRICT,
  servicio_id BIGINT NOT NULL REFERENCES servicios(id) ON DELETE RESTRICT,
  fecha_hora_programada TIMESTAMPTZ NOT NULL,
  fecha_hora_fin_programada TIMESTAMPTZ NOT NULL,
  estado estado_cita NOT NULL DEFAULT 'pendiente',
  es_urgente BOOLEAN NOT NULL DEFAULT FALSE,
  motivo VARCHAR(500),
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  veterinario_id BIGINT REFERENCES veterinarios(usuario_id) ON DELETE RESTRICT,
  fecha_hora_propuesta TIMESTAMPTZ,
  telefono_contacto VARCHAR(30),
  preferencia_contacto VARCHAR(20),
  nota_coordinacion VARCHAR(500),
  estado_actualizado_por BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
  fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_citas_id_mascota UNIQUE (id, mascota_id),
  CONSTRAINT ck_citas_rango CHECK (fecha_hora_fin_programada > fecha_hora_programada)
);

CREATE INDEX idx_citas_mascota ON citas (mascota_id);
CREATE INDEX idx_citas_servicio ON citas (servicio_id);
CREATE INDEX idx_citas_fecha ON citas (fecha_hora_programada);
CREATE INDEX idx_citas_veterinario_estado ON citas (veterinario_id, estado);

-- Una solicitud ocupa el slot desde que el cliente la reserva.
CREATE UNIQUE INDEX uq_citas_horario_activo
  ON citas (veterinario_id, fecha_hora_programada)
  WHERE veterinario_id IS NOT NULL
    AND estado NOT IN ('cancelada', 'no_asistio');

-- Protección de base de datos contra cruces considerando la duración real.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE citas
  ADD CONSTRAINT ex_citas_veterinario_solapamiento
  EXCLUDE USING gist (
    veterinario_id WITH =,
    tstzrange(fecha_hora_programada, fecha_hora_fin_programada, '[)') WITH &&
  )
  WHERE (
    veterinario_id IS NOT NULL
    AND estado NOT IN ('cancelada', 'no_asistio')
  );

-- Agenda recurrente y bloqueos excepcionales del veterinario.
CREATE TABLE horarios_veterinarios (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  veterinario_id BIGINT NOT NULL
    REFERENCES veterinarios(usuario_id) ON DELETE CASCADE,
  dia_semana INTEGER NOT NULL,
  hora_inicio TIME NOT NULL,
  hora_fin TIME NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT ck_horarios_dia CHECK (dia_semana BETWEEN 0 AND 6),
  CONSTRAINT ck_horarios_horas CHECK (hora_fin > hora_inicio),
  CONSTRAINT uq_horario_veterinario_rango
    UNIQUE (veterinario_id, dia_semana, hora_inicio, hora_fin)
);

CREATE INDEX idx_horarios_veterinario
  ON horarios_veterinarios (veterinario_id, dia_semana);

CREATE TABLE bloqueos_horario (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  veterinario_id BIGINT NOT NULL
    REFERENCES veterinarios(usuario_id) ON DELETE CASCADE,
  fecha_hora_inicio TIMESTAMPTZ NOT NULL,
  fecha_hora_fin TIMESTAMPTZ NOT NULL,
  motivo VARCHAR(255) NOT NULL,
  CONSTRAINT ck_bloqueos_horas CHECK (fecha_hora_fin > fecha_hora_inicio)
);

CREATE INDEX idx_bloqueos_veterinario_fecha
  ON bloqueos_horario (veterinario_id, fecha_hora_inicio);

CREATE TABLE notificaciones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  cita_id BIGINT REFERENCES citas(id) ON DELETE SET NULL,
  tipo VARCHAR(50) NOT NULL,
  titulo VARCHAR(150) NOT NULL,
  mensaje VARCHAR(500) NOT NULL,
  leida BOOLEAN NOT NULL DEFAULT FALSE,
  fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notificaciones_usuario_leida
  ON notificaciones (usuario_id, leida);

CREATE TABLE procesos_atencion (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cita_id BIGINT UNIQUE,
  mascota_id BIGINT NOT NULL REFERENCES mascotas(id) ON DELETE RESTRICT,
  tipo tipo_proceso_atencion NOT NULL,
  fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_fin TIMESTAMPTZ,
  observaciones TEXT,
  motivo_consulta TEXT,
  anamnesis TEXT,
  proxima_fecha_control DATE,
  CONSTRAINT fk_procesos_cita_mascota
    FOREIGN KEY (cita_id, mascota_id)
    REFERENCES citas(id, mascota_id) ON DELETE RESTRICT,
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
  vacunas TEXT,
  desparasitaciones TEXT,
  medicamentos TEXT,
  procedimientos TEXT,
  examenes_resultados TEXT,
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
