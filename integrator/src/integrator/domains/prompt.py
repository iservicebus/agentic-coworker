
from __future__ import annotations
import json
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import  asdict

def _as_json(obj_or_text: Union[str, Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    if isinstance(obj_or_text, (dict, list)):
        return obj_or_text
    text = (obj_or_text or "").strip()
    return json.loads(text) if text else {}


CAN_TOOL_PROMPT_TEMPLATE = """


SYSTEM ROLE
You are an expert system that reads an API tool’s specification (its description AND input schema) and outputs one JSON object that accurately summarizes the tool. Your summary must preserve the exact meaning of the original specification while adding semantic clarity so an LLM can understand how this tool’s outputs may be used as another tool’s inputs. Every detail of the inputs and outputs must be captured as accurately as possible.

GOAL
From the provided tool description and input schema, produce exactly one JSON object with the following keys (exact casing):

0. Tool Intent (Tier 0 – Intent)
Describe the tool’s single, high-level purpose. This should not restate the description verbatim, but must remain fully accurate to its intended function.

1. Strict, Canonical Business Objects (Tier 1 – Business Objects)
Identify the core domain entities the tool directly operates on. Use concrete nouns that appear or are implied in the original specification. These should allow an LLM to understand what kinds of objects flow between tools.

2. Strict, Canonical Operation (Tier 2 – Operation)
From the tool description, identify the primary action the tool performs and express it as a verb phrase. This must reflect the actual capability exactly as defined.

3. Strict, Canonical Inputs (Tier 2 – Inputs)
Your "inputs" field must contain:
{
  "required": [...],
  "optional": "..."
}

Rules:

Required Inputs:
- Only treat a parameter as required if the inputSchema explicitly lists it under a “required” field.
- For each required parameter, provide a semantic description that accurately reflects:
  • what the parameter represents  
  • why it is needed  
  • how it relates to the tool’s operation  
- Do not alter or invent meaning; stay faithful to the original semantics.
- If the schema contains no required fields, write:
  "required": "none"

Optional Inputs:
- Summarize all non-required parameters (even if many exist) into a single description.
- Ensure the summary accurately reflects original behaviors such as pagination, filtering, sorting, authentication-dependent fields, or additional metadata rules.
- Do not list optional parameters individually.
- Capture their purpose so an LLM sees how upstream outputs may satisfy these optional inputs.

4. Strict, Canonical Outputs (Tier 2 – Outputs)
Describe exactly what the tool returns, including:
- the type of data (e.g., “array of organization records”, “comment metadata and bodies”)
- what the returned objects represent
- how they could serve as inputs to other tools

Your description must match the original specification precisely—do not generalize beyond what is stated.

5. Strict, Canonical Preconditions and Postconditions (Tier 3)

Preconditions:
Accurately identify all logical conditions that must be true before the tool can run, derived from the specification. Examples include:
- required permissions
- required resource existence
- required value constraints
- required API accessibility
You must not introduce preconditions that are not implied by the original text.

Postconditions:
Describe the guaranteed state after successful execution, while accurately reflecting whether the tool is read-only or mutating. Do not infer side effects not present in the specification.

6. Strict, Canonical Context (Tier 4 – Context)
Summarize environmental, systemic, or operational factors that influence tool behavior. This may include:
- pagination rules
- time-format constraints
- rate limits
- media type negotiation
- cursor semantics
- default behaviors defined in the description

Context must stay faithful to the original description and must not introduce new assumptions.

OUTPUT FORMAT (MANDATORY)
Produce exactly one JSON object in the following structure:

{
  "name": "[Insert Tool Name Provided]",
  "intent": "[Tier 0 Result]",
  "business_objects": ["[Tier 1 Result]"],
  "operation": "[Tier 2 Operation]",
  "inputs": {
    "required": [ ... ] OR "none",
    "optional": "..."
  },
  "outputs": "[Tier 2 Output Description]",
  "preconditions": "[Tier 3 Preconditions]",
  "postconditions": "[Tier 3 Postconditions]",
  "context": "[Tier 4 Context]"
}

FINAL RULES
- The JSON must be strictly aligned with the tool’s description and input schema.
- Inputs and outputs must be captured as accurately as possible.
- You must not invent or assume features that are not described.
- Provide semantically rich descriptions for LLM reasoning, but never distort original meaning.
- Output only the JSON object and nothing else.

TOOL Name: [[TOOL_NAME]]

TOOL DESCRIPTION:
=== BEGIN TOOL DESCRIPTION ===
[[TOOL_DESCRIPTION]]
=== END TOOL DESCRIPTION ===

INPUT SCHEMA (RAW JSON):
=== BEGIN INPUT SCHEMA ===
[[INPUT_SCHEMA_RAW]]
=== END INPUT SCHEMA ===
"""


def build_can_tool_prompt(
    tool_name: str,    
    tool_description: str,
    input_schema: Union[str, Dict[str, Any]],
) -> str:
    """
    Builds a schema-aware capability extraction prompt using both description and JSON Schema.
    """
    cleaned_desc = tool_description
    schema_obj = _as_json(input_schema)
    schema_raw = json.dumps(schema_obj, ensure_ascii=False, indent=2) if schema_obj else "{}"

    prompt_str = CAN_TOOL_PROMPT_TEMPLATE.replace("[[TOOL_DESCRIPTION]]", cleaned_desc)
    prompt_str = prompt_str.replace("[[TOOL_NAME]]", tool_name)
    prompt_str = prompt_str.replace("[[INPUT_SCHEMA_RAW]]", schema_raw)
    return dedent(prompt_str).strip() + "\n"

DOMAIN_CLASSIFER="""

You are a domain classifier that assigns integration tools to exactly ONE business domain.

You are given:

1) A BUSINESS DOMAIN LIST as JSON ARRAY (DOMAINS_JSON):
   - Each item has:
     - name
     - label
     - description
     - scope
     - domain_entities
     - domain_purposes

2) TOOL DEFINITION as JSON (TOOLS_JSON):
   - The tool has:
     - tool_name
     - intent
     - business_objects
     - inputs
     - outputs
     - preconditions
     - postconditions
     - context
     - (optionally) operations

Your job is to map the tool to ONE domain.name from DOMAINS_JSON.

--------------------
CLASSIFICATION RULES
--------------------

When classifying a tool, apply these priorities IN ORDER:

1) PRIMARY MATCH: BUSINESS OBJECTS + CONTEXT
   - Compare the tool’s:
     - business_objects (what objects it manipulates),
     - inputs & outputs (the main payload types),
     - context (APIs/platforms it calls)
   - to each domain’s:
     - domain_entities,
     - description,
     - scope.
   - Choose the domain whose entities/description/scope best match the tool’s primary business objects and usage context.

2) SECONDARY MATCH: INTENT & OUTPUT vs DOMAIN PURPOSE
   - Use the tool’s intent and outputs to compare with domain_purposes:
     - “Why does this tool exist?” vs “Why does this domain exist?”
   - Confirm that the chosen domain’s purposes align with the tool’s outcome:
     - e.g., if the tool sends messages, supports collaboration, or community interaction → likely Social Communication & Community.
     - if the tool manages code, repos, branches, builds, or code quality → likely Product Design & Engineering.
     - if the tool manages documents, files, drives, or shared content → likely Content & Collaboration.
     - if the tool manages events, calendars, tasks, projects, or goals/OKRs → likely Workplace Management & Productivity.
     - if the tool manages customers, leads, opportunities, orders, or marketing campaigns → likely Go-to-Market, Sales & Customer Success.
     - if the tool manages enterprise-wide infrastructure, platform IAM, SSO, data, AI/ML, or security incidents → likely Digital & AI Platform, Data & Security.

3) TERTIARY MATCH: OPERATIONS AS CONFIRMATION
   - (If operations are available) Use them to confirm/validate your domain choice:
     - CRUD on messages/posts/conversations → Social Communication & Community.
     - CRUD/search on files, folders, drives, documents → Content & Collaboration.
     - CRUD/search on repositories, branches, commits, code scanning, releases → Product Design & Engineering.
     - CRUD/search on ServiceNow platform records, platform configuration, or similar infra services → Digital & AI Platform, Data & Security.
     - CRUD/search on sales orders, customer orders, or SAP customer objects → Go-to-Market, Sales & Customer Success.

--------------------
IMPORTANT DISTINCTIONS
--------------------

- Identity & Security vs Social Profiles:
  - If a tool deals with **enterprise-wide IAM, SSO, platform auth, or cross-app security** (e.g., generic OAuth provider URLs, platform user identity for many apps), map to:
    - digital_ai_platform_data_security
  - If a tool deals with **user identity or profile info specifically inside a communication or social network**, and is used for messaging, posting, or social presence (e.g., LinkedIn profile for posting, Gmail user profile for email context), map to:
    - social_communication_and_community

- Social Communication & Community:
  - Tools that primarily:
    - create or manage messages, emails, chats, posts, comments, threads, feeds, livestreams, groups, or communities; OR
    - list/search content on communication/social platforms (e.g., YouTube playlists/videos, Gmail messages),
  - should typically map to:
    - social_communication_and_community

- Content & Collaboration:
  - Tools that primarily:
    - manage documents, spreadsheets, presentations, wikis, files, folders, shared drives, or file metadata,
  - should typically map to:
    - content_and_collaboration

- Product Design & Engineering:
  - Tools that primarily:
    - manage GitHub organizations, users, repositories, branches, commits, code scanning analyses, artifacts, releases, PRs, etc.,
  - should typically map to:
    - product_design_and_engineering

- Workplace Management & Productivity:
  - Tools that primarily:
    - manage calendar events, calendars, subscriptions, meetings, tasks, projects, goals/OKRs,
  - should typically map to:
    - workplace_management_and_productivity

- Go-to-Market, Sales & Customer Success:
  - Tools that primarily:
    - manage customers, leads, opportunities, SAP customer orders, or other sales/renewal objects,
  - should typically map to:
    - go_to_market_sales_and_customer_success

--------------------
INPUTS YOU WILL RECEIVE
--------------------
DOMAINS_JSON:
=== BEGIN DOMAINS JSON ===
[[DOMAINS_JSON]]
=== END DOMAINS JSON ===

TOOL_JSON:
=== BEGIN TOOL_JSON ===
[[TOOL_JSON]]
=== END TOOL_JSON ===

--------------------
OUTPUT FORMAT
--------------------
Return a SINGLE JSON object  with this structure:

{ "domain_name": "<domain.name>" }

Rules:
- Use domain.name values from DOMAINS_JSON as the keys.
- Only include domains that have at least one tool assigned.
- Each tool_name from TOOLS_JSON must appear in exactly one domain’s list.
- Do NOT include any extra commentary, just the JSON object.
"""


def build_domain_classifer_prompt(
    tool_json: Dict[str, Any],
    domains: List[Dict[str, Any]],
) -> str:
    """
    Builds a schema-aware capability extraction prompt using both description and JSON Schema.
    """
   
    tool_raw = json.dumps(_as_json(tool_json), ensure_ascii=False, indent=2) if tool_json else "{}"

    domains_raw = json.dumps(_as_json(domains), ensure_ascii=False, indent=2) if domains else "[]"

    prompt_str = DOMAIN_CLASSIFER.replace("[[TOOL_JSON]]", tool_raw)
    prompt_str = prompt_str.replace("[[DOMAINS_JSON]]", domains_raw)
    return dedent(prompt_str).strip() + "\n"

CAPABILITY_CLASSIFER="""


You are a business capability classifier.

You will be given three JSON inputs:
1) capabilities: array of capability objects, each with:
       - name: capability key (e.g., "content_collaboration_integrations")
       - label: capability label
       - description: what this capability does and why it exists
       - business_context: list of key entities/contexts
       - business_processes: list of supported processes
       - business_intent: list of business intents
       - outcome: business outcome

2) CANONICAL_TOOL in JSON Format, including
     - tool_name
     - intent: high-level goal of the tool
     - business_objects: list of core entities it operates on
     - operation: main verb/verb phrase (what it does)
     - inputs: description of key inputs
     - outputs: description of primary outputs
     - preconditions
     - postconditions
     - context: environment/APIs/platforms it uses

--------------------
YOUR TASK
--------------------
assign the tool to EXACTLY ONE capability in the capability list
You MUST choose one and only one capability per tool, and you must NOT move tools across capability.
--------------------
MATCHING RULES
--------------------
When choosing a capability for a tool, follow this reasoning order:
1) PRIMARY MATCH: INTENT / OPERATION vs BUSINESS PROCESSES
   - Compare the tool’s:
     - intent (why it exists),
     - operation (what it primarily does)
     - outputs (what it returns)
     - context (platforms/APIs/services it calls),
   - to each capability’s:
     - description,
     - business_processes.
     - business_context (entities, objects, scenarios),
     - outcome.
   - Ask: “Which capability’s processes and context best match what this tool actually does?”
2) SECONDARY MATCH: BUSINESS OBJECTS + CONTEXT
   - Use the tool’s:
     - business_objects (what entities it manipulates),
     - context (platforms/APIs/services it calls),
     - inputs & outputs (what it takes and returns)
   - and compare them with the capability’s:
     - description,
     - business_context (entities, objects, scenarios),
3) TERTIARY MATCH: OPERATIONS & PROCESSES AS CONFIRMATION
   - If multiple capabilities are close, use the operations and business_processes as tie-breakers.
   - Examples:
     - If the tool lists, updates, or deletes records related to source code, branches, or pull requests → align with a capability that covers software engineering / source control / code review.
     - If the tool manages content/files/drives and sharing → align with a capability around file storage, collaboration, or content integrations.
     - If the tool sends messages/emails or posts social content → align with messaging/email/community or content publishing capabilities.
     - If the tool manages ITSM/ServiceNow-like records → align with ITSM/platform/operations capabilities, not generic business ones.
4) USE INPUTS & OUTPUTS FOR CONFIRMATION
   - Use the tool’s inputs/outputs to disambiguate:
     - Do the payloads look like messages, documents, files, calendar events, customer orders, incidents, etc.?
   - Prefer the capability whose business_context and business_processes naturally “consume” those payloads.

If a tool seems to fit multiple capabilities, choose the one where:
- The business_processes describe what the tool enables most directly.
- The capability description could naturally “own” that tool in a real organization.

Do NOT leave any tool unassigned. Do NOT assign a tool to more than one capability.



--------------------
INPUTS YOU WILL RECEIVE
--------------------
CAPABILITIES_JSON:
=== BEGIN CAPABILITIES JSON ===
[[CAPABILITIES_JSON]]
=== END CAPABILITIES JSON ===

TOOL_JSON:
=== BEGIN TOOL_JSON ===
[[TOOL_JSON]]
=== END TOOL_JSON ===


--------------------
OUTPUT FORMAT
--------------------

Return a single JSON object structured as:

{
  "capability_name": "<capability_name>"
}
    
"""


def build_capability_classifer_prompt(
    tool_json: Dict[str, Any],
    capabilities: List[Dict[str, Any]],
) -> str:
    """
    Builds a schema-aware capability extraction prompt using both description and JSON Schema.
    """
   
    tool_raw = json.dumps(_as_json(tool_json), ensure_ascii=False, indent=2) if tool_json else "{}"

    capabilities_raw = json.dumps(_as_json(capabilities), ensure_ascii=False, indent=2) if capabilities else "[]"

    prompt_str = CAPABILITY_CLASSIFER.replace("[[TOOL_JSON]]", tool_raw)
    prompt_str = prompt_str.replace("[[CAPABILITIES_JSON]]", capabilities_raw)
    return dedent(prompt_str).strip() + "\n"




TOOL_REL_PROMPT="""

TASK: Identify business-meaningful TWO-TOOL WORKFLOWS between one SOURCE tool and a list of TARGET tools.

You are given:
• One SOURCE tool specification
• A list of TARGET tool specifications

Each tool specification contains at minimum:
• name
• intent
• inputs (required + optional)
• outputs
• business_objects
• operation / context
• preconditions / postconditions

Your goal:
Identify all VALID workflows where one tool’s OUTPUT is REQUIRED as a REQUIRED INPUT to another tool.

Valid workflow directions:
• SOURCE → TARGET
• TARGET → SOURCE
• Tools must be distinct.

Return ONLY a JSON array (no commentary).  
If no workflows exist, return exactly: []

======================================================================
RULE 0 — DISTINCT TOOLS
======================================================================
A workflow must not use the same tool twice.

======================================================================
RULE 1 — STRICT REQUIRED-INPUT DEPENDENCY
======================================================================
A workflow A → B is VALID ONLY IF:

1. At least ONE required input of B can be satisfied by a documented output field of A.

2. The mapping MUST be explicit and field-level:  
   Name the exact output field of A and the exact required input field of B.  
   If A outputs “records of <Entity>”, you may reference a “selected <Entity> record”  
   and its implied canonical identifier fields.

3. The mapped fields MUST refer to the SAME business object type (see RULE 1A).

4. Optional inputs MUST NOT be used to establish dependency.

5. You may NOT invent fields or relationships not supported by the schema.

If you cannot name a valid field-level mapping, the workflow is INVALID.

======================================================================
RULE 1A — ENTITY-TYPE MATCHING (HARD REQUIREMENT)
======================================================================
A mapping is valid ONLY if the required input of B and the output field of A
refer to the SAME business object type.

To determine type:
• Use the tool’s `business_objects` list as the primary source.
• Use input/output text to refine or clarify the type.
• Entity types must match exactly or be clearly equivalent in the schema.

Examples that count as SAME entity:
• “Customer” ↔ “customer_id”
• “GitHub organization” ↔ “organization login”
• “User profile” ↔ “GitHub user”

Examples that are DIFFERENT entity types:
• organization ↔ user
• user ↔ repository
• organization ↔ repository
• organization ↔ account (unless explicitly stated as the same)
• ANY pair not clearly described as the same entity in the schema.

If the schema does NOT say two labels represent the same entity,  
YOU MUST TREAT THEM AS DIFFERENT.

======================================================================
RULE 1B — GENERIC LABELS ("ACCOUNT", "OWNER", "IDENTITY")
======================================================================
Generic words such as:
• account, owner, identity, subject, resource, record, object

MUST NOT be treated as parent or umbrella entity types.

You MUST NOT assume:
• organization is a subtype of “account”
• user is a subtype of “account”
• organization ↔ user via “owner”
• any entity ↔ any other via “identity” or “subject”

You may only map A → B through a generic term if:
• BOTH tools explicitly use the SAME generic term to describe the SAME business object, OR
• B’s input explicitly says it accepts the specific entity output by A.

Otherwise, treat them as DIFFERENT entity types.

======================================================================
RULE 1C — CONCEPTUAL LEVELS (ONLY WITHIN ONE ENTITY TYPE)
======================================================================
Within a SINGLE entity type, conceptual levels are:

1. Entity object (most general)  
2. Entity identifier (ID, key, login, handle, code)  
3. Entity-scoped primitive (paths, slugs, etc.)

Allowed:
• GENERAL → SPECIFIC (entity object → entity identifier)
• SPECIFIC → SPECIFIC (identifier → identifier)

Not allowed:
• SPECIFIC → GENERAL
• Any mapping across different entity types.

======================================================================
RULE 1D — INVALID IF FIRST-TOOL “OUTPUT” ORIGINATES FROM ITS OWN INPUTS OR PRECONDITIONST
======================================================================
A → B is INVALID if the field taken from A is not truly produced by A.

A field is NOT produced if:
It existed before A was called
(user input, auth identity, path params, or anything implied by preconditions)
A only echoes it back
(A returns the same value the user or auth context already supplied)
It comes from a “me/current user” endpoint
(any identity field like id, login, username, email is always precondition-derived)

Only values that A discovers, creates, or retrieves—not provided by the caller—may be used as valid dependencies for B.

✔️ Quick Test
To check any mapping A.output_field → B.required_input:

Did this value already exist before A ran?
→ YES → ❌ INVALID
→ NO → proceed

Is A just reflecting a user-supplied or auth-derived value?
→ YES → ❌ INVALID
→ NO → allowed

✔️ Valid Output Types
Lists of discovered entities

Search results
Retrieved metadata for unknown targets
IDs of newly created resources

❌ Invalid Output Types

Authenticated user identity
Path parameters that the user already supplied
Any value that A did not generate or discover


======================================================================
RULE 2 — ENUMERATION (LIST → DETAIL WORKFLOWS)
======================================================================
If A outputs a LIST of entities, A may be step 1 if:

• B operates on a SELECTED element from that list, AND
• B requires an identifier or reference for the SAME entity type.

In enumeration workflows:
• It is acceptable that a user could theoretically provide the identifier manually.
• A is still considered a valid provider because it enables discovery/selection.

INVALID enumeration:
• B ignores the selected entity
• B requires a field not present or implied in A’s entity records
• B’s required input is unrelated (e.g., a generic query string)

======================================================================
RULE 3 — BUSINESS PLAUSIBILITY
======================================================================
A workflow must represent a realistic business scenario:
• A discovers or produces an entity
• B operates on that exact entity

List → detail patterns are always plausible if entity types match.

======================================================================
RULE 4 — COMPOSITE INTENT
======================================================================
For each valid workflow, produce EXACTLY ONE plain-language sentence describing:
• The real-world scenario
• The specific entity passed from A to B
• Why A’s output is useful for calling B

======================================================================
RULE 5 — OUTPUT FORMAT (MANDATORY)
======================================================================
Return a JSON array of objects like:

{
  "tool_flow": ["<ToolA>", "<ToolB>"],
  "field_mapping": [
    {
      "from_output_field": "<A.output_field OR selected entity field>",
      "to_input_field": "<B.required_input_field>",
      "entity_type": "<shared business object>"
    }
  ],
  "composite_intent": "<one-sentence description>"
}

If no workflows exist, output exactly:

[]

======================================================================
RULE 6 — HARD PROHIBITIONS
======================================================================
A workflow is INVALID if:
• It uses invented fields not in outputs or implied by entity records
• It maps across different entity types
• It uses optional inputs to justify dependency
• It relies on vague natural-language hierarchy (e.g., organization → account)
• It treats generic words (“account”, “owner”, “identity”) as true entity types

======================================================================
RULE 7 — INTERNAL VALIDATION CHECKLIST
======================================================================
Before outputting a workflow, internally verify:

1. A provides a documented or implied identifier for the SAME entity type B requires.  
2. The mapping satisfies entity-type equality.  
3. Conceptual level mapping is GENERAL→SPECIFIC or SPECIFIC→SPECIFIC.  
4. No invented fields or cross-type mappings were used.  
5. Enumeration flows use selected entity records correctly.  
6. All required inputs of B that depend on A appear in `field_mapping`.  
7. The scenario is business-plausible.

If ANY check fails, the workflow is INVALID, return []

=== BEGIN SOURCE TOOL  ===
[[SOURCE_TOOL]]
=== END SOURCRE TOOL ===

=== BEGIN TARGET TOOL LIST ===
[[TARGET_TOOLS]]
=== END TARGET TOOL LIST ===

"""


def build_tool_rel_prompt(
    src_tool_json: Dict[str, Any],
    target_tool_list: List[Dict[str, Any]],
) -> str:
    """
    Builds a tool_rel extraction prompt 
    """
   
    src_tool_raw = json.dumps(_as_json(src_tool_json), ensure_ascii=False, indent=2) if src_tool_json else "{}"

    target_tool_list_raw = json.dumps(_as_json(target_tool_list), ensure_ascii=False, indent=2) if target_tool_list else "[]"

    prompt_str = TOOL_REL_PROMPT.replace("[[SOURCE_TOOL]]", src_tool_raw)
    prompt_str = prompt_str.replace("[[TARGET_TOOLS]]", target_tool_list_raw)
    return dedent(prompt_str).strip() + "\n"

SKILL_EXTRACT_PROMPT="""
SYSTEM INSTRUCTIONS: Skill Extraction From Tool Chains  
============================================================

You are an expert designer of reusable operational business skills for an AI agent.

Your input is a list of tool chains. Each chain contains either:
- a single tool, or
- a sequence of tools forming a workflow (tool_A → tool_B → …)

Your task:

For each tool chain:
1. Decide whether it represents a valid standalone business skill.
2. If YES, produce a skill object (see schema below).
3. If NO, produce nothing for that chain.

After evaluating all chains, output ONE array of all valid skills.
If none qualify, output:
[]

============================================================
WHAT QUALIFIES AS A SKILL
============================================================

A chain qualifies only if ALL the following hold:

1) BUSINESS–MEANINGFUL  
The action must correspond to a real, understandable business task.

2) BUSINESS–ATOMIC  
The chain must accomplish ONE coherent business action.

3) NO USER-PROVIDED INTERNAL FIELDS (CRITICAL RULE)  
A required input is invalid if it is an internal system field unless it:
- is produced earlier in the same chain, or
- comes from a UI selection (not typed by the user).

Internal fields include any field whose name contains or ends with:
id, _id, uuid, guid, hash, key, token, ref, reference, handle, cursor,  
file_id, org_id, repo_id, project_id, thread_id, message_id, row_id,  
object_id, event_id, calendar_id, email_id, contact_id, sha, commit,  
revision, version_id, primary_key, foreign_key.

Also internal:
- opaque tokens
- database keys
- commit hashes
- any field described as “unique identifier”, “system ID”, etc.

Human-friendly values (emails, names, login names, search text, natural-language dates) are allowed.

If ANY required parameter violates these rules → the entire chain is invalid.

============================================================
RECURSIVE INTERNAL FIELD ANALYSIS
============================================================

For EVERY tool, recursively inspect:
- top-level parameters
- nested objects
- arrays of objects

If ANY nested required field matches internal-ID rules → the tool requires internal fields → invalid unless produced earlier.

============================================================
SCHEMA COMPLETENESS RULE
============================================================

If a tool does NOT explicitly list every required parameter by *name*:
- if “required”: [...] is shown without actual parameter names, or
- required fields are partially or fully undisclosed,

→ The tool is automatically INVALID (cannot be validated).

============================================================
INFERRING REQUIRED INPUTS WHEN NOT OBVIOUS (NEW RULE)
============================================================

If a tool’s required input parameters are NOT obvious from the schema:

1. Inspect the tool’s:
   - **preconditions**
   - **description**
   - **intent**
   - **operation/context** text

2. Infer what inputs the tool *effectively* requires to perform the described action.

3. Validate those inferred inputs against internal-field rules:
   - If inferred inputs are business-friendly (names, emails, natural-language dates, login strings) → allowed.
   - If inferred inputs are IDs or ID-like (internal identifiers) and not produced earlier in the chain → the chain is invalid.

============================================================
SEMANTIC ID RULE (MANDATORY)
============================================================
If a tool’s intent/description says it “fetches/retrieves/gets a specific or single entity” (e.g., “a specific GitHub organization”) using a field such as login, handle, username, or account name, then that field must be treated as an internal identifier, even if its name does not contain “id”. Such a tool is invalid as a standalone skill unless that identifier is produced earlier in the same chain.

============================================================
VALIDATION PROCESS FOR EACH TOOL CHAIN
============================================================

Step 1 — Validate Schema Completeness.  
If incomplete → chain invalid.

Step 2 — Initialize AVAILABLE INFORMATION SET.  
Includes only business-friendly inputs:
- search text
- names, emails, login names
- natural-language dates
- UI selections

Excludes all internal IDs.

Step 3 — Validate Each Tool Step.  
For every required parameter (explicit or inferred):
- If business-friendly → allowed.
- If internal → must be available from earlier tool output or UI selection.
Otherwise → chain invalid.

Step 4 — Apply Semantic ID Rule.  
If tool intent or name implies ID lookup → treat as internal requirement.

Step 5 — Update AVAILABLE INFORMATION SET.  
Add newly produced outputs, including internal IDs.

Step 6 — Single Tool Special Case.  
A single tool qualifies only if:
- it requires no internal IDs as input,
- its schema is complete,
- it performs a meaningful business action.

Step 7 — Invalid Chain Behavior.  
If ANY violation occurs:
- Do not repair or infer missing values beyond allowed inference.
- Do not partially output.
- Output nothing for that chain.

============================================================
SKILL OBJECT SCHEMA
============================================================

For each VALID skill:

{
  "name": string,                 // lower_snake_case
  "label": string,                // human-readable title
  "description": string,          // 2–3 sentence description
  "operational_entities": string[],
  "operational_procedures": [
    {
      "tool": string,
      "step_intent": string       // business reason for the step
    }
  ],
  "operational_intent": string,
  "preconditions": string[],
  "postconditions": string[],
  "proficiency": "basic" | "intermediate" | "advanced"
}

============================================================
OUTPUT FORMAT
============================================================

Return exactly one JSON array:

[ <zero or more skill objects> ]

If no chains qualify, output:

[]

--------------------------------
Inputs for Tool Chains 
--------------------------------
[[TOOL_CHAINS]]

"""



def build_skill_exract_prompt(
    tool_chains: List[Dict[str, Any]],
) -> str:
    """
    Builds a tool_rel extraction prompt 
    """
    src_chain_raw = json.dumps(([asdict(c) for c in tool_chains]), ensure_ascii=False, indent=2) if tool_chains else "{}"
    prompt_str = SKILL_EXTRACT_PROMPT.replace("[[TOOL_CHAINS]]", src_chain_raw)
    return dedent(prompt_str).strip() + "\n"


OP_MATCH_TEMPLATE = """
Operation-to-Operation Match Scoring

ROLE
You are a matcher that scores how well each Candidate Operation functionally matches a Target Operation.

TASK
Given a single Target Operation and a list of Candidate Operations, assign each candidate an integer score from 1–100 for overall functional match quality to the Target. Return ONLY a JSON array of objects with fields {"name","score"}, sorted by score descending. No explanations or extra keys.

INPUTS (inject below)

TARGET OPERATION (JSON):
[[TARGET_OPERATION_JSON]]

CANDIDATE OPERATIONS (JSON array):
[[CANDIDATE_OPERATIONS_JSON]]

SCHEMAS

Both Target and Candidate share:
name: string (short, stable verb_noun)
description: string (one sentence; function + boundaries; impl-agnostic)
inputs: string | string[] | null | omitted
outputs: string | string[] | null | omitted

Target-only fields:
capability: one sentence summarizing the tool capability context and intent
category: one sentence describing the relevant enterprise/consumer category

Candidate-only field:
related_capabilities?: Capability[] (optional)

Capability (for related_capabilities)
name: short, unique, stable identifier (e.g., invoice_management)
label: short, human-friendly title (≤80 chars)
description: plain-language scope/boundaries (what’s in/out)
intent: business purpose / desired outcome (why it exists)

MATCHING CRITERIA (evaluate each candidate vs. the Target)

Capability Context Alignment 50%
Target capability along with category semantically aligns with Candidate related_capabilities (by description and intent).

Functional Description Match 30%
Semantic overlap between Target description and Candidate description (function, boundaries, exclusions).

Inputs Compatibility 10%
Candidate accepts the semantical similar inputs as Target, or requires minimal/obvious adaptation.

Outputs Compatibility 10%
Candidate produces the semantically similar outputs as Target, or requires minimal/obvious adaptation.



Use semantics, not exact string matches. Treat omitted fields as null. When arrays vs. strings differ but are semantically equivalent, treat as compatible.


OUTPUT (strict)
[
  {"name":"<candidate-1>","score":<1-100>},
  {"name":"<candidate-2>","score":<1-100>}
]


"""


def build_op_match_prompt(
    target_op: Union[str, Dict[str, Any]],

    candidate_ops: Union[str, Dict[str, Any]],
) -> str:
    """
    Builds a schema-aware capability extraction prompt using both description and JSON Schema.
    """
    target_obj = _as_json(target_op)
    target_raw = json.dumps(target_obj, ensure_ascii=False, indent=2) if target_obj else "{}"

    candidate_obj = _as_json(candidate_ops)
    candidate_raw = json.dumps(candidate_obj, ensure_ascii=False, indent=2) if candidate_obj else "{}"

    prompt_str = OP_MATCH_TEMPLATE.replace("[[TARGET_OPERATION_JSON]]", target_raw)
    prompt_str = prompt_str.replace("[[CANDIDATE_OPERATIONS_JSON]]", candidate_raw)
    return dedent(prompt_str).strip() + "\n"
