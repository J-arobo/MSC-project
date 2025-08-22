from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timezone

app = Flask(__name__)
DB_PATH = "reactive_state.db"
DEFAULT_VALUE = 1  # Fallback multiplier input

# Initialize the database
def init_db():
    print("Initializing database...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_value REAL,
                result REAL,
                fallback_used INTEGER
            )
        """)
        conn.commit()

# Log each processed request
def log_to_db(value, result, fallback_used):
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (timestamp, input_value, result, fallback_used)
            VALUES (?, ?, ?, ?)
        """, (timestamp, value, result, int(fallback_used)))
        conn.commit()

@app.route('/reactive-api/process', methods=['POST'])
def process_data():
    try:
        data = request.get_json(force=True)
        value = data.get("value")

        if value is None or not isinstance(value, (int, float)):
            fallback_result = DEFAULT_VALUE * 2
            log_to_db(DEFAULT_VALUE, fallback_result, True)
            return jsonify({
                "warning": "Invalid input. Fallback value used.",
                "fallback_used": True,
                "result": fallback_result
            }), 200

        result = value * 2
        log_to_db(value, result, False)
        return jsonify({
            "fallback_used": False,
            "result": result})

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

# Optional: View recent logs
@app.route('/reactive-api/logs', methods=['GET'])
def view_logs():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()

    keys = ["id", "timestamp", "input_value", "result", "fallback_used"]
    return jsonify([dict(zip(keys, row)) for row in rows])

if __name__ == '__main__':
    init_db()
    print("Starting Flask app...")
    app.run(host='0.0.0.0', port=5001)
