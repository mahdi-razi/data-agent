import os
from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.prebuilt import ToolNode, tools_condition
from tools import get_schema, load_query, run_python, profiler, load_skill
from prompts import SYSTEM_PROMPT
from langgraph.errors import GraphRecursionError


RECURSION_LIMIT = 30
TRIM_MAX_TOKENS = 5000
NUM_CTX = 8192
MODEL = "gemma4:12b"
CHECKPOINT_DATABASE_URL = os.environ["CHECKPOINT_DATABASE_URL"]


def build_graph(llm, checkpointer):
    tools = [get_schema, load_query, profiler, run_python, load_skill]
    llm_with_tools = llm.bind_tools(tools)

    def assistant(state: MessagesState):
        recent = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=TRIM_MAX_TOKENS,
            start_on="human",
            include_system=False,
        )
        reply = llm_with_tools.invoke([SystemMessage(SYSTEM_PROMPT)] + recent)
        return {"messages": [reply]}

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))

    graph.add_edge(START, "assistant")
    graph.add_conditional_edges("assistant", tools_condition)
    graph.add_edge("tools", "assistant")

    return graph.compile(checkpointer=checkpointer)


def ask_project_name():
    while True:
        name = input("project name> ").strip().lower()
        if name and name.replace("_", "").replace("-", "").isalnum():
            return name
        print("Use only letters, digits, - and _.")


def main():
    with PostgresSaver.from_conn_string(CHECKPOINT_DATABASE_URL) as checkpointer:
        checkpointer.setup()
        llm = ChatOllama(model=MODEL, num_ctx=NUM_CTX, temperature=0)
        graph = build_graph(llm, checkpointer)

        try:
            project = ask_project_name()
        except (KeyboardInterrupt, EOFError):
            return
        config = {
            "configurable": {"thread_id": project},
            "recursion_limit": RECURSION_LIMIT,
        }

        print(f"Project: {project}. Ctrl+C to quit.")
        while True:
            try:
                user_text = input("\nyou> ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_text:
                continue
            
            try:
                for state in graph.stream({"messages": [HumanMessage(user_text)]}, config, stream_mode="values"):
                    state["messages"][-1].pretty_print()
            except GraphRecursionError:
                print("\nagent> I got stuck in a loop and stopped. Try a simpler or more specific question.")
            except KeyboardInterrupt:
                print("\nagent> Stopped.")


if __name__ == "__main__":
    main()