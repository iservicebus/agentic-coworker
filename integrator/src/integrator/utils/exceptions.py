"""
Custom exceptions for the integrator application.
"""


class DuplicateToolError(Exception):
    """
    Exception raised when attempting to create a tool that already exists.
    
    This exception is raised when a tool with the same name and tenant
    already exists in the database, indicating a duplicate entry conflict.
    
    Attributes:
        message: Explanation of the error
        tool_name: Name of the duplicate tool
        tenant: Tenant name where the duplicate exists
        existing_id: ID of the existing tool (if available)
    """
    
    def __init__(self, message: str, tool_name: str = None, tenant: str = None, existing_id: str = None):
        """
        Initialize the DuplicateToolError.
        
        Args:
            message: Error message describing the duplicate
            tool_name: Name of the tool that is duplicated
            tenant: Tenant name where the duplicate exists
            existing_id: ID of the existing tool
        """
        self.message = message
        self.tool_name = tool_name
        self.tenant = tenant
        self.existing_id = existing_id
        super().__init__(self.message)
    
    def __str__(self):
        """Return a string representation of the error."""
        return self.message
