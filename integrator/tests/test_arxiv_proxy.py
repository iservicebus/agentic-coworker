import httpx, json
from urllib.parse import urlencode

headers = {
    "Host": "export.arxiv.org"
}




client = httpx.Client()
url="http://localhost/default-exportarxivorg443/api/query?search_query=all:quantum+computing&start=0&max_results=3"

response = client.request(
            method="get",
            url=url,
            headers=headers,
        )

print(f"Response Status Code: {response.status_code}")

if response.status_code == 200:
    try:
        # Parse the JSON response
        received_data = response.text
        print("Received data:", received_data)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
else:
    print("Error: Request failed.")
    print("Response Text:")
    print(response.text)

# You might want to add assertions here for automated testing, e.g.:
# assert response.status_code == 200
# assert "expected_tool_name" in tool_names
