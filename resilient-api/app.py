from flask import Flask, request, jsonify
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
import random
import time
import logging
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
REQUEST_COUNT = Counter("resilient_requests_total", "Total requests received")
RETRY_SUCCESS = Counter("resilient_retry_success_total", "Successful retries")
FALLBACK_USED = Counter("resilient_fallback_total", "Fallbacks triggered")
STRESSOR_TYPE = Counter("resilient_stressor_type_total", "Stressor type triggered", ["type"])
LATENCY_HISTOGRAM = Histogram("resilient_latency_seconds", "Latency injected by chaos")

# Adding structured logging
logger = logging.getLogger("locust_logger")
logger.setLevel(logging.INFO)

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(extra)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

#Separate Outcomes
#logger.info("Naive response", extra={"status": naive_response.status_code, "payload":payload})
#logger.info("Resilient response", extra={"status": resilient_response.status_code, "payload":payload})

app = Flask(__name__)

# Simulated fragile dependency with stressors
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def fragile_operation(value):
    stressor = random.choice(["timeout", "latency", "failure", "none"])
    STRESSOR_TYPE.labels(type=stressor).inc()

    if stressor == "timeout":
        logger.warning("Trigerred timeout", extra={"stressor": stressor, "value": value})
        raise TimeoutError("Simulated timeout")

    elif stressor == "latency":
        latency = random.uniform(0.5, 2.0)
        #print(f"[CHAOS] Triggered latency: {latency:.2f}s")
        logger.info("Triggered latency", extra={"stressor": stressor, "latency": latency, "value":value})
        LATENCY_HISTOGRAM.observe(latency)
        time.sleep(latency)

    elif stressor == "failure":
        #print("[CHAOS] Triggered failure")
        logger.error("Triggered failure", extra={"stressor": stressor, "value":value})
        raise Exception("Simulated failure")

    time.sleep(0.2)  # Base latency
    result = value * 2
    #print(f"[SUCCESS] Operation completed with result: {result}")
    logger.info("Operation succeeded", extra={"result":result, "value": value})
    return result


@app.route('/resilient-api/process', methods=['POST'])
def process_data():
    REQUEST_COUNT.inc()
    try:
        data = request.get_json(force=True)
        value = data.get("value")
        #print(f"[REQUEST] Received value: {value}")
        logger.info("Received request", extra={"value":value})
        result = fragile_operation(value)
        RETRY_SUCCESS.inc()

        if value is None or not isinstance(value, (int, float)):
            logger.warning("Invalid input", extra={"input":data})
            #print("[VALIDATION] Invalid input")
            return jsonify({"error": "Invalid input: 'value' must be a number"}), 400

        try:
            result = fragile_operation(value)
            #print("[RETRY] Operation succeeded after retry")
            logger.info("Retry succeeded", extra={"result":result})
            return jsonify({
                "result": result,
                "retries_used": True
            })
        except RetryError:
            FALLBACK_USED.inc()
            fallback_result = value * 1.5
            #print("[FALLBACK] Retry failed. Fallback result used.")
            logger.warning("Fallback used after retries failed", extra={"fallback_result":fallback_result})
            return jsonify({
                "warning": "Dependency failed after retries. Fallback used.",
                "result": fallback_result,
                "retries_used": False
            }), 200

    except Exception as e:
        #print(f"[ERROR] Unhandled exception: {str(e)}")
        logger.exception("Unhandled exception", extra={"error": str(e)})
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
