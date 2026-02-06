from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
from datetime import datetime
from integrator.tools.tool_db_model import Application, AppKey, StagingService, McpTool
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from integrator.utils.etcd import get_etcd_client
from integrator.utils.host import generate_host_id
from sqlalchemy import select

logger = get_logger(__name__)


def backup_tools_database(sess, backup_dir, file_name):
    """Backup tools and services from database in init format"""
    try:
        # Get all tools grouped by tenant
        tools_stmt = select(McpTool)
        tools = sess.execute(tools_stmt).scalars().all()
        
        # Group tools by tenant
        tools_by_tenant = {}
        for tool in tools:
            tenant_name = tool.tenant or "default"
            if tenant_name not in tools_by_tenant:
                tools_by_tenant[tenant_name] = []
            
            # Reconstruct the service definition from document field
            service_data = {
                "name": tool.name,
                "description": tool.description,
                "tool_type": tool.tool_type  # Default transport
            }
            
            # McpTool stores service data in document field
            if tool.document:
                # Extract relevant fields from document
                if "inputSchema" in tool.document:
                    service_data["inputSchema"] = tool.document["inputSchema"]
                if "staticInput" in tool.document:
                    service_data["staticInput"] = tool.document["staticInput"]
                if "transport" in tool.document:
                    service_data["transport"] = tool.document["transport"]
            
            tools_by_tenant[tenant_name].append(service_data)
        
        # Save in initial_services.json format
        services_backup_file = os.path.join(backup_dir, file_name)
        with open(services_backup_file, "w") as f:
            json.dump(tools_by_tenant, f, indent=2)
        
        total_tools = sum(len(tools) for tools in tools_by_tenant.values())
        logger.info(f"Backed up {total_tools} tools across {len(tools_by_tenant)} tenants to {services_backup_file}")
        return services_backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup tools database: {str(e)}")
        return None

def main():
    """Main backup function for tools and services data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name=f"raw_tools_{timestamp}.json"
    backup_dir = os.path.join(os.path.dirname(__file__), f"../../backup")
  
    os.makedirs(backup_dir, exist_ok=True)

    logger.info(f"Starting tools and services backup to {backup_dir}")
    
    backup_files = []

    with get_db_cm() as sess:
        # Backup tools database
        tools_file = backup_tools_database(sess, backup_dir, file_name)
        if tools_file:
            backup_files.append(tools_file)
    
    logger.info(f"Tools and services backup completed. Files created: {backup_files}")
    return backup_files

if __name__ == "__main__":
    main()
