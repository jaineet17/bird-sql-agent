import json
import random
import matplotlib.pyplot as plt
from evaluate import analyze_errors

def generate_sample_results(sample_size=50, success_rate=0.64):
    """Generate sample evaluation results for demonstration"""
    # Sample question types
    question_types = [
        "What is the ratio of X?",
        "How many X have property Y?",
        "Find the maximum X for Y",
        "Calculate the average X for Y",
        "Count the number of X in Y",
        "List all X where Y > Z",
        "Find the top 5 X by Y",
        "Group X by Y and count",
        "Find the sum of X for each Y",
        "Find the difference between X and Y"
    ]
    
    # Sample databases
    databases = [
        "debit_card_specializing",
        "student_club",
        "formula_1",
        "thrombosis_prediction",
        "codebase_community",
        "toxicology",
        "european_football_2",
        "financial",
        "california_schools",
        "superhero",
        "card_games"
    ]
    
    # Sample error types
    error_types = [
        "Missing JOIN",
        "Missing WHERE",
        "Missing GROUP BY",
        "Date Format Error",
        "Conditional Logic Error",
        "Column Reference Error",
        "Syntax Error",
        "Aggregation Error"
    ]
    
    # Generate results
    results = {
        "correct": 0,
        "total": sample_size,
        "details": []
    }
    
    for i in range(sample_size):
        # Decide if this example is correct based on desired success rate
        is_correct = random.random() < success_rate
        
        if is_correct:
            results["correct"] += 1
        
        # Generate a sample detail
        db_id = random.choice(databases)
        question_template = random.choice(question_types)
        question = question_template.replace("X", f"{db_id} data").replace("Y", "value").replace("Z", "threshold")
        
        detail = {
            "question": question,
            "db_id": db_id,
            "gold_query": f"SELECT * FROM {db_id}_table WHERE condition = 'value'",
            "predicted_query": f"SELECT * FROM {db_id}_table WHERE condition = {'value' if is_correct else 'wrong_value'}",
            "is_correct": is_correct
        }
        
        # Add error information if not correct
        if not is_correct:
            detail["error_type"] = random.choice(error_types)
        
        results["details"].append(detail)
    
    # Calculate accuracy
    results["accuracy"] = (results["correct"] / results["total"]) * 100
    
    return results

def save_and_analyze_demo_results(results, filename="demo_evaluation_results.json"):
    """Save and analyze the demo results"""
    # Save to file
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"Demo Evaluation Results:")
    print(f"Total examples: {results['total']}")
    print(f"Correct predictions: {results['correct']}")
    print(f"Accuracy: {results['accuracy']:.2f}%")
    
    # Plot accuracy chart
    plt.figure(figsize=(10, 6))
    plt.bar(["Accuracy"], [results["accuracy"]])
    plt.title(f"Simulated Execution Accuracy on BIRD Mini-Dev ({results['total']} samples)")
    plt.ylabel("Accuracy (%)")
    plt.ylim(0, 100)
    plt.axhline(y=60, color='r', linestyle='-', label='Target (60%)')
    plt.legend()
    plt.savefig("demo_accuracy_results.png")
    
    # Analyze errors
    error_types, db_errors = analyze_errors(results)
    
    print("\nDemo completed. Files generated:")
    print(f"- {filename}")
    print("- demo_accuracy_results.png")
    print("- error_analysis.png")
    
    return results

if __name__ == "__main__":
    # Generate sample results with desired accuracy
    results = generate_sample_results(sample_size=50, success_rate=0.64)
    
    # Save and analyze results
    save_and_analyze_demo_results(results) 