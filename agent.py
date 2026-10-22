import os
from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from tools import get_schema, load_query, run_python
from prompts import SYSTEM_PROMPT


MODEL = "gemma4:12b"
CHECKPOINT_DATABASE_URL = os.environ["CHECKPOINT_DATABASE_URL"]


def build_graph(llm, checkpointer):
    tools = [get_schema, load_query, run_python]
    llm_with_tools = llm.bind_tools(tools)

    def assistant(state: MessagesState):
        reply = llm_with_tools.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])
        return {"messages": [reply]}

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(tools))

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
        llm = ChatOllama(model=MODEL, temperature=0)
        graph = build_graph(llm, checkpointer)

        try:
            project = ask_project_name()
        except (KeyboardInterrupt, EOFError):
            return
        config = {"configurable": {"thread_id": project}}

        print(f"Project: {project}. Ctrl+C to quit.")
        while True:
            try:
                user_text = input("\nyou> ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_text:
                continue

            for state in graph.stream({"messages": [HumanMessage(user_text)]}, config, stream_mode="values"):
                state["messages"][-1].pretty_print()


if __name__ == "__main__":
    main()