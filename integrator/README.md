# Project Integrator

Project Integrator is a Python-based AI integration service that provides a robust platform for managing and interacting with various AI services. It is built with FastAPI and offers a comprehensive suite of features, including service registration, deletion, and metadata management.

## Key Features

- **Service Management**: Easily register, delete, and retrieve AI services.
- **Authentication and Authorization**: Secure your services with built-in IAM and OAuth2 support.
- **Centralized Logging**: Monitor and debug your services with a centralized logging system.
- **API Consumption**: A dedicated client for consuming registered APIs.
- **Staging Environment**: Test and validate services in a staging environment before publishing.

## Project Structure

The project is organized into the following key modules:

- **`apis`**: The main FastAPI application, which orchestrates the different services.
- **`iam`**: Handles Identity and Access Management, including user authentication and authorization.
- **`publish`**: Manages the lifecycle of AI services, including registration, deletion, and retrieval.
- **`staging`**: Provides a staging environment for testing and validating services.
- **`clients`**: Includes a client for consuming registered APIs.
- **`logs`**: A centralized logging service for monitoring and debugging.
- **`utils`**: A collection of utility functions for database connections, cryptography, and more.

## Getting Started

### Prerequisites

- Python 3.8+
- Docker
- `pip` for package management

### Installation

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/jingnanzhou/aintegrator.git
    cd aintegrator
    ```

2.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Set up environment variables**:

    Create a `.env` file in the root directory and add the required environment variables. You can use the `.env.example` file as a template.

2.  **Start the application**:

    ```bash
    python src/integrator/apis/api_server.py
    ```

    The application will be available at `http://localhost:6060`.

## API Endpoints

The following API endpoints are available:

- **`/mcp`**: For managing MCP services.
- **`/staging`**: For staging and validating services.
- **`/users`**: For user management and authentication.
- **`/oauth`**: For OAuth2-based authentication.
- **`/logs`**: For accessing application logs.
- **`/client`**: For consuming registered APIs.

For detailed API documentation, please refer to the OpenAPI specification available at `http://localhost:6060/docs`.

## Running with Docker

You can also run the application using Docker:

1.  **Build the Docker image**:

    ```bash
    docker build -t integrator .
    ```

2.  **Run the Docker container**:

    ```bash
    docker run -p 6060:6060 integrator
    ```

## Testing

To run the test suite, use `pytest`:

```bash
pytest
