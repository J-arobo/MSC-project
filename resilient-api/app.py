from flask import Flask, request, jsonify
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
import random
import time

app = Flask(__name__)

# Simulated fragile dependency with stressors
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def fragile_operation(value):

    # Some of the chaos injected internaly are: 
    
    #Simulate timeout
    if random.random() < 0.7:   #Instead of 0.3 to intensify chaos
        print("Simulated timeout triggered")
        raise TimeoutError("Simulated timeout")
    
    #Simulated variable latency
    elif random.random() < 0.5:
        latency = random.uniform(0.5, 2.0)
        print(f"Simulated latency: {latency: 2f}s")
        time.sleep(latency)

    #Simulate memory spike
    if random.random() < 0.2:
        raise MemoryError("Simulated memory spike")

    # Simulate random failure
    if random.random() < 0.5:
        raise Exception("Simulated failure")
    time.sleep(0.2)  # Simulate latency
    return value * 2

@app.route('/resilient-api/process', methods=['POST'])
def process_data():
    try:
        data = request.get_json(force=True)
        value = data.get("value")

        print(f"Received request with value: {value}")

        if value is None or not isinstance(value, (int, float)):
            print("Invalid Input")
            return jsonify({"error": "Invalid input: 'value' must be a number"}), 400

        try:
            result = fragile_operation(value)
            print(f"Operation Succeeded with result: {result}")
            return jsonify({
                "result": result,
                "retries_used": True
            })
        except RetryError:
            # Fallback after retries fail
            fallback_result = value * 1.5
            print(f"Operation failed after retries. Fallback result: {fallback_result}")
            return jsonify({
                "warning": "Dependency failed after retries. Fallback used.",
                "result": fallback_result,
                "retries_used": False
            }), 200

    except Exception as e:
        print(f"Unhandled exception: {str(e)}")
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
