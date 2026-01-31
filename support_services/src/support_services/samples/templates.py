from fastapi import HTTPException, Body, Query, Path, Depends, Request, APIRouter, Response, Form, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn

from support_services.utils.logger import get_logger
from support_services.utils.oauth import validate_token

# Initialize logger for this module
logger = get_logger(__name__)

sample_router = APIRouter(
    prefix="/samples", 
    tags=["Sample APIs"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        500: {"description": "Internal server error"}
    }
)

auth_scheme = HTTPBearer()

def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """
    Verify authentication credentials.
    
    Args:
        credentials: Bearer token credentials
        
    Raises:
        HTTPException: If credentials are invalid
    """
    if credentials.credentials != "your_token_here":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Response Models
class TextDataResponse(BaseModel):
    """Response model for text data processing"""
    header_received: str = Field(..., description="The custom header value received")
    query_param: Optional[str] = Field(None, description="The query parameter value")
    text_content: str = Field(..., description="The processed text content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "header_received": "custom-value",
                "query_param": "google",
                "text_content": "Sample text content"
            }
        }

class BinaryDataResponse(BaseModel):
    """Response model for binary data processing"""
    header_received: str = Field(..., description="The custom header value received")
    query_param: Optional[str] = Field(None, description="The query parameter value")
    binary_size_bytes: int = Field(..., description="Size of the binary data in bytes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "header_received": "custom-value",
                "query_param": "test",
                "binary_size_bytes": 1024
            }
        }

class FormDataResponse(BaseModel):
    """Response model for form data processing"""
    header_received: str = Field(..., description="The custom header value received")
    query_param: Optional[str] = Field(None, description="The query parameter value")
    form_data: Dict[str, Any] = Field(..., description="The processed form data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "header_received": "custom-value",
                "query_param": "test",
                "form_data": {
                    "name": "John Doe",
                    "age": 30
                }
            }
        }

class GreetInput(BaseModel):
    """Input model for greeting request"""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the person to greet")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe"
            }
        }

class GreetResponse(BaseModel):
    """Response model for greeting"""
    message: str = Field(..., description="Personalized greeting message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello, John Doe!"
            }
        }

@sample_router.post(
    "/text-data",
    summary="Process Text Data with Authentication",
    description="""
    Process incoming text data with custom headers and query parameters.
    
    This endpoint demonstrates how to:
    - Handle raw text data in request body
    - Process custom headers
    - Handle optional query parameters
    - Implement bearer token authentication
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    """,
    response_model=TextDataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Text data processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "header_received": "custom-value",
                        "query_param": "google",
                        "text_content": "Sample text content"
                    }
                }
            }
        },
        400: {"description": "Bad request - Invalid input data"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"}
    }
)
async def receive_text_data(
    request: Request,
    x_custom_header: str = Header(..., description="Custom header value for request identification"),
    q: Optional[str] = Query(
        None, 
        description="Optional query parameter for additional context (e.g., provider name like 'google', 'linkedin', 'github')",
        example="google"
    ),
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth),
) -> TextDataResponse:
    """
    Process text data from request body along with custom headers and query parameters.
    
    Args:
        request: FastAPI request object containing the raw body
        x_custom_header: Custom header value for request identification
        q: Optional query parameter for additional context
        credentials: Bearer token authentication credentials
        
    Returns:
        TextDataResponse: Processed text data with metadata
        
    Raises:
        HTTPException: If authentication fails or request is malformed
    """
    try:
        body = await request.body()
        text = body.decode("utf-8")
        
        logger.info(f"Received request for /text-data:")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body: {text}")
        
        return TextDataResponse(
            header_received=x_custom_header,
            query_param=q,
            text_content=text
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must contain valid UTF-8 text"
        )
    except Exception as e:
        logger.error(f"Error processing text data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing text data"
        )

@sample_router.post(
    "/binary-data",
    summary="Process Binary Data with Authentication",
    description="""
    Process incoming binary data with custom headers and query parameters.
    
    This endpoint demonstrates how to:
    - Handle raw binary data in request body
    - Process custom headers
    - Handle optional query parameters
    - Implement bearer token authentication
    - Log binary data size without exposing content
    
    **Authentication Required**: Bearer token must be provided in Authorization header.
    """,
    response_model=BinaryDataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Binary data processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "header_received": "custom-value",
                        "query_param": "test",
                        "binary_size_bytes": 1024
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing authentication token"}
    }
)
async def receive_binary_data(
    request: Request,
    x_custom_header: str = Header(..., description="Custom header value for request identification"),
    q: Optional[str] = Query(None, description="Optional query parameter for additional context"),
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth),
) -> BinaryDataResponse:
    """
    Process binary data from request body along with custom headers and query parameters.
    
    Args:
        request: FastAPI request object containing the raw binary body
        x_custom_header: Custom header value for request identification
        q: Optional query parameter for additional context
        credentials: Bearer token authentication credentials
        
    Returns:
        BinaryDataResponse: Binary data metadata with size information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        body = await request.body()
        
        logger.info(f"Received request for /binary-data:")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body size: {len(body)} bytes")
        
        return BinaryDataResponse(
            header_received=x_custom_header,
            query_param=q,
            binary_size_bytes=len(body)
        )
    except Exception as e:
        logger.error(f"Error processing binary data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing binary data"
        )

@sample_router.post(
    "/form-data",
    summary="Process Form Data",
    description="""
    Process incoming form data with custom headers and query parameters.
    
    This endpoint demonstrates how to:
    - Handle form-encoded data (application/x-www-form-urlencoded)
    - Process multiple form fields with different data types
    - Process custom headers
    - Handle optional query parameters
    
    **Note**: This endpoint does not require authentication for demonstration purposes.
    """,
    response_model=FormDataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Form data processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "header_received": "custom-value",
                        "query_param": "test",
                        "form_data": {
                            "name": "John Doe",
                            "age": 30
                        }
                    }
                }
            }
        },
        422: {"description": "Validation error - Invalid form data"}
    }
)
async def receive_form_data(
    request: Request,
    name: str = Form(..., description="User's name", example="John Doe"),
    age: int = Form(..., description="User's age", ge=0, le=150, example=30),
    x_custom_header: str = Header(..., description="Custom header value for request identification"),
    q: Optional[str] = Query(None, description="Optional query parameter for additional context"),
) -> FormDataResponse:
    """
    Process form data along with custom headers and query parameters.
    
    Args:
        request: FastAPI request object
        name: User's name from form data
        age: User's age from form data (must be between 0 and 150)
        x_custom_header: Custom header value for request identification
        q: Optional query parameter for additional context
        
    Returns:
        FormDataResponse: Processed form data with metadata
        
    Raises:
        HTTPException: If form validation fails
    """
    try:
        form_content = {"name": name, "age": age}
        
        logger.info(f"Received request for /form-data:")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Form data: {form_content}")
        
        return FormDataResponse(
            header_received=x_custom_header,
            query_param=q,
            form_data=form_content
        )
    except Exception as e:
        logger.error(f"Error processing form data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing form data"
        )

@sample_router.post(
    "/greet",
    summary="Generate Personalized Greeting",
    description="""
    Generate a personalized greeting message for a given name.
    
    This endpoint demonstrates how to:
    - Handle JSON request body with Pydantic models
    - Validate input data
    - Return structured JSON responses
    - Log request details for monitoring
    
    **Note**: This endpoint does not require authentication for demonstration purposes.
    """,
    response_model=GreetResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Greeting generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Hello, John Doe!"
                    }
                }
            }
        },
        422: {"description": "Validation error - Invalid input data"}
    }
)
async def greet(
    request: Request, 
    data: GreetInput
) -> GreetResponse:
    """
    Generate a personalized greeting message.
    
    Args:
        request: FastAPI request object for logging purposes
        data: Input data containing the name to greet
        
    Returns:
        GreetResponse: Personalized greeting message
        
    Raises:
        HTTPException: If input validation fails
    """
    try:
        logger.info(f"Received request for /greet:")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body: {data.model_dump()}")
        
        return GreetResponse(message=f"Hello, {data.name}!")
    except Exception as e:
        logger.error(f"Error generating greeting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating greeting"
        )
