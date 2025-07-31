# 🎯 LangGraph Studio Project Structure - Simple Guide

## 📁 Basic Project Structure

```
my-project/
├── 📂 my_agent/              # Your main code folder
│   ├── 📂 utils/            # Helper functions
│   │   ├── __init__.py      
│   │   ├── tools.py         # External tools (APIs, databases)
│   │   ├── nodes.py         # Graph node functions  
│   │   └── state.py         # Data structure definitions
│   ├── __init__.py
│   ├── agent.py             # Main graph construction
│   └── requirements.txt     # Python packages needed
├── 📄 .env                  # Secret keys & settings
└── 📄 langgraph.json        # Studio configuration
```

## 🧩 Key Components Explained

### 1. **`langgraph.json`** - The Brain 🧠
```json
{
  "dependencies": ["."],
  "graphs": {
    "my_agent": "./my_agent/agent.py:graph"
  },
  "env": ".env"
}
```
- **What it does**: Tells Studio where to find your graph
- **Key parts**:
  - `dependencies`: What to install
  - `graphs`: Maps name → file location
  - `env`: Where your API keys live

### 2. **`.env`** - Your Secrets 🔐
```bash
OPENAI_API_KEY=your-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=my-project
```
- **What it does**: Stores API keys and settings
- **Important**: Never commit this to git!

### 3. **`state.py`** - Your Data Structure 📊
```python
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    user_input: str
    result: str
```
- **What it does**: Defines what data flows through your graph
- **Think of it as**: The "variables" your graph uses

### 4. **`nodes.py`** - Your Functions ⚙️
```python
def process_user_input(state: AgentState):
    # Do something with the input
    return {"result": "processed!"}

def generate_response(state: AgentState):
    # Generate AI response
    return {"messages": [response]}
```
- **What it does**: Individual steps in your workflow
- **Think of it as**: The "actions" your graph performs

### 5. **`tools.py`** - External Connections 🔌
```python
def search_web(query: str):
    # Call external API
    return results

def query_database(question: str):
    # Query your database
    return data
```
- **What it does**: Connects to outside services
- **Examples**: Web search, database queries, file operations

### 6. **`agent.py`** - The Graph Builder 🏗️
```python
from langgraph.graph import StateGraph, START, END

# Create the graph
workflow = StateGraph(AgentState)

# Add your functions as nodes
workflow.add_node("process", process_user_input)
workflow.add_node("generate", generate_response)

# Connect them
workflow.add_edge(START, "process")
workflow.add_edge("process", "generate")
workflow.add_edge("generate", END)

# Export for Studio
graph = workflow.compile()
```
- **What it does**: Connects all your nodes into a workflow
- **Think of it as**: The "recipe" that combines everything

## 🚀 Getting Started - 3 Steps

### Step 1: Create Your Project
```bash
# Option A: Use template
langgraph new --template=new-langgraph-project-python my_project

# Option B: Manual setup
mkdir my_project
cd my_project
```

### Step 2: Set Up Your Files
1. **Create `langgraph.json`** (tells Studio about your graph)
2. **Create `.env`** (add your API keys)
3. **Build your graph** in the code folder

### Step 3: Start Studio
```bash
# Install CLI
pip install -U "langgraph-cli[inmem]"

# Start Studio
langgraph dev

# For Safari/Brave browsers
langgraph dev --tunnel
```

## 🎨 How Studio Works

1. **Studio reads** your `langgraph.json`
2. **Finds your graph** in the specified file
3. **Loads your environment** from `.env`
4. **Shows visual interface** at http://localhost:2024
5. **Let's you test** your graph step by step

## 💡 Think of It Like This

- **LangGraph** = Your workflow engine
- **Studio** = Visual interface to see/test your workflow
- **Your Project** = The specific workflow you built
- **Nodes** = Individual tasks/functions
- **State** = Data that flows between tasks
- **Graph** = How tasks connect together

## 🔧 Your Current Project Structure

```
lc_document_classifier/
├── 📂 lc_classifier/        # Your agent code
│   ├── graph.py            # Graph definition
│   ├── nodes.py            # Processing steps
│   ├── state.py            # Data structure
│   └── utils.py            # Helper functions
├── 📄 graph_wrapper.py     # Studio-compatible export
├── 📄 langgraph.json       # Studio config
├── 📄 .env                 # Your API keys
└── 📄 test_classifier.py   # Test script
```

## 🎯 Quick Commands Reference

```bash
# Create new project
langgraph new --template=new-langgraph-project-python my_project

# Install CLI
pip install -U "langgraph-cli[inmem]"

# Start Studio (regular)
langgraph dev

# Start Studio (Safari/Brave compatible)
langgraph dev --tunnel

# Test your graph
python test_classifier.py
```

## ✅ What You Need to Do Next

1. **Add your OpenRouter API key** to `.env`
2. **Run**: `langgraph dev --tunnel` (for Safari/Brave)
3. **Open the Studio URL** shown in terminal
4. **Explore your graph** visually!

---
*Your graph logic works perfectly - Studio just needs the right API key to run the LLM calls! 🎉*