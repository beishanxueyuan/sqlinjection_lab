import requests
import time

BASE_URL = "http://localhost:8888"

def test_endpoint(path, params, method='GET', data=None, json_data=None):
    url = f"{BASE_URL}{path}"
    try:
        if method == 'GET':
            response = requests.get(url, params=params)
        elif method == 'POST':
            if json_data:
                response = requests.post(url, json=json_data)
            else:
                response = requests.post(url, data=data)
        
        print(f"Testing {path} with {params or data or json_data}...")
        if response.status_code == 200:
            print(f"  SUCCESS: {response.json()}")
            return True
        else:
            print(f"  FAILED: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def run_verification():
    # Wait for app to be ready
    print("Waiting for app to be ready...")
    for i in range(10):
        try:
            requests.get(BASE_URL)
            break
        except:
            time.sleep(2)
    
    # Initialize DBs
    print("Initializing databases...")
    requests.get(f"{BASE_URL}/init")
    time.sleep(2)

    # MySQL Tests
    test_endpoint('/mysql/char', {'id': "1' OR '1'='1"})
    test_endpoint('/mysql/int', {'id': "1 OR 1=1"})
    test_endpoint('/mysql/like', {'username': "a' OR '1'='1"})
    test_endpoint('/mysql/orderby', {'col': "id"})

    # Postgres Tests
    test_endpoint('/postgres/char', {'id': "1"}) # Simple test, injection might need casting
    test_endpoint('/postgres/int', {'id': "1 OR 1=1"})
    test_endpoint('/postgres/orderby', {'col': "id"})
    test_endpoint('/postgres/like', {'username': "a' OR '1'='1"})

    # ClickHouse Tests
    test_endpoint('/clickhouse/int', {'id': "1 OR 1=1"})
    test_endpoint('/clickhouse/char', {'username': "admin' OR '1'='1"})
    test_endpoint('/clickhouse/orderby', {'col': "id"})
    test_endpoint('/clickhouse/like', {'username': "admin"})

    # Oracle Tests
    test_endpoint('/oracle/char', {'username': "admin' OR '1'='1"})
    test_endpoint('/oracle/int', {'id': "1 OR 1=1"})
    test_endpoint('/oracle/orderby', {'col': "id"})
    test_endpoint('/oracle/like', {'username': "admin"})

    # Input Method Tests
    print("\nTesting Input Methods...")
    # POST Form
    test_endpoint('/mysql/char', None, method='POST', data={'id': "1' OR '1'='1"})
    # JSON
    test_endpoint('/mysql/char', None, method='POST', json_data={'id': "1' OR '1'='1"})
    # Nested JSON
    test_endpoint('/mysql/char', None, method='POST', json_data={'data': {'id': "1' OR '1'='1"}})
    # URL Encoded JSON
    # data={"id":"1' OR '1'='1"} -> data=%7B%22id%22%3A%221%27%20OR%20%271%27%3D%271%22%7D
    test_endpoint('/mysql/char', None, method='POST', data={'data': '{"id": "1\' OR \'1\'=\'1"}'})

if __name__ == "__main__":
    run_verification()
