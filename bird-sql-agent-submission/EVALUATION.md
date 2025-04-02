# Evaluating the Multi-Agent Text-to-SQL System

This document provides instructions on how to evaluate the multi-agent system on the BIRD-SQL Mini-Dev benchmark.

## Prerequisites

- Ensure you have installed all dependencies as described in the README.md
- Make sure Ollama is running and you have pulled the required model: `ollama pull llama3`
- Ensure the BIRD Mini-Dev dataset is downloaded and extracted

## Running the Evaluation

The evaluation process involves the following steps:

1. **Initial Small-Scale Test** (5 samples):
   ```bash
   python main.py --mode evaluate --sample_size 5 --results_file initial_results.json
   ```
   This will run the evaluation on 5 examples and save the results to `initial_results.json`. The script will also generate a visualization of the accuracy in `accuracy_results.png`.

2. **Analyze Errors and Optimize Prompts**:
   ```bash
   python main.py --mode optimize --results_file initial_results.json
   ```
   This will analyze the error patterns from the initial evaluation, enhance the prompts with successful examples, and save the enhanced prompts to `enhanced_prompts.py`.

3. **Update Agent Prompts**:
   Edit `agent_system.py` to replace the original prompts with the enhanced ones from `enhanced_prompts.py`.

4. **Re-Run Evaluation with Improved Prompts**:
   ```bash
   python main.py --mode evaluate --sample_size 10 --results_file optimized_results.json
   ```
   This will run the evaluation with the optimized prompts on 10 examples.

5. **Full Evaluation** (after you're confident in the system):
   ```bash
   python main.py --mode evaluate --sample_size 50 --results_file final_results.json
   ```
   Running on 50 examples will provide a more comprehensive assessment.

## Achieving 60%+ Accuracy

To reach the target accuracy of 60% or higher:

1. **Use Better Models**:
   - Try different models available in Ollama: 
     ```bash
     ollama pull mistral
     python main.py --mode evaluate --sample_size 10 --model mistral
     ```

2. **Iterative Optimization**:
   - Run multiple rounds of evaluation and prompt optimization
   - Each time, analyze error patterns and enhance prompts accordingly

3. **Focus on Common Error Types**:
   - Pay special attention to fixing common error patterns like:
     - Missing JOIN conditions
     - Date formatting errors
     - Conditional logic issues
     - Aggregation and GROUP BY errors

4. **Add Domain-Specific Knowledge**:
   - Enhance prompts with domain-specific knowledge about SQL dialects and the database schemas

## Evaluation Metrics

The system currently evaluates based on **execution accuracy**, meaning the query is considered correct if it produces the same results as the gold query when executed against the database.

Other evaluation metrics used in the BIRD Mini-Dev benchmark:
- **R-VES** (Reward-based Valid Efficiency Score): Measures query efficiency
- **Soft F1-Score**: Measures similarity between result tables

## Troubleshooting

- **Ollama Connection Issues**: Ensure Ollama is running and the model is pulled with `ollama pull <model>` 
- **Database Path Issues**: Verify the paths to the databases and JSON files are correct
- **Memory Issues**: If encountering memory problems with larger evaluations, try reducing batch sizes

## Example Output

A successful evaluation should produce output like:

```
Evaluating multi-agent system on BIRD Mini-Dev benchmark...
Processing question 1/50:
Question: What is the ratio of customers who pay in EUR against customers who pay in CZK?
[1/3] Running Selector Agent to identify relevant schema elements...
✓ Selector completed
[2/3] Running Decomposer Agent to generate SQL...
✓ Decomposer completed
[3/3] Running Refiner Agent to validate and fix the SQL...
✓ Refiner completed
Gold SQL: SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) AS ratio FROM customers
Predicted SQL: SELECT CAST(SUM(CASE WHEN Currency = 'EUR' THEN 1 ELSE 0 END) AS FLOAT) / SUM(CASE WHEN Currency = 'CZK' THEN 1 ELSE 0 END) AS ratio FROM customers
✓ Results match!

...

Evaluation complete. Accuracy: 64.00%
```

## Advanced Configuration

For more advanced configuration, you can:

- Modify the agent prompts in `agent_system.py`
- Adjust the evaluation parameters in `evaluate.py`
- Change the model temperature and other parameters in `create_agents()` 