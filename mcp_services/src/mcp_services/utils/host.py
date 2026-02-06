
from urllib.parse import urlparse, urlunparse

def generate_host_id(url):

    # Extract protocol, hostname, and port
    protocol = url["protocol"]
    hostname = ".".join(url["host"])
    port = url.get("port")
    path="/".join(url["path"])
    query="&".join([f"{k}={v}" for k,v in url.get("query", {}).items()] )

    # Reverse the hostname
    reversed_hostname = ''.join(url["host"])


    if protocol == "http" and port in ("80", 80):
        port=None

    if protocol == "https" and port in ("443", 443):
        port=None



    # Construct the host_id and base_url
    if port:
        host_id = f"{reversed_hostname}{port}"
        base_url = f"{protocol}://{hostname}:{port}"
    else:
        host_id = f"{reversed_hostname}"
        base_url = f"{protocol}://{hostname}"


    # Reconstruct path with query
    path_with_query = urlunparse(("", "", path, "", query, ""))

    return host_id, base_url, path_with_query

if __name__ == "__main__":
    # Example usage
    #url= "http://www.localhost:9000/path1/path2?obj=1"
    url = {
        "protocol": "http",
        "host": [
          "host",
          "docker",
          "internal"
        ],
        "port": "9000",
        "path": [
          "add"
        ]
       # "query": {"q1":"v1", "q2":"v2"}
      }

    host_id, base_url, path = generate_host_id(url)
    print(host_id, base_url, path)
