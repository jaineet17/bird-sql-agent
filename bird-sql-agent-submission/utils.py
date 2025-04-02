import sqlite3
import re
import os
import json

def load_schema(db_path):
    """Extract schema information from a SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema = {}
    for table in tables:
        table_name = table[0]
        # Get columns for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        sample_data = cursor.fetchall()
        
        schema[table_name] = {
            "columns": [col[1] for col in columns],
            "types": [col[2] for col in columns],
            "sample_data": sample_data
        }
    
    # Get foreign key relationships
    foreign_keys = []
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        fks = cursor.fetchall()
        for fk in fks:
            if len(fk) >= 5:  # Make sure we have enough elements
                foreign_keys.append({
                    "table": table_name,
                    "column": fk[3] if len(fk) > 3 else "",
                    "ref_table": fk[2] if len(fk) > 2 else "",
                    "ref_column": fk[4] if len(fk) > 4 else ""
                })
    
    schema["foreign_keys"] = foreign_keys
    conn.close()
    
    return schema

def format_schema(schema):
    """Format schema for LLM prompt"""
    formatted = "DATABASE SCHEMA:\n"
    
    # Add tables and columns
    for table_name, table_info in schema.items():
        if table_name == "foreign_keys":
            continue
            
        formatted += f"Table: {table_name}\n"
        formatted += "Columns:\n"
        
        for i, col in enumerate(table_info["columns"]):
            col_type = table_info["types"][i] if i < len(table_info["types"]) else "unknown"
            formatted += f"  - {col} ({col_type})\n"
        
        # Add sample data
        if table_info["sample_data"]:
            formatted += "Sample data:\n"
            for row in table_info["sample_data"][:2]:  # Show just 2 sample rows
                sample_str = []
                for i, val in enumerate(row):
                    if i < len(table_info["columns"]):
                        sample_str.append(f"{table_info['columns'][i]}={val}")
                formatted += f"  {', '.join(sample_str)}\n"
        
        formatted += "\n"
    
    # Add foreign keys
    if "foreign_keys" in schema and schema["foreign_keys"]:
        formatted += "Foreign Keys:\n"
        for fk in schema["foreign_keys"]:
            formatted += f"  {fk['table']}.{fk['column']} → {fk['ref_table']}.{fk['ref_column']}\n"
    
    return formatted

def execute_query(db_path, query):
    """Execute SQL query and return results"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description] if cursor.description else []
        
        conn.close()
        return {"results": results, "column_names": column_names}
    except Exception as e:
        return {"error": str(e)}

def extract_sql(text):
    """Extract SQL query from text"""
    # Try to extract SQL between SQL code markers
    sql_pattern = r"```sql\s*(.*?)\s*```"
    match = re.search(sql_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # If no code block, try to find SQL by keywords
    lines = text.split('\n')
    sql_lines = []
    in_sql = False
    
    for line in lines:
        line = line.strip()
        if line.upper().startswith("SELECT") or in_sql:
            in_sql = True
            sql_lines.append(line)
            if line.endswith(";"):
                break
    
    if sql_lines:
        return " ".join(sql_lines)
    
    # Last resort: return the whole text
    return text 