-- init.sql

-- Tabla de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    fecha_registro DATE DEFAULT CURRENT_DATE
);

-- Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
    producto_id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    categoria VARCHAR(50),
    precio DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0
);

-- Tabla de Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    pedido_id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL,
    fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10, 2) DEFAULT 0.00,
    estado VARCHAR(20) DEFAULT 'Pendiente',
    CONSTRAINT fk_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE CASCADE
);

-- Tabla de Detalle del Pedido
CREATE TABLE IF NOT EXISTS detalles_pedido (
    detalle_id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    CONSTRAINT fk_producto FOREIGN KEY (producto_id) REFERENCES productos(producto_id) ON DELETE CASCADE
);

-- Inserción de Datos de Prueba
INSERT INTO clientes (nombre, apellido, email, fecha_registro) VALUES
('Sofía', 'García', 'sofia.garcia@email.com', '2026-01-15'),
('Mateo', 'López', 'mateo.lopez@email.com', '2026-02-10'),
('Valeria', 'Rodríguez', 'valeria.rodriguez@email.com', '2026-03-01'),
('Lucas', 'Martínez', 'lucas.martinez@email.com', '2026-04-12')
ON CONFLICT DO NOTHING;

INSERT INTO productos (nombre, categoria, precio, stock) VALUES
('Laptop Pro 15"', 'Electrónica', 1299.99, 15),
('Mouse Inalámbrico', 'Accesorios', 25.50, 50),
('Teclado Mecánico RGB', 'Accesorios', 85.00, 30),
('Monitor 27" 4K', 'Electrónica', 349.99, 10),
('Auriculares Cancelación Ruido', 'Audio', 199.00, 20)
ON CONFLICT DO NOTHING;

INSERT INTO pedidos (cliente_id, fecha_pedido, total, estado) VALUES
(1, '2026-06-10 10:30:00', 1325.49, 'Completado'),
(2, '2026-06-15 14:20:00', 85.00, 'Enviado'),
(3, '2026-07-01 09:15:00', 548.99, 'Pendiente')
ON CONFLICT DO NOTHING;

INSERT INTO detalles_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES
(1, 1, 1, 1299.99),
(1, 2, 1, 25.50),
(2, 3, 1, 85.00),
(3, 4, 1, 349.99),
(3, 5, 1, 199.00)
ON CONFLICT DO NOTHING;
