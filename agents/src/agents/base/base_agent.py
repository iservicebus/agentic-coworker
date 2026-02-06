import inspect
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)
from warnings import warn

from langchain_core.language_models import (
    BaseChatModel,
    LanguageModelLike,
)
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import (
    Runnable,
    RunnableBinding,
    RunnableConfig,
    RunnableSequence,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from typing_extensions import Annotated, NotRequired, TypedDict

from langgraph._internal._runnable import RunnableCallable, RunnableLike
from langgraph._internal._typing import MISSING
from langgraph.errors import ErrorCode, create_error_message
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, Send
from langgraph.warnings import LangGraphDeprecatedSinceV10

StructuredResponse = Union[dict, BaseModel]
StructuredResponseSchema = Union[dict, type[BaseModel]]
F = TypeVar("F", bound=Callable[..., Any])


# We create the AgentState that we will pass around
# This simply involves a list of messages
# We want steps to return messages to append to the list
# So we annotate the messages attribute with `add_messages` reducer
class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    remaining_steps: NotRequired[RemainingSteps]

class AgentStatePydantic(BaseModel):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    remaining_steps: RemainingSteps = 25


class AgentStateWithStructuredResponse(AgentState):
    """The state of the agent with a structured response."""

    structured_response: StructuredResponse


class AgentStateWithStructuredResponsePydantic(AgentStatePydantic):
    """The state of the agent with a structured response."""
    structured_response: StructuredResponse


StateSchema = TypeVar("StateSchema", bound=Union[AgentState, AgentStatePydantic])
StateSchemaType = Type[StateSchema]



def _should_bind_tools(
    model: LanguageModelLike, tools: Sequence[BaseTool], num_builtin: int = 0
) -> bool:
    if isinstance(model, RunnableSequence):
        model = next(
            (
                step
                for step in model.steps
                if isinstance(step, (RunnableBinding, BaseChatModel))
            ),
            model,
        )

    if not isinstance(model, RunnableBinding):
        return True

    if "tools" not in model.kwargs:
        return True

    bound_tools = model.kwargs["tools"]
    if len(tools) != len(bound_tools) - num_builtin:
        raise ValueError(
            "Number of tools in the model.bind_tools() and tools passed to create_react_agent must match"
            f" Got {len(tools)} tools, expected {len(bound_tools) - num_builtin}"
        )

    tool_names = set(tool.name for tool in tools)
    bound_tool_names = set()
    for bound_tool in bound_tools:
        # OpenAI-style tool
        if bound_tool.get("type") == "function":
            bound_tool_name = bound_tool["function"]["name"]
        # Anthropic-style tool
        elif bound_tool.get("name"):
            bound_tool_name = bound_tool["name"]
        else:
            # unknown tool type so we'll ignore it
            continue

        bound_tool_names.add(bound_tool_name)

    if missing_tools := tool_names - bound_tool_names:
        raise ValueError(f"Missing tools '{missing_tools}' in the model.bind_tools()")

    return False


class BaseAgent:
    def __init__(self, model: BaseChatModel,     
                 tools: Union[Sequence[Union[BaseTool, Callable, dict[str, Any]]], ToolNode],
                response_format: Optional[
                    Union[StructuredResponseSchema, tuple[str, StructuredResponseSchema]]
                ] = None,
                state_schema: Optional[StateSchemaType] = None,
                context_schema: Optional[Type[Any]] = None,

                debug: bool = False,
                name: Optional[str] = None ):

        self.graph: StateGraph=None
        self.tools=tools
        self.response_format=response_format
        self.name=name
        self.debug=debug
        self.context_schema=context_schema
        self.model=model

        if state_schema is not None:
            required_keys = {"messages", "remaining_steps"}
        if response_format is not None:
            required_keys.add("structured_response")
        if state_schema:
            schema_keys = set(get_type_hints(state_schema))
            if missing_keys := required_keys - set(schema_keys):
                raise ValueError(f"Missing required key(s) {missing_keys} in state_schema")

        if state_schema is None:
            self.state_schema = (
                AgentStateWithStructuredResponse
                if response_format is not None
                else AgentState
            )
        else:
            self.state_schema=state_schema    

        self._set_tool_node(tools)

    def _set_tool_node(self, tools: Union[Sequence[Union[BaseTool, Callable, dict[str, Any]]], ToolNode]):
        llm_builtin_tools: list[dict] = []
        if isinstance(tools, ToolNode):
            self.tool_classes = list(tools.tools_by_name.values())
            self.tool_node = tools
        else:
            llm_builtin_tools = [t for t in tools if isinstance(t, dict)]
            self.tool_node = ToolNode([t for t in tools if not isinstance(t, dict)])
            self.tool_classes = list(self.tool_node.tools_by_name.values())


        self.tool_calling_enabled = len(self.tool_classes) > 0

        if (
             _should_bind_tools(self.model, self.tool_classes, num_builtin=len(llm_builtin_tools))  # type: ignore[arg-type]
             and len(self.tool_classes + llm_builtin_tools) > 0
         ):
             self.model = cast(BaseChatModel, self.model).bind_tools(
                 self.tool_classes + llm_builtin_tools  # type: ignore[operator]
             )


    def _get_state_value(self, state: StateSchema, key: str, default: Any = None) -> Any:
        return (
            state.get(key, default)
            if isinstance(state, dict)
            else getattr(state, key, default)
        )


    def _validate_chat_history(self, messages: Sequence[BaseMessage]) -> None:
        """Validate that all tool calls in AIMessages have a corresponding ToolMessage."""
        all_tool_calls = [
            tool_call
            for message in messages
            if isinstance(message, AIMessage)
            for tool_call in message.tool_calls
        ]
        tool_call_ids_with_results = {
            message.tool_call_id for message in messages if isinstance(message, ToolMessage)
        }
        tool_calls_without_results = [
            tool_call
            for tool_call in all_tool_calls
            if tool_call["id"] not in tool_call_ids_with_results
        ]
        if not tool_calls_without_results:
            return

        error_message = create_error_message(
            message="Found AIMessages with tool_calls that do not have a corresponding ToolMessage. "
            f"Here are the first few of those tool calls: {tool_calls_without_results[:3]}.\n\n"
            "Every tool call (LLM requesting to call a tool) in the message history MUST have a corresponding ToolMessage "
            "(result of a tool invocation to return to the LLM) - this is required by most LLM providers.",
            error_code=ErrorCode.INVALID_CHAT_HISTORY,
        )
        raise ValueError(error_message)


    def _get_model_input_state(self, state: StateSchema) -> StateSchema:
        messages = self._get_state_value(state, "messages")
        error_msg = (
            f"Expected input to call_model to have 'messages' key, but got {state}"
        )

        if messages is None:
            raise ValueError(error_msg)

        self._validate_chat_history(messages)
        # we're passing messages under `messages` key, as this is expected by the prompt
        if isinstance(self.state_schema, type) and issubclass(self.state_schema, BaseModel):
            state.messages = messages  # type: ignore
        else:
            state["messages"] = messages  # type: ignore

        return state

    async def call_model(self, state: StateSchema, config: RunnableConfig
    ) -> StateSchema:
        model_input = self._get_model_input_state(state)
        messages = self._get_state_value(model_input, "messages")

        response = cast(AIMessage, await self.model.ainvoke(messages, config))  # type: ignore[arg-type]

        # add agent name to the AIMessage
        response.name = self.name
        return {"messages": [response]}


    async def generate_structured_response(self,
        state: StateSchema, config: RunnableConfig
    ) -> StateSchema:
        messages = self._get_state_value(state, "messages")
        structured_response_schema = self.response_format
        if isinstance(self.response_format, tuple):
            system_prompt, structured_response_schema = self.response_format
            messages = [SystemMessage(content=system_prompt)] + list(messages)

        model_with_structured_output = self.model.with_structured_output(
            cast(StructuredResponseSchema, structured_response_schema)
        )
        response = await model_with_structured_output.ainvoke(messages, config)
        return {"structured_response": response}


    # Define the function that determines whether to continue or not
    async def should_continue(self, state: StateSchema) -> Union[str, list[Send]]:
        messages = self._get_state_value(state, "messages")
        last_message = messages[-1]
        # If there is no function call, then we finish
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            if self.response_format is not None:
                return "generate_structured_response"
            else:
                return END
        # Otherwise if there is, we continue
        else:
                return "tools"
        
    async def build(self,
                checkpointer: Optional[Checkpointer] = None,
                store: Optional[BaseStore] = None,
                interrupt_before: Optional[list[str]] = None,
                interrupt_after: Optional[list[str]] = None,
    
                    ):

        # Define a new graph
        self.graph = StateGraph(
            state_schema=self.state_schema or AgentState, context_schema=self.context_schema
        )

        # Define the two nodes we will cycle between
        self.graph.add_node(
            "llm",
            self.call_model,
        )
        self.graph.add_node("tools", self.tool_node)

        entrypoint = "llm"

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        self.graph.set_entry_point(entrypoint)

        agent_paths = []

        agent_paths.append("tools")

        # Add a structured output node if response_format is provided
        if self.response_format is not None:
            self.graph.add_node(
                "generate_structured_response",
                self.generate_structured_response,
            )
            agent_paths.append("generate_structured_response")
        else:
            agent_paths.append(END)

        self.graph.add_conditional_edges(
            "llm",
            self.should_continue,
            path_map=agent_paths,
        )
        self.graph.add_edge("tools", entrypoint)

        self.graph=self.graph.compile(
            checkpointer=checkpointer,
            store=store,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            debug=self.debug,
            name=self.name,
        )
        return self

    from langgraph.typing import ContextT, InputT, OutputT, StateT
    from langgraph.types import (
        All,
        Command,
        Durability,
        StreamMode,
    )
    async def ainvoke(
        self,
        input: InputT | Command | None,
        config: RunnableConfig | None = None,
        *,
        context: ContextT | None = None,
        stream_mode: StreamMode = "values",
        print_mode: StreamMode | Sequence[StreamMode] = (),
        output_keys: str | Sequence[str] | None = None,
        interrupt_before: All | Sequence[str] | None = None,
        interrupt_after: All | Sequence[str] | None = None,
        durability: Durability | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | Any:
        return await self.graph.ainvoke(
            input=input,
            config=config,
            context=context,
            stream_mode=stream_mode,
            print_mode=print_mode,
            output_keys=output_keys,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            durability=durability,
            **kwargs,
        )

    def invoke(
        self,
        input: InputT | Command | None,
        config: RunnableConfig | None = None,
        *,
        context: ContextT | None = None,
        stream_mode: StreamMode = "values",
        print_mode: StreamMode | Sequence[StreamMode] = (),
        output_keys: str | Sequence[str] | None = None,
        interrupt_before: All | Sequence[str] | None = None,
        interrupt_after: All | Sequence[str] | None = None,
        durability: Durability | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | Any:
        return self.graph.invoke(
            input=input,
            config=config,
            context=context,
            stream_mode=stream_mode,
            print_mode=print_mode,
            output_keys=output_keys,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            durability=durability,
            **kwargs,
        )
