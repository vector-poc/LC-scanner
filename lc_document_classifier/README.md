# LC Document Classifier - LangGraph Studio Project

A LangGraph-powered document classification system that automatically assigns documents to Letter of Credit (LC) requirements using semantic matching and LLM-powered analysis.

## 🏗️ Architecture

This project implements a state-driven workflow using LangGraph that:

1. **Extracts** LC document requirements from existing LC analysis
2. **Classifies** input documents against each LC requirement 
3. **Assigns** documents to requirements based on content matching
4. **Validates** assignments using LLM reasoning
5. **Reports** final classification results

## 📁 Project Structure

```
lc_document_classifier/
├── lc_classifier/
│   ├── __init__.py          # Package initialization
│   ├── state.py             # Graph state definitions
│   ├── nodes.py             # Graph node implementations  
│   ├── utils.py             # Helper functions and LLM classifier
│   └── graph.py             # Main graph definition
├── .env                     # Environment variables
├── langgraph.json           # LangGraph Studio configuration
├── test_classifier.py       # Test runner script
├── USAGE.md                 # Usage guide
└── README.md               # This file
```

## 🎯 Graph Flow

```
START → initialize_state → get_next_requirement → classify_documents → record_assignment → check_completion
                                    ↑                                                          |
                                    |__________(if more requirements)_____________________|
                                                                                             |
                                                                                             ↓
                                                                                    format_results → END
```

## 🚀 Getting Started

### Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r ../requirements.txt
   pip install langgraph-cli
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

### Development with LangGraph Studio

1. **Start LangGraph Studio**:
   ```bash
   cd lc_document_classifier
   langgraph dev
   ```

2. **Open Studio**: Navigate to http://localhost:8123 in your browser

3. **Select Graph**: Choose "document_classifier" from the available graphs

4. **Test the Graph**: Use the Studio interface to:
   - Input sample LC data and documents
   - Step through the graph execution
   - Inspect state at each node
   - Debug classification logic

### Command Line Testing

Run the test script to verify the setup:

```bash
python test_classifier.py
```

This will:
- Load sample LC data from the existing output
- Create mock input documents
- Run the classification graph
- Display detailed results

## 📊 Input/Output Format

### Input
```python
{
    "extracted_lc": {
        "DOCUMENTS_REQUIRED": [
            {
                "name": "Commercial Invoice",
                "description": "Invoice requirements...",
                "quantity": 1,
                "validation_criteria": [...]
            }
        ]
    },
    "input_documents": [
        {
            "name": "invoice.pdf",
            "summary": "Commercial invoice summary",
            "full_text": "Full document content..."
        }
    ]
}
```

### Output
```python
{
    "final_assignments": {
        "Commercial Invoice": ["invoice.pdf"],
        "Bill of Lading": [],  # No match found
    },
    "classification_results": [...],  # Detailed results
    "processing_complete": true,
    "errors": []
}
```

## 🔧 Configuration

### LLM Settings
- **Model**: `google/gemini-2.0-flash-001` (via OpenRouter)
- **Temperature**: 0.1 (low for consistent classification)
- **Max Tokens**: 2000

### Graph Settings
- **Checkpointer**: MemorySaver (for Studio debugging)
- **State Management**: TypedDict with reducers
- **Error Handling**: Graceful failure with error tracking

## 🎯 Classification Logic

The system uses LLM-powered semantic matching to:

1. **Analyze** document content against LC requirements
2. **Compare** validation criteria with document features
3. **Score** confidence levels (0.0 - 1.0) for matches
4. **Reason** about classification decisions
5. **Filter** out false positives with strict matching

## 🚀 Integration

### With Existing LC Extraction
```python
from lc_classifier.graph import run_classification

# Use with existing LC extraction results
lc_data = extract_lc_from_pdf("letter_of_credit.pdf")
documents = [
    {"name": "doc1.pdf", "summary": "...", "full_text": "..."}
]

results = run_classification(lc_data, documents)
```

### API Integration
The graph can be deployed as an API using LangGraph Platform or custom FastAPI wrapper.

## 🔍 Debugging

### LangGraph Studio Features
- **Visual Graph**: See execution flow in real-time
- **State Inspector**: Monitor state changes at each node  
- **Breakpoints**: Pause execution for detailed analysis
- **Time Travel**: Replay and modify past executions

### Logging
Each node provides detailed console output for tracking:
- Requirements processing progress
- Document classification results  
- Assignment statistics
- Error reporting

## 📈 Performance

- **Concurrency**: Processes one requirement at a time (sequential)
- **Memory**: Uses state reducers for efficient accumulation
- **Caching**: MemorySaver enables replay and debugging
- **Scalability**: Can be extended for parallel processing

## 🔒 Security

- **API Keys**: Stored in environment variables
- **Content**: Documents processed in-memory only
- **Logging**: No sensitive data in logs
- **Validation**: Input validation for all documents

## 🤝 Contributing

1. Use LangGraph Studio for development
2. Test changes with `test_classifier.py`
3. Follow existing node patterns
4. Update state management as needed

## 📝 License

This project extends the existing LC-scanner codebase.