from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

def get_db():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'user-mysql'),
        user=os.environ.get('DB_USER', 'fooduser'),
        password=os.environ.get('DB_PASSWORD', 'foodpassword'),
        database=os.environ.get('DB_NAME', 'userdb')
    )

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            address VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'user-service'})

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (name, email, address) VALUES (%s, %s, %s)',
        (data['name'], data['email'], data.get('address', ''))
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({'id': user_id, 'message': 'User created'}), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    import time
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as e:
            print(f"DB not ready, retrying... ({attempt+1}/10): {e}")
            time.sleep(5)
    app.run(host='0.0.0.0', port=5000)
