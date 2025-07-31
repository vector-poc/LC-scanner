# LangGraph Studio Usage Guide

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Ensure you're in the LC-scanner project directory
cd /Users/shaveensilva/Projects/LC-scanner

# Install dependencies (if not already done)
pip install -r requirements.txt

# Navigate to the classifier project
cd lc_document_classifier

# Set up your API keys in .env
# Edit the .env file and add your OPENROUTER_API_KEY
```

### 2. Start LangGraph Studio
```bash
# Start the development server
langgraph dev

# This will start the server on http://localhost:8080
# Open your browser and navigate to that URL
```

### 3. Using the Studio Interface

1. **Select Graph**: Choose "document_classifier" from the dropdown
2. **Input Data**: Provide sample input in JSON format:

```json
{
  "extracted_lc": {
    "DOCUMENTS_REQUIRED": [
      {
        "name": "Commercial Invoice",
        "description": "Invoice showing goods and pricing",
        "quantity": 1,
        "validation_criteria": ["Must be signed", "Must show LC number"]
      }
    ]
  },
  "input_documents": [
    {
      "name": "invoice.pdf",
      "summary": "Commercial invoice for vehicle export",
      "full_text": "COMMERCIAL INVOICE\nInvoice No: INV-001\nLC No: DB5032LC2503324..."
    }
  ]
}
```

3. **Run Graph**: Click execute to start the classification process
4. **Monitor Progress**: Watch each node execute in real-time
5. **Inspect State**: Click on any node to see the state at that point
6. **Debug Issues**: Use breakpoints and step-through debugging

## 🧪 Command Line Testing

Run the test script to verify everything works:

```bash
python test_classifier.py
```

This will:
- Load real LC data from your existing output
- Create sample documents
- Run the classification graph
- Show detailed results

## 📊 Expected Output

The graph will process documents through these stages:

1. **Initialize State**: Extract LC requirements and validate inputs
2. **Get Next Requirement**: Select next LC document requirement
3. **Classify Documents**: Use LLM to match documents to requirement
4. **Record Assignment**: Store the classification result
5. **Check Completion**: Loop until all requirements processed
6. **Format Results**: Create final assignment mapping

Final output format:
```json
{
  "final_assignments": {
    "Commercial Invoice": ["invoice.pdf"],
    "Bill of Lading": ["bill_lading.pdf"],
    "Insurance Certificate": []
  },
  "classification_results": [...],
  "processing_complete": true,
  "errors": []
}
```

## 🔧 Studio Features

### Graph Visualization
- **Real-time Flow**: See execution path as it happens
- **Node States**: Inspect state changes at each step
- **Error Tracking**: Identify where issues occur

### Debugging Tools
- **Breakpoints**: Pause execution at specific nodes
- **State Inspector**: Examine all state variables
- **Time Travel**: Replay and modify past executions
- **Logs**: View detailed console output

### Iteration Workflow
1. **Test**: Run with sample data
2. **Debug**: Identify classification issues
3. **Modify**: Adjust prompts or logic in code
4. **Reload**: Hot reload detects changes
5. **Repeat**: Test again with improvements

## 🎯 Customization

### Modifying Classification Logic
Edit `lc_classifier/utils.py`:
- Adjust LLM prompts for better accuracy
- Change confidence thresholds
- Add custom validation rules

### Adding New Nodes
1. Create node function in `lc_classifier/nodes.py`
2. Add to graph in `lc_classifier/graph.py`
3. Update state if needed in `lc_classifier/state.py`

### Changing LLM Model
Update `lc_classifier/utils.py`:
```python
# Change model in DocumentClassifierLLM
model = "anthropic/claude-3-haiku"  # or other models
```

## 🔍 Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure you're in the right directory
   - Check Python path in scripts

2. **API Key Issues**
   - Verify OPENROUTER_API_KEY in .env
   - Check API key permissions

3. **Studio Connection Problems**
   - Try different port: `langgraph dev --port 8123`
   - Use tunnel for Safari: `langgraph dev --tunnel`

4. **Graph Loading Errors**
   - Check langgraph.json syntax
   - Verify graph.py exports 'graph' variable

### Debug Commands
```bash
# Validate configuration
langgraph dockerfile test.dockerfile

# Check imports
python -c "import lc_classifier.graph; print('OK')"

# Test classification without Studio
python test_classifier.py
```

## 📈 Performance Tips

- **Batch Processing**: Process multiple documents efficiently
- **Caching**: Use checkpointer for replay functionality
- **Monitoring**: Watch LLM API usage and costs
- **Optimization**: Adjust prompt lengths for speed vs accuracy

## 🔐 Security Notes

- API keys stored in .env (not committed to git)
- Document content processed in-memory only
- No persistent storage of sensitive data
- LLM calls go through secure OpenRouter proxy