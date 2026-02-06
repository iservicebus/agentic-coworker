import logging
import uuid, json
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.sql import bindparam
from integrator.tools.tool_db_model import  AppKey, Application, McpTool, ToolSkill, StagingService, CapabilityTool, Skill, CapabilitySkill, ToolRel
from integrator.domains.domain_llm import normalize_tool
from integrator.domains.domain_db_model import Domain, Capability, DomainCapability
from integrator.iam.iam_db_model import Role, RoleAgent, RoleDomain
from integrator.utils.exceptions import DuplicateToolError
from integrator.utils.host import generate_host_id
from typing import Dict , Any, List, Optional, Union
import numpy as np
logger = logging.getLogger(__name__)


def serialize_for_jsonb(data: Any) -> Any:
    """
    Recursively serialize data to make it JSON-compatible for JSONB storage.
    Converts UUID objects to strings and handles nested dictionaries and lists.
    
    Args:
        data: The data to serialize
        
    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, dict):
        return {key: serialize_for_jsonb(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_for_jsonb(item) for item in data]
    elif isinstance(data, (datetime,)):
        return data.isoformat()
    else:
        return data



def get_app_by_app_name_and_tenant_name(sess, app_name: str, tenant_name: str) -> Optional[Application]:
    """
    Retrieve an application by its app_name and tenant_name (composite PK).
    
    Args:
        sess: SQLAlchemy session
        app_name: The name of the application
        tenant_name: The tenant name
        
    Returns:
        Optional[Application]: The application if found, None otherwise
    """
    try:
        application = sess.execute(
            select(Application).where(
                Application.app_name == app_name,
                Application.tenant_name == tenant_name
            )
        ).scalar_one_or_none()
        
        if application:
            logger.info(f"Retrieved application with app_name: {app_name}, tenant_name: {tenant_name}")
        else:
            logger.warning(f"Application not found with app_name: {app_name}, tenant_name: {tenant_name}")
        return application
    except Exception as e:
        logger.error(f"Error retrieving application by app_name {app_name} and tenant_name {tenant_name}: {str(e)}")
        raise

    
def upsert_application(sess, app_data, tenant_name, tool_id = None, old_tool_url = None):

    if app_data.get("protocol"):
        app_name, _, _ = generate_host_id(app_data)
        tool_url=app_data
    elif app_data.get("app_name"):
        app_name=app_data.get("app_name")
        tool_url=app_data.get("app_note") 
    else:
        tool_url=app_data       

    if not app_name:
        logger.warning("Skipping application with no app_name.")
        return
    application = sess.execute(
        select(Application).where(
            Application.app_name == app_name,
            Application.tenant_name == tenant_name
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    
    # Convert tool_url dict to JSON string for TEXT column
    app_note_text = json.dumps(tool_url) if isinstance(tool_url, dict) else tool_url
    
    if not application:
        application = Application(
            app_name=app_name,
            tenant_name=tenant_name,
            app_note=app_note_text,
            created_at=now,
            updated_at=now
        )
        sess.add(application)
        logger.info(f"Inserted new application: {app_name} for tenant: {tenant_name}")
    else:
        application.app_note = app_note_text
        application.updated_at = now
        logger.info(f"Updated existing application: {app_name} for tenant: {tenant_name}")
    sess.flush()

    if tool_id:
        insert_application_mcp_tool(sess, app_name, tenant_name, tool_id)

    if old_tool_url:
        old_app_name, _, _=generate_host_id(old_tool_url)

        if old_app_name and old_app_name != app_name:
            delete_application_mcp_tool(sess, tool_id, tenant_name, old_app_name)




def upsert_app_key(sess, secret_data, app_name, agent_id, tenant_name):
    app_key = sess.execute(
        select(AppKey).where(
            (AppKey.app_name == app_name) &
            (AppKey.agent_id == agent_id) &
            (AppKey.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not app_key:
        app_key = AppKey(
            app_name=app_name,
            agent_id=agent_id,
            tenant_name=tenant_name,
            secrets=secret_data["secrets"],
            created_at=now,
            updated_at=now
        )
        sess.add(app_key)
        logger.info(f"Inserted new service secret for app: {app_name}")
    else:
        app_key.secrets = secret_data["secrets"]
        app_key.updated_at = now
        logger.info(f"Updated service secret for app: {app_name}")



def get_mcp_tool_by_id(sess, tool_id: str) -> Optional[McpTool]:
    """
    Retrieve  mcp tool by its ID.
    
    Args:
        sess: SQLAlchemy session
        tool_id: The ID of the mcp tool
        
    Returns:
        Optional[McpTool]: The mcp tool if found, None otherwise
    """
    try:

        # Convert string to UUID if necessary
        if isinstance(tool_id, str):
            tool_uuid = uuid.UUID(tool_id)
        else:
            tool_uuid = tool_id
            
        tool = sess.execute(
            select(McpTool).where(McpTool.id == tool_uuid)
        ).scalar_one_or_none()
                
        
        if tool:
            logger.info(f"Retrieved mcp tool with ID: {tool_id}")
        else:
            logger.warning(f"mcp tool not found with ID: {tool_id}")
        return tool
    except Exception as e:
        logger.error(f"Error retrieving mcp tool by ID {tool_id}: {str(e)}")
        raise


def get_mcp_tool_by_name_tenant(sess, tool_name: str, tenant: str) -> Optional[McpTool]:
    """
    Retrieve mcp tool by its name and tenant (respecting unique constraint).
    
    Args:
        sess: SQLAlchemy session
        tool_name: The name of the mcp tool
        tenant: The tenant name
        
    Returns:
        Optional[McpTool]: The mcp tool if found, None otherwise
    """
    try:
        tool = sess.execute(
            select(McpTool).where(
                McpTool.name == tool_name,
                McpTool.tenant == tenant
            )
        ).scalar_one_or_none()
        
        if tool:
            logger.info(f"Retrieved mcp tool with name: {tool_name}, tenant: {tenant}")
        else:
            logger.warning(f"mcp tool not found with name: {tool_name}, tenant: {tenant}")
        return tool
    except Exception as e:
        logger.error(f"Error retrieving mcp tool by name {tool_name} and tenant {tenant}: {str(e)}")
        raise


def check_duplicate_tool(sess, tool_name: str, tenant: str, tool_id: Optional[uuid.UUID] = None) -> None:
    """
    Check if there's a duplicate tool with the same name and tenant.
    
    Args:
        sess: SQLAlchemy session
        tool_name: The name of the tool to check
        tenant: The tenant name
        tool_id: Optional tool ID to compare against
        
    Raises:
        DuplicateToolError: If a duplicate tool is found
    """
    try:
        existing_tool = sess.execute(
            select(McpTool).where(
                McpTool.name == tool_name,
                McpTool.tenant == tenant
            )
        ).scalar_one_or_none()
        
        if existing_tool:
            if tool_id is None:
                # If no tool_id provided and tool exists, it's a duplicate
                error_msg = f"Duplicate tool name '{tool_name}' and tenant '{tenant}' already exists. Existing ID: {existing_tool.id}"
                logger.error(error_msg)
                raise DuplicateToolError(
                    message=error_msg,
                    tool_name=tool_name,
                    tenant=tenant,
                    existing_id=str(existing_tool.id)
                )
            elif existing_tool.id != tool_id:
                # If tool_id provided but different from existing, it's a duplicate
                error_msg = f"Duplicate tool name '{tool_name}' and tenant '{tenant}' exists with different ID. Input ID: {tool_id}, Existing ID: {existing_tool.id}"
                logger.error(error_msg)
                raise DuplicateToolError(
                    message=error_msg,
                    tool_name=tool_name,
                    tenant=tenant,
                    existing_id=str(existing_tool.id)
                )
        
    except DuplicateToolError:
        # Re-raise DuplicateToolError as-is
        raise
    except Exception as e:
        logger.error(f"Error checking for duplicate tool {tool_name} and tenant {tenant}: {str(e)}")
        raise



def upsert_tool(etcd_client, sess, emb, llm,  mcp_tool: dict, tenant: str, canonical_data=None) -> tuple[bool, McpTool]:
    # Input validation
    
    tool_name = mcp_tool.get("name")
    tool_description = mcp_tool.get("description")
    tool_input_schema = mcp_tool.get("inputSchema", {})
    tool_id = mcp_tool.get("id")  # Get the ID if provided
    tool_type = mcp_tool.get("tool_type", "general")  # Get tool_type with default "general"
    #ensure app name is consistent
    tool_url = mcp_tool.get("staticInput", {}).get("url")
    new_app_name, _, _ = generate_host_id(tool_url)
    if new_app_name: 
        mcp_tool["appName"] = new_app_name

    old_tool_url=None
    tool_by_id=None
    tool_by_name_tenant=None

    if tool_id:
        tool_by_id=get_mcp_tool_by_id(sess, tool_id)

        try:
            # Convert string to UUID if necessary
            if isinstance(tool_id, str):
                tool_id = uuid.UUID(tool_id)
        except:
            tool_id=None

    # Also check for existing tool by name and tenant (due to unique constraint)
    if tool_name and tenant:
        tool_by_name_tenant = sess.execute(
            select(McpTool).where(
                McpTool.name == tool_name,
                McpTool.tenant == tenant
            )
        ).scalar_one_or_none()

    update = False    
    try:
        # Check for duplicate tool conflicts using the dedicated function
        check_duplicate_tool(sess, tool_name, tenant, tool_id)
        
        if not canonical_data:
            canonical_data = normalize_tool(llm, tool_name, tool_description, tool_input_schema)
       
        # Determine which tool to use for update
        if tool_by_id and tool_by_name_tenant:
            # Both exist - they should be the same tool (no conflict case handled above)
            existing_tool = tool_by_id
        elif tool_by_id:
            # Only found by ID
            existing_tool = tool_by_id
        elif tool_by_name_tenant:
            # Only found by name+tenant
            existing_tool = tool_by_name_tenant
        else:
            # Neither exists
            existing_tool = None
        
        if not existing_tool:
            # Create new tool
            tool = McpTool(
                name=tool_name,
                description=tool_description,
                embedding=emb.encode(tool_description),
                document=mcp_tool,
                tenant=tenant,
                tool_type=tool_type,
                canonical_data=canonical_data,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            if tool_id:
                tool.id=tool_id
            else:

                new_id = uuid.uuid4()
                tool.id=new_id
                tool.document["id"]=str(new_id)
                    
            sess.add(tool)
            sess.flush()
            update=False
            logger.info(f"Inserted new mcp tool {tool_name}")

        else:

            # Update existing tool
            tool = existing_tool
            old_name = tool.name
            old_tenant = tool.tenant
            old_tool_url=tool.document.get("staticInput", {}).get("url")
            # If the name or tenant is changing, delete all existing tool operations first
            # The tool ingestion process will recreate them anyway
            if old_name != tool_name or old_tenant != tenant:
                logger.info(f"Tool name/tenant changing from '{old_name}/{old_tenant}' to '{tool_name}/{tenant}', deleting existing tool operations")
                from integrator.tools.tool_etcd_crud import delete_service_metadata
                delete_service_metadata(etcd_client, sess, tool.id, old_tenant, None, None)

                from sqlalchemy import delete
                delete_stmt = delete(ToolSkill).where(ToolSkill.tool_id == tool.id)
                result = sess.execute(delete_stmt)
                deleted_count = result.rowcount
                logger.info(f"Deleted {deleted_count} existing tool skills for tool_id '{tool.id}'")
                
                # Flush the deletion before updating the tool
                sess.flush()
            
            # Now update the tool itself
            tool.name = tool_name
            tool.description = tool_description
            tool.embedding = emb.encode(tool_description)
            tool.document = mcp_tool
            tool.canonical_data = canonical_data
            tool.tenant = tenant  # Update tenant in case it changed
            tool.tool_type = tool_type  # Update tool_type
            tool.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Updated existing mcp tool {tool_name} (ID: {tool.id})")
            update=True

        upsert_application(sess, tool_url, tool.tenant,tool.id, old_tool_url)
        return (update, tool)        
    except Exception as e:
        logger.error(f"Failed to upsert tool, error: {str(e)}")
        raise


def insert_capability_tools(sess, capability_name, tools: List[McpTool]):
    """
    Insert many-to-many relationships between a capability and a list of tools using the CapabilityTool model.

    This function assumes the capability already exists in the `capabilities` table and
    validates that `capability_name` matches an existing `Capability.name` before
    inserting relationships. If the capability does not exist, a ValueError is raised
    instead of relying on the database to throw a foreign key error.
    
    Note: Requires tenant_name to be added to CapabilityTool composite PK.
    """

    try:
        # Validate that the capability exists to avoid FK violations later
        capability = sess.execute(
            select(Capability).where(Capability.name == capability_name)
        ).scalar_one_or_none()
        if not capability:
            error_msg = (
                f"Capability '{capability_name}' does not exist in capabilities table; "
                "cannot create capability_tool relationships."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get tenant_name from the capability
        tenant_name = capability.tenant_name

        # Then insert the new capability-tool relationships
        for tool in tools:
            try:
                existing_capability_tool = sess.execute(
                    select(CapabilityTool).where(
                        CapabilityTool.tool_id == tool.id,
                        CapabilityTool.capability_name == capability_name,
                        CapabilityTool.tenant_name == tenant_name
                    )
                ).scalar_one_or_none()
        
                if not existing_capability_tool:
                    capability_tool = CapabilityTool(
                        tool_id=tool.id,
                        capability_name=capability_name,
                        tenant_name=tenant_name
                    )
                    sess.add(capability_tool)
                logger.info(
                    f"Inserted new capability and tool relation, "
                    f"capability_name={capability_name}, tool_id={tool.id}, tenant_name={tenant_name}"
                )
            except Exception as e:
                logger.error(f"Failed to capability_tool ({tool.id}, {capability_name}, {tenant_name}): {e}")
        
        # Flush all changes at once
        sess.flush()
        logger.info(
            f"Successfully updated capability tool for capability_name={capability_name}: "
            f"{len(tools)} tools"
        )
        
    except Exception as e:
        logger.error(f"Failed to update capability tool relationship for capability_name={capability_name}: {e}")
        raise


def check_tool_has_capability(sess, tool: Union[McpTool, str, uuid.UUID]) -> bool:
    """
    Check if an MCP tool has any capability.
    
    This function checks the CapabilityTool association table to determine if
    the tool has at least one capability relationship.
    
    Args:
        sess: SQLAlchemy session
        tool: The tool to check. Can be:
            - McpTool instance
            - tool_id as string (UUID format)
            - tool_id as UUID
        
    Returns:
        bool: True if the tool has at least one capability, False otherwise
        
    Raises:
        ValueError: If invalid tool identifier provided
    """
    try:
        # Determine the tool_id based on input type
        if isinstance(tool, McpTool):
            tool_id = tool.id
        elif isinstance(tool, str):
            try:
                tool_id = uuid.UUID(tool)
            except ValueError:
                # Assume it's a tool name, need tenant to look it up
                raise ValueError(
                    f"String tool identifier must be a valid UUID. "
                    f"Use get_mcp_tool_by_name_tenant() first if you have a tool name."
                )
        elif isinstance(tool, uuid.UUID):
            tool_id = tool
        else:
            raise ValueError(
                f"Invalid tool type: {type(tool)}. "
                f"Expected McpTool, str (UUID), or uuid.UUID"
            )
        
        # Check if any capability-tool relationship exists for this tool
        row = sess.execute(
            select(CapabilityTool.tool_id)
            .where(CapabilityTool.tool_id == tool_id)
            .limit(1)
        ).first()
        
        has_capability = row is not None
        
        logger.info(
            f"Tool {tool_id} {'has' if has_capability else 'does not have'} "
            f"any capability"
        )
        
        return has_capability
        
    except Exception as e:
        logger.error(
            f"Error checking if tool has any capability: {str(e)}"
        )
        raise


def get_tools_by_capability_name(sess, capability_name: str, tenant_name: str = None) -> List[McpTool]:
    """Retrieve all MCP tools associated with a given capability name with optional tenant filtering.

    This uses the CapabilityTool association table to find all tools that
    are linked to the provided capability_name.

    Args:
        sess: SQLAlchemy session
        capability_name: Name of the capability to filter tools by
        tenant_name: Optional tenant name for filtering

    Returns:
        List[McpTool]: List of MCP tools associated with the capability
    """
    try:
        query = (
            select(McpTool)
            .join(CapabilityTool, CapabilityTool.tool_id == McpTool.id)
            .where(CapabilityTool.capability_name == capability_name)
        )
        
        if tenant_name:
            query = query.where(McpTool.tenant == tenant_name)
        
        tools = sess.execute(query).scalars().all()
        
        logger.info(
            f"Retrieved {len(tools)} tools for capability_name={capability_name}"
            + (f", tenant={tenant_name}" if tenant_name else "")
        )
        return tools
    except Exception as e:
        logger.error(
            f"Failed to retrieve tools for capability_name={capability_name}: {e}"
        )
        raise


def upsert_tool_rel(sess, tenant: str, relation_data: Dict[str, Any]) -> ToolRel:
    """Insert or update a tool relationship (edge) between two MCP tools.

    The input ``relation_data`` is expected to look like::

        {
            "tool_flow": [
                "list_github_organizations",  # source tool name
                "get_github_organization_by_id",  # target tool name
            ],
            "field_mapping": [...],
            "composite_intent": "...",
        }

    The first tool name is treated as the *source* and the second as the *target*.
    Both tools are looked up in the same tenant. If a row already exists for the
    (source_tool_id, target_tool_id) pair, this function updates its
    ``composite_intent`` and ``field_mapping``; otherwise it inserts a new row.
    """
    tool_flow = relation_data.get("tool_flow") or []
    if len(tool_flow) < 2:
        raise ValueError("tool_flow must contain at least two tool names [source, target]")

    source_name, target_name = tool_flow[0], tool_flow[1]

    # Look up tools by name + tenant
    source_tool = get_mcp_tool_by_name_tenant(sess, source_name, tenant)
    if not source_tool:
        raise ValueError(
            f"Source tool '{source_name}' not found for tenant '{tenant}'"
        )

    target_tool = get_mcp_tool_by_name_tenant(sess, target_name, tenant)
    if not target_tool:
        raise ValueError(
            f"Target tool '{target_name}' not found for tenant '{tenant}'"
        )

    composite_intent = relation_data.get("composite_intent")
    field_mapping = relation_data.get("field_mapping")

    try:
        existing = sess.execute(
            select(ToolRel).where(
                ToolRel.source_tool_id == source_tool.id,
                ToolRel.target_tool_id == target_tool.id,
            )
        ).scalar_one_or_none()

        if existing:
            existing.composite_intent = composite_intent
            existing.field_mapping = field_mapping
            relation = existing
            logger.info(
                "Updated tool relationship: %s -> %s (tenant=%s)",
                source_name,
                target_name,
                tenant,
            )
        else:
            relation = ToolRel(
                source_tool_id=source_tool.id,
                target_tool_id=target_tool.id,
                composite_intent=composite_intent,
                field_mapping=field_mapping,
            )
            sess.add(relation)
            logger.info(
                "Inserted tool relationship: %s -> %s (tenant=%s)",
                source_name,
                target_name,
                tenant,
            )

        sess.flush()
        return relation
    except Exception as e:
        logger.error(
            "Failed to upsert tool relationship %s -> %s (tenant=%s): %s",
            source_name,
            target_name,
            tenant,
            e,
        )
        raise


from typing import Iterable, Tuple  # you already import Dict, Any, List, Optional, Union

def find_skill_by_tool_chain(
    sess,
    tool_chain: List[Any],
    tenant_name: str = None,
) -> Optional[Skill]:
    """
    Find a Skill whose tool_skills chain exactly matches the given sequence of
    (tool_id, step_index) pairs, optionally filtered by tenant.

    The tool chain flow is assumed to be unique per skill.

    Args:
        sess: SQLAlchemy session.
        tool_chain: Iterable of steps where each step is either:
            - a dict with keys {"tool_id", "step_index"}, or
            - a (tool_id, step_index) tuple/list.

            tool_id can be a uuid.UUID or a string UUID.
        tenant_name: Optional tenant name for filtering results.

    Returns:
        Skill instance if a matching skill is found, otherwise None.
    """
    try:
        # Normalize input into a list of (uuid.UUID, int)
        normalized_steps: List[Tuple[uuid.UUID, int]] = []
        for step in tool_chain:
            if isinstance(step, dict):
                tool_id = step.get("tool_id")
                step_index = step.get("step_index")
            elif isinstance(step, (tuple, list)) and len(step) >= 2:
                tool_id, step_index = step[0], step[1]
            else:
                logger.warning(f"Unsupported tool_chain step format: {step!r}; skipping")
                continue

            if tool_id is None or step_index is None:
                logger.warning(f"tool_chain step missing tool_id or step_index; skipping: {step!r}")
                continue

            # Normalize tool_id to UUID
            if isinstance(tool_id, str):
                tool_uuid = uuid.UUID(tool_id)
            else:
                tool_uuid = tool_id

            normalized_steps.append((tool_uuid, int(step_index)))

        if not normalized_steps:
            logger.warning("find_skill_by_tool_chain called with empty or invalid tool_chain")
            return None

        # Build VALUES clause for input_chain CTE
        values_parts = []
        params: Dict[str, Any] = {}
        for i, (tool_uuid, step_idx) in enumerate(normalized_steps):
            # Use plain bound parameters here; SQLAlchemy/psycopg2 will handle
            # typing based on the Python values (uuid.UUID / int) and the
            # context they are used in. Avoid inline casts like ::uuid / ::int
            # because they can interfere with SQLAlchemy's parameter parsing.
            values_parts.append(f"(:tool_id_{i}, :step_index_{i})")
            params[f"tool_id_{i}"] = tool_uuid
            params[f"step_index_{i}"] = step_idx

        values_sql = ", ".join(values_parts)

        # Add tenant_name filter if provided
        tenant_filter = ""
        if tenant_name:
            tenant_filter = "AND ts.tenant_name = :tenant_name"
            params["tenant_name"] = tenant_name

        sql = text(f"""
            WITH input_chain(tool_id, step_index) AS (
                SELECT * FROM (VALUES {values_sql}) AS v(tool_id, step_index)
            )
            SELECT ts.skill_name, ts.tenant_name
            FROM tool_skills ts
            JOIN input_chain ic
              ON ts.tool_id = ic.tool_id
             AND ts.step_index = ic.step_index
            WHERE 1=1 {tenant_filter}
            GROUP BY ts.skill_name, ts.tenant_name
            HAVING
                -- All input steps are present for this skill
                COUNT(*) = (SELECT COUNT(*) FROM input_chain)
                -- And the skill has no extra steps beyond the input chain
                AND COUNT(*) = (
                    SELECT COUNT(*)
                    FROM tool_skills ts2
                    WHERE ts2.skill_name = ts.skill_name
                      AND ts2.tenant_name = ts.tenant_name
                )
            LIMIT 1
        """)

        row = sess.execute(sql, params).first()
        if not row:
            logger.info(
                "No skill found matching tool_chain=%s",
                [(str(t), i) for (t, i) in normalized_steps],
            )
            return None

        skill_name = row[0]
        skill_tenant_name = row[1]
        
        # Use composite primary key (name, tenant_name) to get the skill
        skill = sess.execute(
            select(Skill).where(
                Skill.name == skill_name,
                Skill.tenant_name == skill_tenant_name
            )
        ).scalar_one_or_none()

        if skill:
            logger.info(
                "Found skill '%s' (tenant: %s) for tool_chain=%s",
                skill_name,
                skill_tenant_name,
                [(str(t), i) for (t, i) in normalized_steps],
            )
        else:
            logger.warning(
                "Skill name '%s' (tenant: %s) returned from query but not found via ORM",
                skill_name,
                skill_tenant_name
            )

        return skill

    except Exception as e:
        logger.error(f"Error searching skill by tool_chain: {e}")
        raise


def upsert_skill(sess, emb, skill: Optional[Skill], skill_data: Dict[str, Any], tenant_name: str) -> Skill:
    """Create or update a Skill row based on its name and tenant.

    The embedding is computed from label/description/intent and procedure step intents,
    mirroring the logic previously used in the domain layer.
    
    Args:
        sess: SQLAlchemy session
        emb: Embedder instance for generating embeddings
        skill: Optional existing Skill instance
        skill_data: Dictionary containing skill attributes
        tenant_name: Name of the tenant for isolation
    """
    name = skill_data.get("name")
    label = skill_data.get("label")
    description = skill_data.get("description", "")
    operational_entities = skill_data.get("operational_entities", [])
    operational_procedures = skill_data.get("operational_procedures", [])
    operational_intent = skill_data.get("operational_intent", "")
    preconditions = skill_data.get("preconditions", [])
    postconditions = skill_data.get("postconditions", [])
    proficiency = skill_data.get("proficiency", "")

    emb_input_parts = [
        label or "",
        description or "",
        operational_intent or "",
        " ".join(operational_entities),
        " ".join(
            p.get("step_intent", "")
            for p in operational_procedures
            if isinstance(p, dict)
        ),
        " ".join(preconditions),
        " ".join(postconditions),
    ]
    emb_input = " ".join(part for part in emb_input_parts if part).strip()
    emb_vec = emb.encode(emb_input) if emb_input else None

    # Ensure we always respect the unique constraint on skills.name and tenant_name by
    # preferring any existing row with the same name and tenant if one exists.
    # This allows ingest_skill to behave as a true upsert when the
    # tool_chain changes but the logical skill name stays the same.
    if not skill and name:
        existing_by_name = sess.execute(
            select(Skill).where(
                (Skill.name == name) &
                (Skill.tenant_name == tenant_name)
            )
        ).scalar_one_or_none()
        if existing_by_name is not None:
            skill = existing_by_name

    if not skill:
        skill = Skill(
            name=name,
            tenant_name=tenant_name,
            label=label,
            description=description,
            operational_entities=operational_entities,
            operational_procedures=operational_procedures,
            operational_intent=operational_intent,
            preconditions=preconditions,
            postconditions=postconditions,
            proficiency=proficiency,
            emb=emb_vec,
        )
        sess.add(skill)
        logger.info(f"Inserted new Skill, name={skill.name}, tenant={tenant_name}")
    else:
        skill.label = label
        skill.description = description
        skill.operational_entities = operational_entities
        skill.operational_procedures = operational_procedures
        skill.operational_intent = operational_intent
        skill.preconditions = preconditions
        skill.postconditions = postconditions
        skill.proficiency = proficiency
        skill.emb = emb_vec
        logger.info(f"Updated existing Skill, name={skill.name}, tenant={tenant_name}")

    return skill



def upsert_tool_skill(sess, skill_name: str, tool_id: Union[str, uuid.UUID], rel_json: Dict[str, Any], tenant_name: str) -> ToolSkill:
    """Upsert a single tool→skill relation with step metadata and strict tenant isolation.

    Args:
        sess: SQLAlchemy session
        skill_name: Name of the skill
        tool_id: ID of the tool (can be string or UUID)
        rel_json: Dictionary containing step_index and step_intent
        tenant_name: Name of the tenant for isolation

    Returns:
        ToolSkill: The created or updated ToolSkill relationship
        
    Raises:
        ValueError: If tool and skill belong to different tenants
    """
    try:
        # Convert string to UUID if necessary
        if isinstance(tool_id, str):
            tool_id = uuid.UUID(tool_id)

        step_index = rel_json.get("step_index")
        step_intent = rel_json.get("step_intent")

        # Validate tenant isolation: Get tool's tenant
        tool = sess.execute(
            select(McpTool).where(McpTool.id == tool_id)
        ).scalar_one_or_none()
        
        if not tool:
            raise ValueError(f"Tool with id {tool_id} not found")
        
        # Validate tenant isolation: Get skill's tenant using composite key
        skill = sess.execute(
            select(Skill).where(
                Skill.name == skill_name,
                Skill.tenant_name == tenant_name
            )
        ).scalar_one_or_none()
        
        if not skill:
            raise ValueError(f"Skill with name {skill_name} and tenant {tenant_name} not found")
        
        # Strict tenant validation
        if tool.tenant != tenant_name:
            raise ValueError(
                f"Tool '{tool.name}' belongs to tenant '{tool.tenant}', "
                f"but expected tenant '{tenant_name}'"
            )

        existing = sess.execute(
            select(ToolSkill).where(
                ToolSkill.tool_id == tool_id,
                ToolSkill.skill_name == skill_name,
                ToolSkill.tenant_name == tenant_name,
            )
        ).scalar_one_or_none()

        if existing:
            existing.step_index = step_index
            existing.step_intent = step_intent
            logger.info(
                "Updated tool-skill relation: tool_id=%s, skill_name=%s, step_index=%s, tenant=%s",
                tool_id,
                skill_name,
                step_index,
                tenant_name,
            )
            return existing
        else:
            relation = ToolSkill(
                tool_id=tool_id,
                skill_name=skill_name,
                tenant_name=tenant_name,
                step_index=step_index,
                step_intent=step_intent,
            )
            sess.add(relation)
            logger.info(
                "Inserted tool-skill relation: tool_id=%s, skill_name=%s, step_index=%s, tenant=%s",
                tool_id,
                skill_name,
                step_index,
                tenant_name,
            )
            return relation

    except Exception as e:
        logger.error("Failed to upsert tool skill for skill_name=%s, tool_id=%s, tenant=%s: %s", skill_name, tool_id, tenant_name, e)
        raise


def upsert_tool_skills(sess, skill_name, tool_chain: List[Any], tenant_name: str) -> None:
    """Upsert tool→skill relations including step metadata with strict tenant isolation.

    For each element in ``tool_chain`` this will:
      * create a new ``ToolSkill(tool_id, skill_name)`` row if none exists; or
      * update the existing row's ``step_index`` and ``step_intent``.

    This function does **not** delete any existing ``ToolSkill`` rows; relationships
    that are not mentioned in ``tool_chain`` are left untouched.
    
    Args:
        sess: SQLAlchemy session
        skill_name: Name of the skill
        tool_chain: List of tool chain steps
        tenant_name: Name of the tenant for isolation
    """
    try:
        for step in tool_chain:
            # Support both dict and tuple/list formats for backwards compatibility
            if isinstance(step, dict):
                tool_id = step.get("tool_id")
                rel_json = {
                    "step_index": step.get("step_index"),
                    "step_intent": step.get("step_intent")
                }
            elif isinstance(step, (tuple, list)) and len(step) >= 2:
                tool_id = step[0]
                rel_json = {
                    "step_index": step[1],
                    "step_intent": step[2] if len(step) > 2 else None
                }
            else:
                logger.warning("Unsupported tool_chain element %r; skipping", step)
                continue

            if tool_id is None:
                logger.warning("tool_chain element missing tool_id; skipping: %r", step)
                continue

            # Use the new upsert_tool_skill function with tenant validation
            upsert_tool_skill(sess, skill_name, tool_id, rel_json, tenant_name)

        sess.flush()
        logger.info("Successfully upserted tool skills for skill_name=%s, tenant=%s", skill_name, tenant_name)
    except Exception as e:
        logger.error("Failed to upsert tool skills for skill_name=%s, tenant=%s: %s", skill_name, tenant_name, e)
        raise



def tool_has_skills(sess, tenant: str, tool_name: str) -> bool:
    """Check whether a tool (by tenant and name) has any associated skills.

    This helper looks up the ``McpTool`` by ``(name, tenant)`` and then checks
    if at least one ``ToolSkill`` row exists for that tool.

    Returns ``True`` if the tool exists and has at least one skill, otherwise
    ``False``.
    """
    try:
        tool = get_mcp_tool_by_name_tenant(sess, tool_name, tenant)
        if not tool:
            logger.info(
                "tool_has_skills: tool not found, name=%s, tenant=%s",
                tool_name,
                tenant,
            )
            return False

        row = sess.execute(
            select(ToolSkill.tool_id)
            .where(ToolSkill.tool_id == tool.id)
            .limit(1)
        ).first()

        has_skills = row is not None
        logger.info(
            "tool_has_skills: tool_name=%s, tenant=%s, has_skills=%s",
            tool_name,
            tenant,
            has_skills,
        )
        return has_skills
    except Exception as e:
        logger.error(
            "Error checking skills for tool_name=%s, tenant=%s: %s",
            tool_name,
            tenant,
            e,
        )
        raise



def insert_capability_skill(sess, capability_name: str, skill_name: str, tenant_name: str = None) -> CapabilitySkill | None:
    """Insert a capability↔skill relationship if it does not already exist.

    Because ``capability_skill.skill_name`` has an FK to ``skills.name``, we must
    ensure the corresponding Skill row exists before creating the relation to
    avoid IntegrityError (e.g. for LLM-generated skills that were not persisted).
    
    Note: Requires tenant_name to be added to CapabilitySkill composite PK.
    """
    # Ensure the Skill exists; if not, skip creating the relation
    skill = sess.execute(select(Skill).where(Skill.name == skill_name)).scalar_one_or_none()
    if not skill:
        logger.warning(
            "Skipping capability-skill relation because Skill does not exist: "
            "capability_name=%s, skill_name=%s",
            capability_name,
            skill_name,
        )
        return None

    # Get tenant_name from capability if not provided
    if not tenant_name:
        capability = sess.execute(
            select(Capability).where(Capability.name == capability_name)
        ).scalar_one_or_none()
        if capability:
            tenant_name = capability.tenant_name
        else:
            logger.warning(
                "Capability not found: capability_name=%s",
                capability_name,
            )
            return None

    existing = sess.execute(
        select(CapabilitySkill).where(
            CapabilitySkill.capability_name == capability_name,
            CapabilitySkill.skill_name == skill_name,
            CapabilitySkill.tenant_name == tenant_name
        )
    ).scalar_one_or_none()

    if existing:
        logger.info(
            "Capability-skill relation already exists, capability_name=%s, skill_name=%s, tenant_name=%s",
            capability_name,
            skill_name,
            tenant_name,
        )
        return existing

    relation = CapabilitySkill(
        capability_name=capability_name,
        skill_name=skill_name,
        tenant_name=tenant_name
    )
    sess.add(relation)
    logger.info(
        "Inserted new capability and skill relation, capability_name=%s, skill_name=%s, tenant_name=%s",
        capability_name,
        skill_name,
        tenant_name,
    )
    return relation

def search_mcp_tools(
    sess,
    emb,
    tenant_name: str,
    agent_id: Optional[str] = None,
    filter: Optional[Dict[str, Any]] = None,
    tool_query: Optional[str] = None,
    k: int = 10,
) -> List[Dict[str, Any]]:
    """Search MCP tools with flexible filtering options and strict tenant isolation.

    Filtering Order (applied sequentially):
    1. First priority: If agent_id is provided, constrain output to agent's roles
    2. Second priority: If filter is provided, apply it on top of agent-constrained output (if agent exists)
    3. Third priority: If tool_query is provided, apply vector search on top of all filtered output

    Tool Types:
    - system: Always returned regardless of search filters (filtered by tenant)
    - general: Subject to search logic and filtering (filtered by tenant)

    Args:
        sess: SQLAlchemy session
        emb: Embedding model for vector search
        tenant_name: Tenant name for strict isolation (REQUIRED)
        agent_id: Optional agent ID to filter tools (first priority filter)
        filter: Optional filter dict following tool_filter_schema.json structure (second priority filter)
                {
                    "tool_query": "search string",
                    "roles": [
                        {
                            "name": "role_name",
                            "domains": [
                                {
                                    "name": "domain_name",
                                    "capabilities": [
                                        {
                                            "name": "capability_name",
                                            "skills": ["skill1", "skill2"]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
        tool_query: Optional tool description query for vector search (third priority, overrides filter.tool_query if both provided)
        k: Number of results to return for vector search (default: 10)

    Returns:
        List of dictionaries containing tool information with similarity scores
    """
    try:
        # First, get all system tools for this tenant (always returned)
        system_tools_query = select(McpTool).where(
            McpTool.tool_type == "system",
            McpTool.tenant == tenant_name
        )
        system_tools = sess.execute(system_tools_query).scalars().all()
        logger.info(f"Found {len(system_tools)} system tools for tenant {tenant_name} (always included)")

        # Step 1: Apply agent_id constraint first (if provided)
        agent_constrained_tool_ids = None
        if agent_id:
            logger.info(f"Step 1: Applying agent_id constraint for agent {agent_id}")
            # Get all tools accessible to this agent through agent -> roles -> domains -> capabilities -> tools
            agent_tools_query = (
                select(McpTool.id).distinct()
                .where(McpTool.tool_type == "general", McpTool.tenant == tenant_name)
                .join(CapabilityTool, CapabilityTool.tool_id == McpTool.id)
                .join(
                    DomainCapability,
                    DomainCapability.capability_name == CapabilityTool.capability_name,
                )
                .join(RoleDomain, RoleDomain.domain_name == DomainCapability.domain_name)
                .join(RoleAgent, RoleAgent.role_name == RoleDomain.role_name)
                .where(RoleAgent.agent_id == agent_id)
            )
            agent_tool_ids_result = sess.execute(agent_tools_query).fetchall()
            agent_constrained_tool_ids = [row.id for row in agent_tool_ids_result]
            logger.info(f"Agent {agent_id} has access to {len(agent_constrained_tool_ids)} tools")

            if not agent_constrained_tool_ids:
                logger.warning(f"No tools found for agent {agent_id}, returning only system tools")
                # Return only system tools
                system_results = []
                for tool in system_tools:
                    tool_info = {
                        "id": str(tool.id),
                        "name": tool.name,
                        "description": tool.description,
                        "document": tool.document,
                        "canonical_data": tool.canonical_data,
                        "tenant": tool.tenant,
                        "tool_type": "system"
                    }
                    system_results.append(tool_info)
                return system_results

        # Step 2: Apply filter on top of agent-constrained output (if filter is provided)
        filter_constrained_tool_ids = None
        if filter and "roles" in filter:
            logger.info("Step 2: Applying filter constraint on top of agent-constrained output")
            roles = filter.get("roles", [])
            role_queries = []

            for role in roles:
                role_name = role.get("name")
                if not role_name:
                    continue

                # Extract hierarchical filter for this specific role
                role_domain_names = []
                role_capability_names = []
                role_skill_names = []

                domains = role.get("domains", [])
                for domain in domains:
                    domain_name = domain.get("name")
                    if domain_name:
                        role_domain_names.append(domain_name)

                    capabilities = domain.get("capabilities", [])
                    for capability in capabilities:
                        capability_name = capability.get("name")
                        if capability_name:
                            role_capability_names.append(capability_name)

                        skills = capability.get("skills", [])
                        role_skill_names.extend(skills)

                # Build query for this specific role based on its filter depth
                role_query = select(McpTool.id).distinct().where(
                    McpTool.tool_type == "general",
                    McpTool.tenant == tenant_name
                )

                # If agent_id was provided, constrain this role query to agent's tools
                if agent_constrained_tool_ids is not None:
                    role_query = role_query.where(McpTool.id.in_(agent_constrained_tool_ids))

                # Determine filter level for this role
                if role_skill_names:
                    # Skill-based filtering for this role
                    logger.info(f"Role '{role_name}': Using skill-based filtering with skills: {role_skill_names}")
                    role_query = role_query.join(ToolSkill, ToolSkill.tool_id == McpTool.id)
                    role_query = role_query.join(
                        CapabilitySkill,
                        CapabilitySkill.skill_name == ToolSkill.skill_name,
                    )
                    role_query = role_query.join(
                        DomainCapability,
                        DomainCapability.capability_name == CapabilitySkill.capability_name,
                    )
                    role_query = role_query.join(
                        RoleDomain, RoleDomain.domain_name == DomainCapability.domain_name
                    )
                    role_query = role_query.where(
                        RoleDomain.role_name == role_name,
                        ToolSkill.skill_name.in_(role_skill_names)
                    )

                elif role_capability_names:
                    # Capability-based filtering for this role
                    logger.info(f"Role '{role_name}': Using capability-based filtering with capabilities: {role_capability_names}")
                    role_query = role_query.join(CapabilityTool, CapabilityTool.tool_id == McpTool.id)
                    role_query = role_query.join(
                        DomainCapability,
                        DomainCapability.capability_name == CapabilityTool.capability_name,
                    )
                    role_query = role_query.join(
                        RoleDomain, RoleDomain.domain_name == DomainCapability.domain_name
                    )
                    role_query = role_query.where(
                        RoleDomain.role_name == role_name,
                        CapabilityTool.capability_name.in_(role_capability_names)
                    )

                elif role_domain_names:
                    # Domain-based filtering for this role
                    logger.info(f"Role '{role_name}': Using domain-based filtering with domains: {role_domain_names}")
                    role_query = role_query.join(CapabilityTool, CapabilityTool.tool_id == McpTool.id)
                    role_query = role_query.join(
                        DomainCapability,
                        DomainCapability.capability_name == CapabilityTool.capability_name,
                    )
                    role_query = role_query.join(
                        RoleDomain, RoleDomain.domain_name == DomainCapability.domain_name
                    )
                    role_query = role_query.where(
                        RoleDomain.role_name == role_name,
                        DomainCapability.domain_name.in_(role_domain_names)
                    )

                else:
                    # Role-level filtering only
                    logger.info(f"Role '{role_name}': Using role-level filtering")
                    role_query = role_query.join(CapabilityTool, CapabilityTool.tool_id == McpTool.id)
                    role_query = role_query.join(
                        DomainCapability,
                        DomainCapability.capability_name == CapabilityTool.capability_name,
                    )
                    role_query = role_query.join(
                        RoleDomain, RoleDomain.domain_name == DomainCapability.domain_name
                    )
                    role_query = role_query.where(RoleDomain.role_name == role_name)

                role_queries.append(role_query)

            # Union all role queries to get combined tool IDs
            if role_queries:
                from sqlalchemy import union_all
                combined_query = union_all(*role_queries)
                filter_tool_ids_result = sess.execute(select(combined_query.c.id).distinct()).fetchall()
                filter_constrained_tool_ids = [row.id for row in filter_tool_ids_result]
                logger.info(f"Filter constraint resulted in {len(filter_constrained_tool_ids)} tools")

                if not filter_constrained_tool_ids:
                    logger.warning("No tools found matching filter criteria, returning only system tools")
                    # Return only system tools
                    system_results = []
                    for tool in system_tools:
                        tool_info = {
                            "id": str(tool.id),
                            "name": tool.name,
                            "description": tool.description,
                            "document": tool.document,
                            "canonical_data": tool.canonical_data,
                            "tenant": tool.tenant,
                            "tool_type": "system"
                        }
                        system_results.append(tool_info)
                    return system_results

        # Determine final tool IDs based on applied constraints
        final_tool_ids = None
        if filter_constrained_tool_ids is not None:
            # Filter was applied (which already includes agent constraint if it was provided)
            final_tool_ids = filter_constrained_tool_ids
        elif agent_constrained_tool_ids is not None:
            # Only agent constraint was applied
            final_tool_ids = agent_constrained_tool_ids
        # else: No constraints, will use all general tools for the tenant

        # Step 3: Apply tool_query (vector search) on top of all filtered output
        # Extract tool_query from filter if not provided directly
        if not tool_query and filter and "tool_query" in filter:
            tool_query = filter.get("tool_query")

        # Execute query with or without vector search
        if tool_query:
            logger.info(f"Step 3: Applying vector search with query: '{tool_query}'")
            vec = np.array(emb.encode([tool_query])[0])

            if final_tool_ids is not None:
                # Perform vector search on the filtered tool IDs
                sql = text(f"""
                    SELECT id, name, description, document, canonical_data, tenant, tool_type,
                           1 - (embedding <=> (:v)::vector) AS cosine_sim
                    FROM mcp_tools
                    WHERE id = ANY(:tool_ids) AND tool_type = 'general' AND tenant = :tenant_name
                    ORDER BY embedding <=> (:v)::vector
                    LIMIT {k}
                """)
                rows = sess.execute(
                    sql.bindparams(
                        bindparam("v", value=vec.tolist()),
                        bindparam("tool_ids", value=final_tool_ids),
                        bindparam("tenant_name", value=tenant_name)
                    )
                ).fetchall()
            else:
                # No prior constraints, perform vector search on all general tools for tenant
                sql = text(f"""
                    SELECT id, name, description, document, canonical_data, tenant, tool_type,
                           1 - (embedding <=> (:v)::vector) AS cosine_sim
                    FROM mcp_tools
                    WHERE tool_type = 'general' AND tenant = :tenant_name
                    ORDER BY embedding <=> (:v)::vector
                    LIMIT {k}
                """)
                rows = sess.execute(
                    sql.bindparams(
                        bindparam("v", value=vec.tolist()),
                        bindparam("tenant_name", value=tenant_name)
                    )
                ).fetchall()
        else:
            # No vector search, get all tools matching the constraints
            if final_tool_ids is not None:
                base_query = select(McpTool).where(
                    McpTool.tool_type == "general",
                    McpTool.tenant == tenant_name,
                    McpTool.id.in_(final_tool_ids)
                )
            else:
                base_query = select(McpTool).where(
                    McpTool.tool_type == "general",
                    McpTool.tenant == tenant_name
                )
            rows = sess.execute(base_query).scalars().all()

        # Format domain tool results
        domain_results = []
        for row in rows:
            # Handle both ORM objects and raw SQL rows
            if hasattr(row, 'id'):
                # ORM object
                tool = row
            else:
                # Raw SQL row from vector search
                tool = row

            tool_info = {
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "document": tool.document,
                "canonical_data": tool.canonical_data,
                "tenant": tool.tenant,
                "tool_type": tool.tool_type if hasattr(tool, 'tool_type') else "general"
            }

            # Add similarity score if vector search was used
            if tool_query and hasattr(row, 'cosine_sim'):
                tool_info["cosine_similarity"] = float(row.cosine_sim)

            domain_results.append(tool_info)

        # Format system tool results
        system_results = []
        for tool in system_tools:
            tool_info = {
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "document": tool.document,
                "canonical_data": tool.canonical_data,
                "tenant": tool.tenant,
                "tool_type": "system"
            }
            system_results.append(tool_info)

        # Combine system tools (always included) with domain tools
        results = system_results + domain_results

        logger.info(f"Returning {len(results)} MCP tools ({len(system_results)} system + {len(domain_results)} domain)")
        return results

    except Exception as e:
        logger.error(f"Failed to search MCP tools: {str(e)}")
        raise


# Keep the original function for backward compatibility
def get_mcp_tools_for_agent(
    sess, 
    emb, 
    agent_id: str, 
    capability_names: Optional[List[str]] = None, 
    tool_query: Optional[str] = None, 
    k: int = 10
) -> List[Dict[str, Any]]:
    """
    Legacy function - use search_mcp_tools instead.
    Get MCP tools for an agent ID.
    """
    return search_mcp_tools(
        sess=sess,
        emb=emb,
        agent_id=agent_id,
        capability_names=capability_names,
        tool_query=tool_query,
        k=k
    )


# Staging Services CRUD Operations

def upsert_staging_service(sess, staging_service_data: dict, tenant: str, username: str = "system",  service_id: uuid.UUID=None) -> StagingService:
    """
    Create or update a staging service in the database.
    
    Args:
        sess: SQLAlchemy session
        staging_service_data: Dictionary containing staging service data
        tenant: Tenant name
        username: Username for created_by/updated_by fields
        
    Returns:
        StagingService: The created or updated staging service
    """
    try:

        service_name = staging_service_data.get("name")
        if not service_name:
            raise ValueError("Service data must contain a 'name' field")
        now = datetime.now(timezone.utc)
        if not service_id:
            tool_id = staging_service_data.get("id")
        else:
            tool_id=service_id    

        if tool_id and isinstance(tool_id, str):
            try:
                tool_id = uuid.UUID(tool_id)
            except ValueError:
                logger.error(f"Invalid UUID format: {tool_id}")
                tool_id=None

        staging_by_id=None
        if tool_id:
            staging_by_id = get_staging_service_by_id(sess, str(tool_id))
        
        if staging_by_id:
            # Serialize the service data to handle UUID objects before storing in JSONB
            serialized_service_data = serialize_for_jsonb(staging_service_data)
            
            staging_by_id.service_data = serialized_service_data
            staging_by_id.name = service_name
            staging_by_id.updated_by = username
            staging_by_id.updated_at = now
            sess.flush()
            logger.info(f"Updated existing staging service: {service_name}")
            return staging_by_id
        else:
        # Try to get existing staging service by name and tenant
            # Create new staging service
            # Serialize the service data to handle UUID objects before storing in JSONB
            serialized_service_data = serialize_for_jsonb(staging_service_data)
            
            new_service = StagingService(
                name=service_name,
                tenant=tenant,
                service_data=serialized_service_data,
                created_by=username,
                updated_by=username,
                created_at=now,
                updated_at=now
            )
            if tool_id:
                new_service.id=tool_id
            else:
                new_id = uuid.uuid4()
                new_service.id= new_id

                new_service.service_data["id"]=str(new_id) 

            sess.add(new_service)
            sess.flush()
            logger.info(f"Created new staging service: {service_name}")
            return new_service
            
    except Exception as e:
        logger.error(f"Failed to create/update staging service: {str(e)}")
        raise


def get_staging_service_by_id(sess, service_id: str) -> Optional[StagingService]:
    """
    Retrieve a staging service by its ID.
    
    Args:
        sess: SQLAlchemy session
        service_id: The ID of the staging service
        
    Returns:
        Optional[StagingService]: The staging service if found, None otherwise
    """
    try:
        service = sess.execute(
            select(StagingService).where(StagingService.id == service_id)
        ).scalar_one_or_none()
        
        if service:
            logger.info(f"Retrieved staging service with ID: {service_id}")
        else:
            logger.warning(f"Staging service not found with ID: {service_id}")
        return service
    except Exception as e:
        logger.error(f"Error retrieving staging service by ID {service_id}: {str(e)}")
        raise


def get_staging_service_by_name(sess, tenant: str, name: str) -> Optional[StagingService]:
    """
    Retrieve a staging service by its name and tenant.
    
    Args:
        sess: SQLAlchemy session
        tenant: Tenant name
        name: The name of the staging service
        
    Returns:
        Optional[StagingService]: The staging service if found, None otherwise
    """
    try:
        service = sess.execute(
            select(StagingService).where(
                StagingService.tenant == tenant,
                StagingService.name == name
            )
        ).scalar_one_or_none()
        
        if service:
            logger.info(f"Retrieved staging service with name: {name}")
        else:
            logger.warning(f"Staging service not found with name: {name}")
        return service
    except Exception as e:
        logger.error(f"Error retrieving staging service by name {name}: {str(e)}")
        raise


def get_all_staging_services(sess, tenant: str, skip: int = 0, limit: int = 100) -> List[StagingService]:
    """
    Retrieve all staging services for a tenant with pagination.
    
    Args:
        sess: SQLAlchemy session
        tenant: Tenant name
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[StagingService]: List of staging services
    """
    try:
        services = sess.execute(
            select(StagingService).where(
                StagingService.tenant == tenant
            ).offset(skip).limit(limit)
        ).scalars().all()

        logger.info(f"Retrieved {len(services)} staging services for tenant {tenant}")
        return services
    except Exception as e:
        logger.error(f"Error retrieving all staging services: {str(e)}")
        raise


def delete_staging_service_by_id(sess, service_id: str) -> bool:
    """
    Delete a staging service by its ID.
    
    Args:
        sess: SQLAlchemy session
        service_id: The ID of the staging service to delete
        
    Returns:
        bool: True if deleted successfully, False if not found
    """
    try:
        service = sess.execute(
            select(StagingService).where(StagingService.id == service_id)
        ).scalar_one_or_none()
        
        if service:
            sess.delete(service)
            sess.flush()
            logger.info(f"Deleted staging service with ID: {service_id}")
            return True
        else:
            logger.warning(f"Staging service not found with ID: {service_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting staging service by ID {service_id}: {str(e)}")
        raise


def search_staging_services(
    sess,
    tenant: Optional[str] = None,
    name_pattern: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[StagingService]:
    """
    Search staging services with flexible filtering options.
    
    Args:
        sess: SQLAlchemy session
        tenant: Optional tenant name to filter by
        name_pattern: Optional name pattern to search for (using LIKE)
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[StagingService]: List of matching staging services
    """
    try:
        query = select(StagingService)
        
        # Apply filters
        if tenant:
            query = query.where(StagingService.tenant == tenant)
        if name_pattern:
            query = query.where(StagingService.name.like(f"%{name_pattern}%"))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        services = sess.execute(query).scalars().all()
        logger.info(f"Found {len(services)} staging services matching search criteria")
        return services
        
    except Exception as e:
        logger.error(f"Error searching staging services: {str(e)}")
        raise


# MCP Tool Deletion Functions

def delete_capability_skill_by_skill_name(sess, skill_name: str) -> int:
    """
    Delete all capability-skill relationships for a given skill.
    
    Args:
        sess: SQLAlchemy session
        skill_name: Name of the skill
        
    Returns:
        int: Number of relationships deleted
    """
    try:
        from sqlalchemy import delete
        
        delete_stmt = delete(CapabilitySkill).where(CapabilitySkill.skill_name == skill_name)
        result = sess.execute(delete_stmt)
        deleted_count = result.rowcount
        
        logger.info(f"Deleted {deleted_count} capability-skill relationships for skill '{skill_name}'")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting capability-skill relationships for skill '{skill_name}': {str(e)}")
        raise


def delete_skill_by_name(sess, skill_name: str) -> bool:
    """
    Delete a skill and its relationships.
    First deletes capability-skill relationships, then the skill itself.
    
    Args:
        sess: SQLAlchemy session
        skill_name: Name of the skill to delete
        
    Returns:
        bool: True if deleted successfully, False if not found
    """
    try:
        # First, find the skill
        skill = sess.execute(
            select(Skill).where(Skill.name == skill_name)
        ).scalar_one_or_none()
        
        if not skill:
            logger.warning(f"Skill not found with name: {skill_name}")
            return False
        
        # Delete capability-skill relationships first
        delete_capability_skill_by_skill_name(sess, skill_name)
        
        # Now delete the skill itself
        sess.delete(skill)
        sess.flush()
        
        logger.info(f"Successfully deleted skill '{skill_name}' and its relationships")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting skill '{skill_name}': {str(e)}")
        sess.rollback()
        raise


def get_tool_count_for_skill(sess, skill_name: str) -> int:
    """
    Get the count of tools associated with a skill.
    
    Args:
        sess: SQLAlchemy session
        skill_name: Name of the skill
        
    Returns:
        int: Number of tools associated with the skill
    """
    try:
        from sqlalchemy import func
        
        count = sess.execute(
            select(func.count(ToolSkill.tool_id)).where(ToolSkill.skill_name == skill_name)
        ).scalar()
        
        logger.info(f"Skill '{skill_name}' has {count} associated tool(s)")
        return count
        
    except Exception as e:
        logger.error(f"Error counting tools for skill '{skill_name}': {str(e)}")
        raise



def insert_application_mcp_tool(sess, app_name: str, tenant_name: str, tool_id: Union[str, uuid.UUID]) -> 'ApplicationMcpTool':
    """
    Insert a relationship between an application and an MCP tool.
    
    Args:
        sess: SQLAlchemy session
        app_name: Name of the application
        tenant_name: Name of the tenant
        tool_id: ID of the MCP tool (can be string or UUID)
        
    Returns:
        ApplicationMcpTool: The created relationship
        
    Raises:
        ValueError: If application or tool doesn't exist
    """
    try:
        # Import here to avoid circular dependency
        from integrator.tools.tool_db_model import ApplicationMcpTool
        
        # Convert string to UUID if necessary
        if isinstance(tool_id, str):
            tool_id = uuid.UUID(tool_id)
        
        # Validate that the application exists
        application = get_app_by_app_name_and_tenant_name(sess, app_name, tenant_name)
        if not application:
            raise ValueError(f"Application '{app_name}' not found for tenant '{tenant_name}'")
        
        # Validate that the tool exists
        tool = get_mcp_tool_by_id(sess, str(tool_id))
        if not tool:
            raise ValueError(f"MCP tool with ID '{tool_id}' not found")
        
        # Check if relationship already exists
        existing = sess.execute(
            select(ApplicationMcpTool).where(
                ApplicationMcpTool.app_name == app_name,
                ApplicationMcpTool.tenant_name == tenant_name,
                ApplicationMcpTool.tool_id == tool_id
            )
        ).scalar_one_or_none()
        
        if existing:
            logger.info(f"Application-MCP tool relationship already exists: app_name={app_name}, tenant={tenant_name}, tool_id={tool_id}")
            return existing
        
        # Create new relationship
        relationship = ApplicationMcpTool(
            app_name=app_name,
            tenant_name=tenant_name,
            tool_id=tool_id
        )
        sess.add(relationship)
        sess.flush()
        
        logger.info(f"Inserted application-MCP tool relationship: app_name={app_name}, tenant={tenant_name}, tool_id={tool_id}")
        return relationship
        
    except Exception as e:
        logger.error(f"Failed to insert application-MCP tool relationship: {str(e)}")
        raise


def delete_application_mcp_tool(sess, tool_id: Union[str, uuid.UUID], tenant_name: str,  app_name: str=None) -> bool:
    """
    Delete a relationship between an application and an MCP tool.
    
    Args:
        sess: SQLAlchemy session
        app_name: Name of the application
        tenant_name: Name of the tenant
        tool_id: ID of the MCP tool (can be string or UUID)
        
    Returns:
        bool: True if deleted successfully, False if not found
    """
    try:
        # Import here to avoid circular dependency
        from integrator.tools.tool_db_model import ApplicationMcpTool
        from sqlalchemy import delete
        
        # Convert string to UUID if necessary
        if isinstance(tool_id, str):
            tool_id = uuid.UUID(tool_id)

        app_names=[]
        if app_name:
            app_names.append(app_name)
        else:
            app_tool_relationships = sess.execute( select(ApplicationMcpTool).where(ApplicationMcpTool.tool_id == tool_id, ApplicationMcpTool.tenant_name==tenant_name)
            ).scalars().all()
        
            app_names = [rel.app_name for rel in app_tool_relationships]    

        for name in app_names:

            # Delete the relationship
            delete_stmt = delete(ApplicationMcpTool).where(
                ApplicationMcpTool.app_name == name,
                ApplicationMcpTool.tenant_name == tenant_name,
                ApplicationMcpTool.tool_id == tool_id
            )
            result = sess.execute(delete_stmt)
            deleted_count = result.rowcount
        
            if deleted_count > 0:
                sess.flush()
                tool_count = get_tool_count_by_app_name(sess, name, tenant_name)
                if tool_count == 0:
                    # This application has no more tools, delete it
                    logger.info(f"Application '{name}' (tenant: {tenant_name}) has no more tools, deleting application")
                    app = get_app_by_app_name_and_tenant_name(sess, name, tenant_name)
                    if app:
                        sess.delete(app)
                        logger.info(f"Deleted application '{name}' (tenant: {tenant_name})")

            logger.info(f"Deleted application-MCP tool relationship: tenant={tenant_name}, tool_id={tool_id}")
            return True
        else:
            logger.warning(f"Application-MCP tool relationship not found: tenant={tenant_name}, tool_id={tool_id}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to delete application-MCP tool relationship: {str(e)}")
        raise


def get_tool_count_by_app_name(sess, app_name: str, tenant_name: str) -> int:
    """
    Get the count of MCP tools associated with an application.
    
    Args:
        sess: SQLAlchemy session
        app_name: Name of the application
        tenant_name: Name of the tenant
        
    Returns:
        int: Number of tools associated with the application
    """
    try:
        # Import here to avoid circular dependency
        from integrator.tools.tool_db_model import ApplicationMcpTool
        from sqlalchemy import func
        
        count = sess.execute(
            select(func.count(ApplicationMcpTool.tool_id)).where(
                ApplicationMcpTool.app_name == app_name,
                ApplicationMcpTool.tenant_name == tenant_name
            )
        ).scalar()
        
        logger.info(f"Application '{app_name}' (tenant: {tenant_name}) has {count} associated tool(s)")
        return count
        
    except Exception as e:
        logger.error(f"Error counting tools for application '{app_name}' (tenant: {tenant_name}): {str(e)}")
        raise


def delete_tool_by_id(sess, tool_id: Union[str, uuid.UUID]) -> Optional[McpTool]:
    """
    Delete an MCP tool and its relationships by tool ID.
    
    This function performs cascading deletes in the following order:
    1. Delete tool-to-tool relationships (ToolRel) where this tool is source or target
    2. Delete capability-tool relationships
    3. Delete tool-skill relationships
    4. For each skill that only has this tool, delete the skill and its capability relationships
    5. Delete application-mcp_tool relationships
    6. Delete the tool itself
    
    Args:
        sess: SQLAlchemy session
        tool_id: ID of the tool to delete (can be string or UUID)
        
    Returns:
        Optional[McpTool]: The deleted tool if successful, None if not found or on error
    """
    try:
        # Convert string to UUID if necessary
        if isinstance(tool_id, str):
            try:
                tool_id = uuid.UUID(tool_id)
            except ValueError:
                logger.error(f"Invalid UUID format: {tool_id}")
                return None
        
        # First, find the tool
        tool = sess.execute(
            select(McpTool).where(McpTool.id == tool_id)
        ).scalar_one_or_none()
        
        if not tool:
            logger.warning(f"Tool not found with ID: {tool_id}")
            return None
        
        # Store tool data before deletion
        tool_name = tool.name
        deleted_tool = McpTool(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            embedding=tool.embedding,
            document=tool.document,
            canonical_data=tool.canonical_data,
            tenant=tool.tenant,
            created_by=tool.created_by,
            created_at=tool.created_at,
            updated_by=tool.updated_by,
            updated_at=tool.updated_at
        )
        
        # Use a direct DELETE statement to avoid potential session issues
        from sqlalchemy import delete
        
        # Step 1: Delete tool-to-tool relationships where this tool is source or target
        delete_tool_rel_source_stmt = delete(ToolRel).where(ToolRel.source_tool_id == tool_id)
        tool_rel_source_result = sess.execute(delete_tool_rel_source_stmt)
        tool_rel_source_count = tool_rel_source_result.rowcount
        logger.info(f"Deleted {tool_rel_source_count} tool relationships where tool_id={tool_id} is source")
        
        delete_tool_rel_target_stmt = delete(ToolRel).where(ToolRel.target_tool_id == tool_id)
        tool_rel_target_result = sess.execute(delete_tool_rel_target_stmt)
        tool_rel_target_count = tool_rel_target_result.rowcount
        logger.info(f"Deleted {tool_rel_target_count} tool relationships where tool_id={tool_id} is target")
        
        # Step 2: Delete capability-tool relationships
        delete_capability_tool_stmt = delete(CapabilityTool).where(CapabilityTool.tool_id == tool_id)
        capability_tool_result = sess.execute(delete_capability_tool_stmt)
        capability_tool_count = capability_tool_result.rowcount
        logger.info(f"Deleted {capability_tool_count} capability-tool relationships for tool_id={tool_id}")
        
        # Step 3: Get all skills associated with this tool before deleting tool-skill relationships
        tool_skills = sess.execute(
            select(ToolSkill).where(ToolSkill.tool_id == tool_id)
        ).scalars().all()
        
        skill_names_to_check = [ts.skill_name for ts in tool_skills]
        
        # Step 4: Delete tool-skill relationships
        delete_tool_skill_stmt = delete(ToolSkill).where(ToolSkill.tool_id == tool_id)
        tool_skill_result = sess.execute(delete_tool_skill_stmt)
        tool_skill_count = tool_skill_result.rowcount
        logger.info(f"Deleted {tool_skill_count} tool-skill relationships for tool_id={tool_id}")
        
        # Step 5: Check each skill and delete if this was the only tool
        for skill_name in skill_names_to_check:
            tool_count = get_tool_count_for_skill(sess, skill_name)
            if tool_count == 0:
                # This skill has no more tools, delete it
                logger.info(f"Skill '{skill_name}' has no more tools, deleting skill")
                delete_skill_by_name(sess, skill_name)
        
        # Step 6: Get all applications associated with this tool before deleting relationships
        delete_application_mcp_tool(sess, tool_id, tool.tenant )

        
        # Step 8: Now delete the tool itself
        sess.delete(tool)
        
        # Flush the changes to ensure they're sent to the database in the correct order
        sess.flush()
        
        logger.info(f"Successfully deleted tool '{tool_name}' (ID: {tool_id}) and its relationships")
        return deleted_tool
        
    except Exception as e:
        logger.error(f"Error deleting tool by ID '{tool_id}': {str(e)}")
        sess.rollback()  # Rollback on error
        return None
