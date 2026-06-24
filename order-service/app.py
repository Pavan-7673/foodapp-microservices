from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import requests as http_requests
import os

app = Flask(__name__)
CORS(app)

USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:5000')
RESTAURANT_SERVICE_URL = os.environ.get('RESTAURANT_SERVICE_URL', 'http://restaurant-service:5000')

def get_db():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'order-mysql'),
        user=os.environ.get('DB_USER', 'fooduser'),
        password=os.environ.get('DB_PASSWORD', 'foodpassword'),
        database=os.environ.get('DB_NAME', 'orderdb')
    )

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            restaurant_id INT NOT NULL,
            menu_item_id INT NOT NULL,
            quantity INT NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'order-service'})

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    user_id = data['user_id']
    restaurant_id = data['restaurant_id']
    menu_item_id = data['menu_item_id']
    quantity = data.get('quantity', 1)

    # Inter-service call #1: validate user exists via user-service
    user_resp = http_requests.get(f"{USER_SERVICE_URL}/api/users/{user_id}", timeout=5)
    if user_resp.status_code != 200:
        return jsonify({'error': 'Invalid user'}), 400

    # Inter-service call #2: get menu item price via restaurant-service
    item_resp = http_requests.get(f"{RESTAURANT_SERVICE_URL}/api/menu-items/{menu_item_id}", timeout=5)
    if item_resp.status_code != 200:
        return jsonify({'error': 'Invalid menu item'}), 400

    item = item_resp.json()
    total_price = float(item['price']) * quantity

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO orders (user_id, restaurant_id, menu_item_id, quantity, total_price) VALUES (%s, %s, %s, %s, %s)',
        (user_id, restaurant_id, menu_item_id, quantity, total_price)
    )
    conn.commit()
    order_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({
        'order_id': order_id,
        'total_price': total_price,
        'message': 'Order placed successfully'
    }), 201

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders WHERE id = %s', (order_id,))
    order = cursor.fetchone()
    cursor.close()
    conn.close()
    if order:
        return jsonify(order)
    return jsonify({'error': 'Order not found'}), 404

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(orders)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
