import requests
import time
import datetime

# URL to query
url = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/valenbisi-disponibilitat-valenbisi-dsiponibilidad/records?select=number%2C%20available%2C%20free%2C%20total%2Cupdated_at&where=update_jcd%3A%20%5B%272025%2F11%2F12%27%20TO%20%272025%2F12%2F13%27%5D&order_by=number&limit=-1"

# Calculate end time (7 days from start)
start_time = time.time()
end_time = start_time + 7 * 24 * 60 * 60  # 7 days in seconds

while time.time() < end_time:
    now = datetime.datetime.now()
    # Get the JSON data from the URL
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['total_count'] > len(data['results']):
            for offset in range(100, data['total_count'], 100):
                paged_url = url + f"&offset={offset}"
                paged_response = requests.get(paged_url)
                paged_response.raise_for_status()
                paged_data = paged_response.json()
                data['results'].extend(paged_data['results'])
        # Save to a file with timestamp
        filename = now.strftime("valenbisi_%Y%m%d_%H%M.json")
        with open(filename, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Failed to get data: {e}")

    # Sleep for an 10 minutes (600 seconds)
    time.sleep(600)


