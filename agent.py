import os
from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from tools import get_schema, load_query, run_python
from prompts import SYSTEM_PROMPT


MODEL = "gemma4:12b"


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


def main():
    llm = ChatOllama(model=MODEL, temperature=0)
    graph = build_graph(llm, MemorySaver())
    config = {"configurable": {"thread_id": "default"}}

    print("Ctrl+C to quit.")
    while True:
        try:
            user_text = input("\nyou> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_text:
            continue

        result = graph.invoke({"messages": [HumanMessage(user_text)]}, config)
        print("\nagent>", result["messages"][-1].content)


if __name__ == "__main__":
    main()