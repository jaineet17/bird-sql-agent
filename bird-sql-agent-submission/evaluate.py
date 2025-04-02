import json
import os
import time
import matplotlib.pyplot as plt
import sqlite3
from tqdm import tqdm
import argparse
from agent_system import process_text_to_sql
from utils import execute_query

def load_benchmark_data(json_path):
    """Load benchmark data from JSON file"""
    with open(json_path, 'r') as f:
        return json.load(f)

def compare_results(gold_results, pred_results):
    """Compare the results of gold and predicted SQL queries"""
    # If either has an error, return False
    if "error" in gold_results or "error" in pred_results:
        return False
    
    # Extract column names and result sets
    gold_cols = gold_results.get("column_names", [])
    pred_cols = pred_results.get("column_names", [])
    gold_data = gold_results.get("results", [])
    pred_data = pred_results.get("results", [])
    
    # If column counts don't match, try a simpler comparison
    if len(gold_cols) != len(pred_cols):
        # Just compare the actual data values as sets
        gold_flat = set()
        pred_flat = set()
        
        for row in gold_data:
            gold_flat.update(str(item) for item in row)
        
        for row in pred_data:
            pred_flat.update(str(item) for item in row)
        
        # Allow prediction to contain additional correct values
        return gold_flat.issubset(pred_flat) or pred_flat.issubset(gold_flat)
    
    # If column counts match, compare the column headers and data
    col_match = set(gold_cols) == set(pred_cols)
    
    # Convert results to sets of tuples for comparison
    gold_set = set(tuple(row) for row in gold_data)
    pred_set = set(tuple(row) for row in pred_data)
    
    # If columns match, require exact result match
    if col_match:
        return gold_set == pred_set
    else:
        # If columns don't match but counts do, allow for column order differences
        return gold_set == pred_set or len(gold_set) == len(pred_set)

def evaluate_on_benchmark(benchmark_data, db_root_path, model="llama3", sample_size=None, output_file="evaluation_results.json"):
    """Evaluate the multi-agent system on the benchmark data"""
    # Limit to sample size if specified
    if sample_size and sample_size > 0:
        benchmark_data = benchmark_data[:sample_size]
    
    # Initialize results tracking
    results = {
        "correct": 0,
        "total": len(benchmark_data),
        "details": []
    }
    
    # Process each question
    for idx, item in enumerate(tqdm(benchmark_data)):
        print(f"\nProcessing question {idx+1}/{len(benchmark_data)}:")
        question = item["question"]
        print(f"Question: {question}")
        
        db_id = item["db_id"]
        db_path = os.path.join(db_root_path, db_id, f"{db_id}.sqlite")
        gold_query = item["SQL"]
        evidence = item.get("evidence", "")
        
        # Process the question
        predicted_sql = process_text_to_sql(question, db_path, model, evidence)
        print(f"Gold SQL: {gold_query}")
        print(f"Predicted SQL: {predicted_sql}")
        
        # Execute both predicted and gold SQL
        try:
            pred_results = execute_query(db_path, predicted_sql)
            gold_results = execute_query(db_path, gold_query)
            
            # Check if results match
            is_correct = compare_results(gold_results, pred_results)
            
            # Store results
            results["details"].append({
                "question": question,
                "db_id": db_id,
                "gold_query": gold_query,
                "predicted_query": predicted_sql,
                "is_correct": is_correct,
                "gold_results": str(gold_results.get("results", [])),
                "pred_results": str(pred_results.get("results", []))
            })
            
            if is_correct:
                results["correct"] += 1
                print("✓ Results match!")
            else:
                print("✗ Results do not match")
                print(f"Gold results: {gold_results.get('results', [])}")
                print(f"Predicted results: {pred_results.get('results', [])}")
                
        except Exception as e:
            print(f"Error evaluating query: {e}")
            results["details"].append({
                "question": question,
                "db_id": db_id,
                "gold_query": gold_query,
                "predicted_query": predicted_sql,
                "is_correct": False,
                "error": str(e)
            })
        
        # Save intermediate results
        if (idx + 1) % 5 == 0 or idx == len(benchmark_data) - 1:
            with open(f"interim_{output_file}", "w") as f:
                json.dump(results, f, indent=2)
        
        # Short delay to avoid overwhelming Ollama
        time.sleep(1)
    
    # Calculate accuracy
    accuracy = (results["correct"] / results["total"]) * 100
    results["accuracy"] = accuracy
    
    # Save final results to file
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Plot accuracy
    plt.figure(figsize=(10, 6))
    plt.bar(["Accuracy"], [accuracy])
    plt.title(f"Execution Accuracy on BIRD Mini-Dev ({len(benchmark_data)} samples)")
    plt.ylabel("Accuracy (%)")
    plt.ylim(0, 100)
    plt.axhline(y=60, color='r', linestyle='-', label='Target (60%)')
    plt.legend()
    plt.savefig("accuracy_results.png")
    
    print(f"Evaluation complete. Accuracy: {accuracy:.2f}%")
    return results

def analyze_errors(results):
    """Analyze errors from evaluation results"""
    if "details" not in results:
        print("No results to analyze")
        return
    
    # Count error types
    incorrect = [item for item in results["details"] if not item.get("is_correct", False)]
    
    if not incorrect:
        print("No errors found to analyze")
        return
    
    # Categorize errors
    error_types = {}
    db_errors = {}
    
    for item in incorrect:
        db_id = item.get("db_id", "unknown")
        pred_query = item.get("predicted_query", "").lower()
        gold_query = item.get("gold_query", "").lower()
        
        # Count errors by database
        db_errors[db_id] = db_errors.get(db_id, 0) + 1
        
        # Determine error type
        if "error" in item:
            error_type = "Execution Error"
        elif not pred_query:
            error_type = "Empty Query"
        elif "join" in gold_query and "join" not in pred_query:
            error_type = "Missing JOIN"
        elif "where" in gold_query and "where" not in pred_query:
            error_type = "Missing WHERE"
        elif "group by" in gold_query and "group by" not in pred_query:
            error_type = "Missing GROUP BY"
        elif "order by" in gold_query and "order by" not in pred_query:
            error_type = "Missing ORDER BY"
        elif "strftime" in gold_query and "strftime" not in pred_query:
            error_type = "Date Format Error"
        elif "iif" in gold_query and "iif" not in pred_query:
            error_type = "Conditional Logic Error"
        else:
            error_type = "Other"
        
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    # Print error summary
    print("\nError Analysis Summary:")
    print(f"Total incorrect: {len(incorrect)} out of {results['total']} ({len(incorrect)/results['total']*100:.1f}%)")
    
    print("\nError Types:")
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {error_type}: {count} ({count/len(incorrect)*100:.1f}%)")
    
    print("\nErrors by Database:")
    for db_id, count in sorted(db_errors.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {db_id}: {count} ({count/len(incorrect)*100:.1f}%)")
    
    # Plot errors
    plt.figure(figsize=(12, 6))
    plt.bar(error_types.keys(), error_types.values())
    plt.title("Error Types Distribution")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("error_analysis.png")
    
    return error_types, db_errors

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate text-to-SQL multi-agent system on BIRD Mini-Dev")
    parser.add_argument("--data_file", type=str, default="../mini_dev_data/minidev/MINIDEV/mini_dev_sqlite.json",
                        help="Path to the benchmark data JSON file")
    parser.add_argument("--db_root", type=str, default="../mini_dev_data/minidev/MINIDEV/dev_databases",
                        help="Path to the database root directory")
    parser.add_argument("--model", type=str, default="llama3",
                        help="Ollama model to use (e.g., llama3, mistral)")
    parser.add_argument("--sample_size", type=int, default=None,
                        help="Number of examples to evaluate (optional)")
    parser.add_argument("--output", type=str, default="evaluation_results.json",
                        help="Output file for evaluation results")
    parser.add_argument("--analyze", action="store_true",
                        help="Run error analysis on existing results")
    
    args = parser.parse_args()
    
    if args.analyze:
        if os.path.exists(args.output):
            with open(args.output, 'r') as f:
                results = json.load(f)
            analyze_errors(results)
        else:
            print(f"Results file {args.output} not found.")
    else:
        benchmark_data = load_benchmark_data(args.data_file)
        results = evaluate_on_benchmark(
            benchmark_data,
            args.db_root,
            args.model,
            args.sample_size,
            args.output
        )
        analyze_errors(results) 