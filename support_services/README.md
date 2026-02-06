# Support Services

This project provides internal API services to support MCP (Model Context Protocol) services.

## Overview

The core of this project is a FastAPI application that exposes several endpoints to provide authentication and email functionalities.

## Features

- **Authentication Service**: Provides endpoints to get authentication provider URLs for services like Google, LinkedIn, and GitHub.
- **Email Service**: Offers a utility to generate raw email bodies in MIME format.

## API Endpoints

### Authentication

- `GET /auth/providers/{provider_name}`: Retrieves the authentication URL for the specified provider.
  - `provider_name`: The name of the authentication provider (e.g., `google`, `linkedin`, `github`).

### Email

- `POST /common/email/raw`: Generates a raw email body in MIME format, encoded in base64url.
  - **Request Body**:
    ```json
    {
      "sender": "sender@example.com",
      "recipient": "recipient@example.com",
      "subject": "Email Subject",
      "body": "This is the email body."
    }
    ```

## Getting Started

### Prerequisites

- Python 3.x
- Poetry

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jingnanzhou/aintegrator.git
   ```
2. Navigate to the `support_services` directory:
   ```bash
   cd support_services
   ```
3. Install the dependencies:
   ```bash
   pip install -e .
   ```

### Running the Service

#### Natively

1. Create a `.env` file in the root of the `support_services` directory and add the following environment variable:
   ```
   INTEGRATOR_URL=http://localhost:8000
   ```
2. Start the service:
   ```bash
   ./start.sh
   ```

The API will be available at `http://localhost:5000`.

#### Using Docker

1. Make sure you have Docker installed.
2. Create a `.env` file in the root of the `support_services` directory and add the following environment variable:
   ```
   INTEGRATOR_URL=http://localhost:8000
   ```
3. Build the Docker image:
   ```bash
   docker build -t support-services .
   ```
4. Run the Docker container:
   ```bash
   docker run --env-file .env -p 5000:5000 support-services
   ```

The API will be available at `http://localhost:5000`.
