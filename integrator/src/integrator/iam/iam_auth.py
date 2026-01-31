from integrator.utils.logger import get_logger
from integrator.iam.iam_db_crud import get_agents_by_username, get_user_by_username, get_agent_by_agent_id

logger = get_logger(__name__)

def get_auth_agent(sess, payload, tenant_name):

    user_type=payload.get("user_type")
    client_type=payload.get("client_type")
    scope=payload.get("scope")
    username = payload.get("preferred_username")
    x_agent_id=payload.get("x_agent_id")

    if user_type=="agent":
        return username, scope
    elif user_type=="human" and x_agent_id:

        agents = get_agents_by_username(sess, username, tenant_name)
        if not agents:
            return None, None

        for agent in agents:
            if agent.get("agent_id")==x_agent_id:
                return x_agent_id, scope
        return None, None
    elif client_type=="agent":
        return payload.get("azp"), scope    
    else:
        return None, None
def validate_tenant(sess, payload, tenant_name):

    user_type=payload.get("user_type")
    username = payload.get("preferred_username")
    client_type=payload.get("client_type")
    if user_type:
        user_id=None
        if not username and user_type=="agent":
            user_id=payload.get("azp")
        else:
            user_id=username
        if user_type=="agent":
            if get_agent_by_agent_id(sess, user_id, tenant_name):
                return True
            else:
                return False

        else:    
            if get_user_by_username(sess, user_id, tenant_name):
                return True
            else:
                return False

    else:
        agent_id=None
        if client_type =="agent":
            agent_id=payload.get("client_id")
        else:
            agent_id=payload.get("x_agent_id")
        if get_agent_by_agent_id(sess, agent_id, tenant_name):
            return True
        else:
            return False            
    return False

def validate_agent_id(sess, payload, agent_id):

    user_type=payload.get("user_type")
    client_type=payload.get("client_type")
    scope=payload.get("scope")
    username = payload.get("preferred_username")

    if user_type=="agent" and username==agent_id:
        return True
    elif user_type=="human":

        agents = get_agents_by_username(sess, username)
        if not agents:
            return False

        for agent in agents:
            if agent.get("agent_id")==agent_id:
                return True
        return False
    elif client_type=="agent" and payload.get("azp")== agent_id:    
        return True
    else:
        return False
    

