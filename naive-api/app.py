from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_PATH = "naive.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_value REAL,
                result REAL
            )
        """)
        conn.commit()


#Log each processed request
def log_to_db(value, result):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (timestamp, input_value, result)
            VALUES (?, ?, ?)
        """, (timestamp, value, result))
        conn.commit()

#Post endpoint to process data
@app.route('/naive-api/process', methods=['POST'])
def process_data():
    data = request.get_json(force=True)
    value = data.get("value")

    if value is None or not isinstance(value, (int, float)):
        return jsonify({"error": "'value' must be a number"}), 400
    
    # Naively assumes input is always valid
    result = value * 2
    log_to_db(value, result)
    return jsonify({"result": result})

# GET endpoint to view recent logs
@app.route('/naive-api/logs', methods=['GET'])
def view_logs():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()

    keys = ["id", "timestamp", "input_value", "result"]
    return jsonify([dict(zip(keys, row)) for row in rows])

if __name__ == '__main__':
    init_db()
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




'''
What makes it naive?
- No input validation
- No exception handling
- Single-threaded, no retries
- Fails on bad input or unexpected request format
'''








