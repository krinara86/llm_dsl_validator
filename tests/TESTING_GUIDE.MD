# LLM Testing Guide

## Setup

1. Place `pytest.ini` in your project root directory
2. Place `test_llm_real.py` in your `tests/` directory

## Running Tests

### Run normal tests (excluding LLM tests)
```bash
# This is the default - LLM tests are automatically excluded
pytest tests/

# Or explicitly exclude
pytest tests/ -m "not llm_tests"
```

### Run ONLY LLM tests
```bash
# Run all LLM tests
pytest tests/test_llm_real.py -m llm_tests -v

# Run with detailed output
pytest tests/test_llm_real.py -m llm_tests -v -s

# Run specific test class
pytest tests/test_llm_real.py::TestLLMExtraction -v -s

# Run specific test
pytest tests/test_llm_real.py::TestLLMExtraction::test_simple_create_extraction_consistency -v -s
```

### Run ALL tests including LLM tests
```bash
# Override the default marker exclusion
pytest tests/ -m "" -v

# Or explicitly include
pytest tests/ --no-markers
```

### Run only slow tests
```bash
pytest tests/ -m "slow" -v
```

### Run benchmark tests
```bash
pytest tests/ -m "benchmark" -v
```

## Configuration Options

### Change the LLM model
Edit `test_llm_real.py` and modify:
```python
self.model = "llama3:8b"  # Change to your model
```

### Adjust test parameters
```python
self.num_runs = 3  # Number of times to run each test
self.success_threshold = 0.66  # Success rate required to pass
```

## Test Strategies Explained

### 1. **Multiple Runs with Statistical Validation**
- Each test runs 3 times by default
- Success if 2/3 runs pass (66% threshold)
- Handles non-deterministic nature of LLMs

### 2. **Consistency Testing**
- Tests if similar queries produce similar results
- Validates paraphrase invariance
- Measures action consistency across variations

### 3. **Robustness Testing**
- Typo tolerance
- Edge case handling
- Performance under different query complexities

### 4. **Performance Metrics**
- Response time distribution
- Statistical analysis (mean, median, std dev)
- Performance vs query complexity

## Interpreting Results

### Success Rates
- **90-100%**: Excellent - pattern works reliably
- **70-90%**: Good - pattern works most of the time
- **50-70%**: Acceptable - pattern needs refinement
- **Below 50%**: Poor - avoid this pattern

### Performance Metrics
- **< 1s**: Excellent response time
- **1-3s**: Acceptable for most use cases
- **3-5s**: May feel slow to users
- **> 5s**: Too slow for interactive use

## Best Practices

1. **Run before demos** to validate your LLM is working
2. **Run after model changes** to ensure compatibility
3. **Run with different models** to find the best one
4. **Collect metrics over time** to track improvements
5. **Adjust thresholds** based on your requirements

## Troubleshooting

### "LLM not available" errors
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Or start Ollama
ollama serve
```

### Tests timing out
- Increase timeout in pytest: `pytest --timeout=300`
- Reduce `num_runs` in test setup
- Check LLM server load

### Low success rates
- Try different prompt patterns
- Adjust temperature settings
- Use a more capable model
- Check if model is appropriate for task

## Example Output
```
[Simple Create] Success rate: 100.0%
Results: {
  "action": "create_venue",
  "parameters": {"name": "Conference Hall"}
}

[Numeric: 25] Success rate: 66.7%
[Numeric: 100] Success rate: 100.0%
[Numeric: 500] Success rate: 66.7%

[Performance: 12 chars]
  Average: 0.85s
  Median: 0.82s
  Std Dev: 0.12s
```