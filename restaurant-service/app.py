from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

def get_db():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'restaurant-mysql'),
        user=os.environ.get('DB_USER', 'fooduser'),
        password=os.environ.get('DB_PASSWORD', 'foodpassword'),
        database=os.environ.get('DB_NAME', 'restaurantdb')
    )

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            cuisine VARCHAR(100),
            rating FLOAT DEFAULT 4.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            restaurant_id INT NOT NULL,
            name VARCHAR(150) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM restaurants')
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO restaurants (name, cuisine, rating) VALUES ('Spice Junction', 'Indian', 4.5)")
        cursor.execute("INSERT INTO restaurants (name, cuisine, rating) VALUES ('Pizza Hub', 'Italian', 4.2)")
        rest1_id = cursor.lastrowid - 1
        rest2_id = cursor.lastrowid
        cursor.execute("INSERT INTO menu_items (restaurant_id, name, price) VALUES (%s, 'Butter Chicken', 280.00)", (rest1_id,))
        cursor.execute("INSERT INTO menu_items (restaurant_id, name, price) VALUES (%s, 'Paneer Tikka', 220.00)", (rest1_id,))
        cursor.execute("INSERT INTO menu_items (restaurant_id, name, price) VALUES (%s, 'Margherita Pizza', 250.00)", (rest2_id,))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'restaurant-service'})

@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM restaurants')
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(restaurants)

@app.route('/api/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM restaurants WHERE id = %s', (restaurant_id,))
    restaurant = cursor.fetchone()
    cursor.close()
    conn.close()
    if restaurant:
        return jsonify(restaurant)
    return jsonify({'error': 'Restaurant not found'}), 404

@app.route('/api/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_menu(restaurant_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = %s', (restaurant_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(items)

@app.route('/api/menu-items/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM menu_items WHERE id = %s', (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    if item:
        return jsonify(item)
    return jsonify({'error': 'Item not found'}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
