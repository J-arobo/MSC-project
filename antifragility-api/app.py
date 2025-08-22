from flask import Flask, request, jsonify
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from prometheus_client import Counter, Gauge, generate_latest
import sqlite3
import random
import time
from datetime import datetime, timezone
import os




app = Flask(__name__)
DB_PATH = "state.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                failures INTEGER,
                retries INTEGER,
                fallback_used INTEGER,
                notes TEXT
            )
        """)
        conn.commit()


#Logging Function
def log_event(failures=0, retries=0, fallback_used=0, notes=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO metrics (timestamp, failures, retries, fallback_used, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, failures, retries, fallback_used, notes))
            conn.commit()
    except Exception as e:
        print(f"DB insert failed: {e}")



# Update failure count
def record_failure(retries=0, fallback_used=1,notes="RetryError treiggered"):
    log_event(failures=1, retries=retries, fallback_used=fallback_used, notes=notes)
    increment_failure_count()

#Helper function for inrement_failure_count above
def increment_failure_count():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Ensure a single summary row exists (e.g., id=1)
        cursor.execute("""
            INSERT OR IGNORE INTO metrics (id, timestamp, failures, retries, fallback_used, notes)
            VALUES (1, ?, 0, 0, 0, 'summary')
        """, (datetime.now(timezone.utc).isoformat(),))
        cursor.execute("""
            UPDATE metrics SET failures = failures + 1 WHERE id = 1
        """)
        conn.commit()   

# Get failure count
def get_failure_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT SUM(failures) FROM metrics")
        result = cursor.fetchone()
        count = result[0] if result and result[0] is not None else 0
    except sqlite3.OperationalError:
        count = 0
    conn.close()
    return count


# Adaptive retry logic
def get_retry_attempts():
    failures = get_failure_count()
    return min(5, 3 + failures // 2)  # Increase retries as failures grow

def adaptive_operation(value):
    attempts = get_retry_attempts()

    @retry(stop=stop_after_attempt(attempts), wait=wait_fixed(1))
    def inner():
        if random.random() < 0.5:
            raise Exception("Simulated failure")
        time.sleep(0.2)
        return value * 2

    return inner()

@app.route('/antifragile-api/process', methods=['POST'])
def process_data():
    REQUESTS.inc()   #Count every incoming request


    try:
        data = request.get_json(force=True)
        value = data.get("value")

        if value is None or not isinstance(value, (int, float)):
            return jsonify({"error": "Invalid input: 'value' must be a number"}), 400

        try:
            retry_attempts = get_retry_attempts()
            RETRIES.set(retry_attempts)     #Track current retry strategy

            result = adaptive_operation(value)
            return jsonify({
                "result": result,
                "adaptive_retries": retry_attempts
            })
        except RetryError:
            record_failure(
                retries=retry_attempts,
                fallback_used=1,
                notes="Fallback used after retries"
            )
            FALLBACKS.inc()


            fallback_result = value * 1.5       #Count fallback usage
            return jsonify({
                "warning": "Operation failed. Fallback used.",
                "result": fallback_result,
                "adaptive_retries": get_retry_attempts()
            }), 200

    except Exception as e:
        #log the unexpected errors
        record_failure(
            retries=0,
            notes=f"Unexpected error: {str(e)}"
        )
        #Return structured error response to client
        #return jsonify({"error": f"Internal error: {str(e)}"}), 500
        return jsonify({"error": "Internal server error:"}), 500
   
    
# Metrics
REQUESTS = Counter('antifragile_requests_total', 'Total requests')
FALLBACKS = Counter('antifragile_fallbacks_total', 'Fallbacks triggered')
RETRIES = Gauge('antifragile_adaptive_retries', 'Adaptive retry count')


#route to view recent logs
@app.route('/antifragile-api/logs', methods=['GET'])
def view_logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    keys = ["id", "timestamp", "failures", "retries", "fallback_used", "notes"]
    return jsonify([dict(zip(keys, row)) for row in rows])



@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

init_db()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)