import json
import os
import sys
from utils import execute_query

def test_evaluation(data_file, db_root, sample_size=3):
    """Simplified evaluation test."""
    print(f"Running simplified evaluation test on {sample_size} samples...")
    
    # Load the benchmark data
    with open(data_file, 'r') as f:
        benchmark_data = json.load(f)
    
    # Limit to sample size
    benchmark_data = benchmark_data[:sample_size]
    
    # Initialize results tracking
    results = {
        "correct": 0,
        "total": len(benchmark_data),
        "details": []
    }
    
    # Process each question
    for idx, item in enumerate(benchmark_data):
        print(f"\nProcessing question {idx+1}/{len(benchmark_data)}:")
        question = item["question"]
        print(f"Question: {question}")
        
        db_id = item["db_id"]
        db_path = os.path.join(db_root, db_id, f"{db_id}.sqlite")
        gold_query = item["SQL"]
        evidence = item.get("evidence", "")
        
        print(f"Database: {db_id}")
        print(f"Gold SQL: {gold_query}")
        
        # Execute gold query
        gold_results = execute_query(db_path, gold_query)
        if "error" in gold_results:
            print(f"Error executing gold query: {gold_results['error']}")
            continue
        
        print(f"Gold Results: {gold_results['results'][:3]}")
        print("✓ Query executed successfully!")
        results["correct"] += 1
        
        # Store results
        results["details"].append({
            "question": question,
            "db_id": db_id,
            "gold_query": gold_query,
            "gold_results": str(gold_results.get("results", [])[:3])
        })
    
    # Calculate accuracy (in a real evaluation, this would be compared with actual predictions)
    accuracy = (results["correct"] / results["total"]) * 100
    results["accuracy"] = accuracy
    
    print(f"\nTest evaluation complete. {results['correct']}/{results['total']} queries executed successfully.")
    return results

if __name__ == "__main__":
    # Default paths
    data_file = "/Users/jaineet/Desktop/multi-agent-system/mini_dev_data/minidev/MINIDEV/mini_dev_sqlite.json"
    db_root = "/Users/jaineet/Desktop/multi-agent-system/mini_dev_data/minidev/MINIDEV/dev_databases"
    
    # Check if paths are valid
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        sys.exit(1)
    
    if not os.path.exists(db_root):
        print(f"Error: Database root directory not found at {db_root}")
        sys.exit(1)
    
    # Run the evaluation test
    test_evaluation(data_file, db_root) 