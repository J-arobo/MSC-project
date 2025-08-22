This system uses tenacity for retry logic and simulate a fragile dependency


1. Functional testing 
curl -X POST http://localhost:5002/resilient-api/process \
     -H "Content-Type: application/json" \
     -d '{"value": 10}'


2. Resislience Testing
for i in {1..20}; do
  curl -s -X POST http://localhost:5002/resilient-api/process \
       -H "Content-Type: application/json" \
       -d '{"value": 10}' | jq
done


3. Chaos & Stress Testing
pushng the system to its limits:
 3.1 Chaos Testing: Amplifying internaL Stressors
 our app already simulates:
 - Timeouts(TimeoutError)
 - Variable (time.sleep(random.unifrom(...)))
 - Random failures (raise Exception(...))
To intensify chaos:
- Increase failure probabilities temporarily:
    if random.random() < 0.7:  # instead of 0.3
    raise TimeoutError("Simulated timeout")
- adding new failure types:
    if random.random() < 0.2:
    raise MemoryError("Simulated memory spike")

    3.2 Stress Testing: External Load Simulation
    Using locust to simulate high traffic and traffic concurrent requests:

    To run:
    bash: "locust -f locustfile.py --host=http://localhost:5002"
    then on browser open:"http://localhost:8089" - to control load







"
to run: docker-compose up --build

to tear down: docker-compose down
""