import argparse
import os
import json
from agent_system import process_text_to_sql, check_ollama
from utils import execute_query
from evaluate import evaluate_on_benchmark, load_benchmark_data, analyze_errors

def run_single_query(question, db_path, model="llama3", evidence=None, test_mode=False):
    """Run a single query through the multi-agent system"""
    print(f"Processing question: {question}")
    print(f"Database: {db_path}")
    
    if evidence:
        print(f"Evidence: {evidence}")
    
    if test_mode:
        # In test mode, use a predefined SQL query for demonstration
        print("[Test Mode] Bypassing LLM for demonstration purposes")
        
        # Extract the table name from the question or use a default
        if "customers" in question.lower():
            table = "customers"
        elif "transactions" in question.lower():
            table = "transactions_1k"
        else:
            # Detect the database from db_path
            db_name = os.path.basename(os.path.dirname(db_path))
            if db_name == "debit_card_specializing":
                table = "customers"
            else:
                # Fallback to a table that most databases have
                table = "customers"
        
        # Generate a simple query based on the question
        if "ratio" in question.lower() and "eur" in question.lower() and "czk" in question.lower():
            sql = "SELECT CAST(SUM(CASE WHEN Currency = 'EUR' THEN 1 ELSE 0 END) AS FLOAT) / SUM(CASE WHEN Currency = 'CZK' THEN 1 ELSE 0 END) AS ratio FROM customers"
        elif "count" in question.lower():
            sql = f"SELECT COUNT(*) FROM {table}"
        else:
            sql = f"SELECT * FROM {table} LIMIT 5"
    else:
        # Use the actual multi-agent system to generate SQL
        sql = process_text_to_sql(question, db_path, model, evidence)
    
    print(f"\nGenerated SQL:\n{sql}")
    
    # Execute the query
    try:
        result = execute_query(db_path, sql)
        if "error" in result:
            print(f"\nError executing query: {result['error']}")
        else:
            print("\nExecution results:")
            
            columns = result.get("column_names", [])
            if columns:
                print(f"Columns: {', '.join(columns)}")
            
            data = result.get("results", [])
            if data:
                for row in data[:10]:  # Show at most 10 rows
                    print(row)
                
                if len(data) > 10:
                    print(f"... and {len(data) - 10} more rows")
            else:
                print("No results returned.")
    except Exception as e:
        print(f"\nError executing query: {e}")

def optimize_prompts(results_file, output_file="enhanced_prompts.py"):
    """Optimize prompts based on error analysis"""
    if not os.path.exists(results_file):
        print(f"Results file '{results_file}' not found")
        return
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Analyze errors
    error_types, db_errors = analyze_errors(results)
    
    # Collect successful examples for few-shot learning
    correct = [item for item in results["details"] if item.get("is_correct", False)]
    
    # Select diverse examples (different databases if possible)
    selected = []
    db_ids = set()
    num_examples = min(3, len(correct))
    
    for item in correct:
        if len(selected) >= num_examples:
            break
        
        if item["db_id"] not in db_ids:
            selected.append(item)
            db_ids.add(item["db_id"])
    
    # If needed, add more examples
    if len(selected) < num_examples:
        for item in correct:
            if len(selected) >= num_examples:
                break
            if item not in selected:
                selected.append(item)
    
    # Format examples
    examples = "EXAMPLES:\n\n"
    for i, item in enumerate(selected):
        examples += f"Example {i+1}:\nQuestion: {item['question']}\nSQL: {item['predicted_query']}\n\n"
    
    # Import original prompts
    from agent_system import SELECTOR_PROMPT, DECOMPOSER_PROMPT, REFINER_PROMPT
    
    # Enhance prompts based on error patterns
    enhanced_decomposer = DECOMPOSER_PROMPT
    enhanced_refiner = REFINER_PROMPT
    
    # Add specific guidance based on common error types
    if error_types:
        common_errors = [error for error, _ in sorted(error_types.items(), key=lambda x: x[1], reverse=True)][:3]
        
        error_guidance = "\n\nCOMMON ERRORS TO AVOID:\n"
        if "Missing JOIN" in common_errors:
            error_guidance += "1. Ensure proper JOIN conditions between tables when query involves multiple tables\n"
        if "Date Format Error" in common_errors:
            error_guidance += "2. Use SQLite date functions correctly (STRFTIME, SUBSTR, etc.)\n"
        if "Conditional Logic Error" in common_errors:
            error_guidance += "3. Use IIF or CASE WHEN for conditional logic\n"
        if "Missing GROUP BY" in common_errors:
            error_guidance += "4. Include GROUP BY when using aggregation functions\n"
        
        enhanced_decomposer += error_guidance
        enhanced_refiner += error_guidance
    
    # Add examples to prompts
    if selected:
        enhanced_decomposer += "\n\n" + examples
        enhanced_refiner += "\n\n" + examples
    
    # Save enhanced prompts
    with open(output_file, "w") as f:
        f.write(f"SELECTOR_PROMPT = '''{SELECTOR_PROMPT}'''\n\n")
        f.write(f"DECOMPOSER_PROMPT = '''{enhanced_decomposer}'''\n\n")
        f.write(f"REFINER_PROMPT = '''{enhanced_refiner}'''\n")
    
    print(f"Enhanced prompts saved to {output_file}")
    return enhanced_decomposer, enhanced_refiner

def main():
    parser = argparse.ArgumentParser(description="BIRD-SQL Multi-Agent System with Autogen")
    parser.add_argument("--mode", type=str, choices=["evaluate", "single", "optimize"],
                       default="single", help="Operation mode")
    parser.add_argument("--data_file", type=str, 
                       default="/Users/jaineet/Desktop/multi-agent-system/mini_dev_data/minidev/MINIDEV/mini_dev_sqlite.json",
                       help="Path to the benchmark data JSON file")
    parser.add_argument("--db_root", type=str, 
                       default="/Users/jaineet/Desktop/multi-agent-system/mini_dev_data/minidev/MINIDEV/dev_databases",
                       help="Path to the database root directory")
    parser.add_argument("--question", type=str, 
                       help="Question to answer (for single mode)")
    parser.add_argument("--db_id", type=str, 
                       help="Database ID (for single mode)")
    parser.add_argument("--evidence", type=str, 
                       help="Optional evidence/knowledge for the query (for single mode)")
    parser.add_argument("--model", type=str, default="llama3",
                       help="Ollama model to use (llama3, mistral, etc.)")
    parser.add_argument("--sample_size", type=int, default=5,
                       help="Number of examples to evaluate (for evaluate mode)")
    parser.add_argument("--results_file", type=str, default="evaluation_results.json",
                       help="Results file for evaluation or optimization")
    parser.add_argument("--skip_model_check", action="store_true",
                       help="Skip checking if Ollama model is available")
    parser.add_argument("--test_mode", action="store_true",
                       help="Run in test mode (bypasses LLM calls)")
    
    args = parser.parse_args()
    
    # Check if Ollama is available with the specified model
    if not args.skip_model_check and not args.test_mode and not check_ollama(args.model):
        print(f"Ollama is not available with model '{args.model}'")
        print(f"Please ensure Ollama is running and pull the model: ollama pull {args.model}")
        return
    
    # Run the appropriate mode
    if args.mode == "evaluate":
        print(f"Evaluating multi-agent system on BIRD Mini-Dev benchmark...")
        benchmark_data = load_benchmark_data(args.data_file)
        results = evaluate_on_benchmark(
            benchmark_data,
            args.db_root,
            args.model,
            args.sample_size,
            args.results_file
        )
        
    elif args.mode == "single":
        if not args.question:
            print("Error: 'question' argument is required for single mode")
            return
        
        if args.db_id:
            db_path = os.path.join(args.db_root, args.db_id, f"{args.db_id}.sqlite")
            if not os.path.exists(db_path):
                print(f"Error: Database {args.db_id} not found at {db_path}")
                return
        else:
            print("Error: 'db_id' argument is required for single mode")
            return
        
        run_single_query(args.question, db_path, args.model, args.evidence, args.test_mode)
    
    elif args.mode == "optimize":
        print(f"Optimizing prompts based on evaluation results...")
        optimize_prompts(args.results_file)

if __name__ == "__main__":
    main() 