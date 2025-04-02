import os
import sys
from utils import load_schema, format_schema, execute_query

def test_sql_execution():
    """Test SQL execution with a simple query"""
    # Get the absolute path to the database
    db_root = "/Users/jaineet/Desktop/multi-agent-system/mini_dev_data/minidev/MINIDEV/dev_databases"
    db_id = "debit_card_specializing"
    db_path = os.path.join(db_root, db_id, f"{db_id}.sqlite")
    
    # Check if the database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    # Try to load the schema
    try:
        schema = load_schema(db_path)
        print(f"Successfully loaded schema with {len(schema) - 1} tables")  # -1 for foreign_keys
        
        # Print table names
        print("Tables:")
        for table_name in schema:
            if table_name != "foreign_keys":
                print(f"  - {table_name}")
        
        # Example query to test
        query = "SELECT COUNT(*) FROM customers WHERE Currency = 'EUR'"
        print(f"\nExecuting query: {query}")
        
        # Execute the query
        result = execute_query(db_path, query)
        if "error" in result:
            print(f"Error: {result['error']}")
            return False
        
        print(f"Result: {result}")
        
        # Get the ratio of EUR to CZK customers
        ratio_query = "SELECT CAST(SUM(CASE WHEN Currency = 'EUR' THEN 1 ELSE 0 END) AS FLOAT) / SUM(CASE WHEN Currency = 'CZK' THEN 1 ELSE 0 END) AS ratio FROM customers"
        print(f"\nExecuting ratio query: {ratio_query}")
        
        ratio_result = execute_query(db_path, ratio_query)
        if "error" in ratio_result:
            print(f"Error: {ratio_result['error']}")
            return False
        
        print(f"Ratio result: {ratio_result}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if test_sql_execution():
        print("\nTest successful!")
        sys.exit(0)
    else:
        print("\nTest failed!")
        sys.exit(1) 