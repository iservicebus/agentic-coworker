
from urllib.parse import urlparse, urlunparse

def parse_url_to_structure(url_string):
    """
    Parse a typical URL string into the data structure required by generate_host_id.
    
    Args:
        url_string (str): A URL string like "http://www.localhost:9000/path1/path2?obj=1"
    
    Returns:
        dict: A dictionary with the structure:
            {
                "protocol": str,
                "host": list[str],
                "port": str (optional),
                "path": list[str],
                "query": dict (optional)
            }
    
    Example:
        >>> parse_url_to_structure("http://www.localhost:9000/path1/path2?obj=1")
        {
            "protocol": "http",
            "host": ["www", "localhost"],
            "port": "9000",
            "path": ["path1", "path2"],
            "query": {"obj": "1"}
        }
    """
    parsed = urlparse(url_string)
    
    # Extract protocol (scheme)
    protocol = parsed.scheme if parsed.scheme else "http"
    
    # Extract hostname parts (keep original order, do not reverse)
    hostname = parsed.hostname if parsed.hostname else parsed.netloc.split(':')[0]
    host_parts = hostname.split('.')
    
    # Extract port
    port = str(parsed.port) if parsed.port else None
    
    # Extract path parts (filter out empty strings)
    path_parts = [part for part in parsed.path.split('/') if part]
    
    # Extract query parameters
    query_dict = {}
    if parsed.query:
        query_pairs = parsed.query.split('&')
        for pair in query_pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                query_dict[key] = value
            else:
                query_dict[pair] = ''
    
    # Build the result structure
    result = {
        "protocol": protocol,
        "host": host_parts,
        "path": path_parts
    }
    
    # Add optional fields only if they exist
    if port:
        result["port"] = port
    if query_dict:
        result["query"] = query_dict
    
    return result

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

def generate_host_id_from_url(url_string):
    """
    Convenience function to generate host_id, base_url, and path directly from a URL string.
    
    This function combines parse_url_to_structure and generate_host_id into a single call.
    
    Args:
        url_string (str): A URL string like "http://www.localhost:9000/path1/path2?obj=1"
    
    Returns:
        tuple: (host_id, base_url, path_with_query)
            - host_id (str): The generated host identifier
            - base_url (str): The base URL (protocol + hostname + port if non-standard)
            - path_with_query (str): The path with query parameters
    
    Example:
        >>> generate_host_id_from_url("http://www.localhost:9000/path1/path2?obj=1")
        ('localhostwww9000', 'http://www.localhost:9000', 'path1/path2?obj=1')
    """
    url_structure = parse_url_to_structure(url_string)
    return generate_host_id(url_structure)

if __name__ == "__main__":
    # Example usage with the new convenience function
    url_string = "http://www.localhost:9000/path1/path2?obj=1"
    
    print("=" * 60)
    print("Testing generate_host_id_from_url (convenience function):")
    print("=" * 60)
    print(f"Input URL: {url_string}")
    host_id, base_url, path = generate_host_id_from_url(url_string)
    print(f"Host ID: {host_id}")
    print(f"Base URL: {base_url}")
    print(f"Path: {path}")
    print()
    
    print("=" * 60)
    print("Testing parse_url_to_structure:")
    print("=" * 60)
    print(f"Input URL: {url_string}")
    url_structure = parse_url_to_structure(url_string)
    print(f"Parsed structure: {url_structure}")
    print()
    
    print("=" * 60)
    print("Testing generate_host_id with parsed structure:")
    print("=" * 60)
    host_id, base_url, path = generate_host_id(url_structure)
    print(f"Host ID: {host_id}")
    print(f"Base URL: {base_url}")
    print(f"Path: {path}")
    print()
    
    # Original example
    print("=" * 60)
    print("Testing with original structure:")
    print("=" * 60)
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
    print(f"Host ID: {host_id}")
    print(f"Base URL: {base_url}")
    print(f"Path: {path}")
