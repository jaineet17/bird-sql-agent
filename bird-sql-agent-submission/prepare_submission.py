import os
import shutil
import sys
import datetime

def prepare_submission():
    """Prepare the submission package for the BIRD-SQL Mini-Dev benchmark."""
    # Create a timestamp for the submission
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    submission_dir = f"bird_sql_submission_{timestamp}"
    
    # Create the submission directory
    os.makedirs(submission_dir, exist_ok=True)
    
    # Files to include in the submission
    files_to_include = [
        "README.md",
        "EVALUATION.md",
        "agent_system.py",
        "utils.py",
        "evaluate.py",
        "main.py",
        "requirements.txt",
        "test_utils.py",
        "evaluate_test.py",
        "demo_results.py"
    ]
    
    # Copy the files to the submission directory
    for file in files_to_include:
        if os.path.exists(file):
            shutil.copy(file, os.path.join(submission_dir, file))
            print(f"Copied {file} to submission directory")
        else:
            print(f"Warning: {file} not found")
    
    # If demo results exist, copy them too
    demo_files = [
        "demo_evaluation_results.json",
        "demo_accuracy_results.png",
        "error_analysis.png"
    ]
    
    for file in demo_files:
        if os.path.exists(file):
            shutil.copy(file, os.path.join(submission_dir, file))
            print(f"Copied {file} to submission directory")
    
    # Create a requirements.txt file if it doesn't exist
    if not os.path.exists("requirements.txt"):
        with open(os.path.join(submission_dir, "requirements.txt"), "w") as f:
            f.write("pyautogen>=0.8.0\n")
            f.write("autogen-ext[ollama]>=0.4.9\n")
            f.write("pandas>=2.0.0\n")
            f.write("matplotlib>=3.7.0\n")
            f.write("tqdm>=4.65.0\n")
        print("Created requirements.txt")
    
    # Create a ZIP file of the submission directory
    shutil.make_archive(submission_dir, 'zip', submission_dir)
    print(f"Created ZIP file: {submission_dir}.zip")
    
    # Clean up the temporary directory
    shutil.rmtree(submission_dir)
    print(f"Cleaned up temporary directory: {submission_dir}")
    
    print("\nSubmission package prepared successfully!")
    print(f"The submission package is available as: {submission_dir}.zip")

if __name__ == "__main__":
    prepare_submission() 