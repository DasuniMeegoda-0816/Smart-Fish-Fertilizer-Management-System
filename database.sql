CREATE DATABASE IF NOT EXISTS smart_fish_db;
USE smart_fish_db;

CREATE TABLE IF NOT EXISTS fish_waste (
    waste_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    location VARCHAR(150) NOT NULL,
    quantity_kg DECIMAL(10,2) NOT NULL,
    status VARCHAR(30) DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fertilizers (
    fertilizer_id INT AUTO_INCREMENT PRIMARY KEY,
    fertilizer_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock_kg DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS fertilizer_orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    farmer_name VARCHAR(100) NOT NULL,
    fertilizer_id INT NOT NULL,
    quantity_kg DECIMAL(10,2) NOT NULL,
    status VARCHAR(30) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(fertilizer_id)
);

INSERT INTO fertilizers (fertilizer_name, price, stock_kg)
SELECT 'Organic Fish Compost', 250.00, 500.00
WHERE NOT EXISTS (SELECT 1 FROM fertilizers WHERE fertilizer_name = 'Organic Fish Compost');
INSERT INTO fertilizers (fertilizer_name, price, stock_kg)
SELECT 'Liquid Fish Fertilizer', 450.00, 200.00
WHERE NOT EXISTS (SELECT 1 FROM fertilizers WHERE fertilizer_name = 'Liquid Fish Fertilizer');
