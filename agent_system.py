import asyncio
import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen_ext.models.ollama import OllamaChatCompletionClient
import os
import json
from utils import load_schema, format_schema, execute_query, extract_sql

# Agent prompts
SELECTOR_PROMPT = """You are a database expert that specializes in analyzing database schemas for SQL queries.

TASK:
Given a user question and a database schema, identify ONLY the tables and columns that are directly relevant to answering the query.

INSTRUCTIONS:
1. Analyze the question carefully to understand what data is needed
2. Review the database schema and identify tables and columns needed to answer the question
3. Identify any necessary join conditions based on foreign key relationships
4. Make sure to include ALL tables and columns that might be needed for the query

OUTPUT FORMAT:
Return a simplified database schema that includes ONLY relevant tables and columns.
"""

DECOMPOSER_PROMPT = """You are an expert in SQL query generation and complex question decomposition.

TASK:
Given a user question and a database schema, generate an accurate SQL query that answers the question.

INSTRUCTIONS:
1. Break down complex questions into logical steps
2. For each step, think about how to express it in SQL
3. Pay close attention to:
   - Proper table and column names (case-sensitive)
   - Correct JOIN conditions
   - Appropriate WHERE clauses
   - Sorting, grouping, and aggregation requirements
   - Nested queries when necessary
4. Use SQLite syntax
5. Be careful with:
   - String literals should be in single quotes
   - Date formatting using proper SQLite functions
   - Proper handling of NULL values
   - Using the correct aggregation functions

OUTPUT:
Provide your reasoning step-by-step, then end with the final SQL query enclosed in ```sql and ``` tags.
"""

REFINER_PROMPT = """You are an expert SQL query validator and debugger.

TASK:
Given a user question, database schema, and a proposed SQL query, validate and fix any issues with the query.

INSTRUCTIONS:
1. Check the SQL query for:
   - Syntax errors
   - Incorrect table or column references
   - Logical errors
   - Missing JOIN conditions
   - Incorrect aggregation/grouping
   - Query structure issues

2. Pay special attention to:
   - Table and column name case sensitivity
   - Proper handling of NULL values
   - Appropriate use of aggregation functions
   - Correct JOIN types (INNER, LEFT, etc.)
   - Matching data types in comparisons
   - SQL functions used correctly (STRFTIME, SUBSTR, etc.)

3. Be detailed in your review, but make sure to fix every error you find

OUTPUT:
Provide the corrected SQL query enclosed in ```sql and ``` tags.
"""

async def async_check_ollama(model="llama3"):
    """Check if Ollama is available with the specified model asynchronously"""
    try:
        client = OllamaChatCompletionClient(model=model)
        # Simple test call
        response = await client.create(messages=[{"role": "user", "content": "Test"}])
        # Check if the response has the expected structure
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return True
        # If it's a dict, try to access the expected structure
        if isinstance(response, dict) and 'choices' in response:
            return True
        print(f"Unexpected response format: {type(response)}")
        print(f"Response: {response}")
        return True  # Assume it's working if we get any response
    except Exception as e:
        print(f"Error checking Ollama: {e}")
        return False

def check_ollama(model="llama3"):
    """Synchronous wrapper for the async check_ollama function"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_check_ollama(model))
    finally:
        loop.close()

def create_agents(model="llama3"):
    """Create the multi-agent system with Autogen"""
    # Basic LLM config
    llm_config = {
        "config_list": [{"model": model}],
        "temperature": 0.2
    }
    
    # Create the agents
    selector_agent = AssistantAgent(
        name="Selector",
        system_message=SELECTOR_PROMPT,
        llm_config=llm_config
    )
    
    decomposer_agent = AssistantAgent(
        name="Decomposer",
        system_message=DECOMPOSER_PROMPT,
        llm_config={
            "config_list": [{"model": model}],
            "temperature": 0.3
        }
    )
    
    refiner_agent = AssistantAgent(
        name="Refiner",
        system_message=REFINER_PROMPT,
        llm_config={
            "config_list": [{"model": model}],
            "temperature": 0.2
        }
    )
    
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )
    
    return selector_agent, decomposer_agent, refiner_agent, user_proxy

def process_text_to_sql(question, db_path, model="llama3", evidence=None):
    """Process a natural language question to SQL using multi-agent collaboration"""
    # Create the agents
    selector_agent, decomposer_agent, refiner_agent, user_proxy = create_agents(model)
    
    # Step 1: Load and format database schema
    schema = load_schema(db_path)
    formatted_schema = format_schema(schema)
    
    # Include evidence/background knowledge if available
    evidence_text = f"\nRELEVANT KNOWLEDGE: {evidence}" if evidence else ""
    
    # Step 2: Selector agent identifies relevant tables and columns
    print("[1/3] Running Selector Agent to identify relevant schema elements...")
    selector_input = f"Question: {question}{evidence_text}\n\nDatabase Schema:\n{formatted_schema}\n\nIdentify only the relevant tables and columns to answer this question."
    
    user_proxy.initiate_chat(
        selector_agent,
        message=selector_input
    )
    selector_output = selector_agent.last_message["content"]
    print("✓ Selector completed")
    
    # Step 3: Decomposer agent breaks down the question and generates SQL
    print("[2/3] Running Decomposer Agent to generate SQL...")
    decomposer_input = f"Question: {question}{evidence_text}\n\nRelevant Schema Information:\n{selector_output}\n\nGenerate a SQL query to answer this question."
    
    user_proxy.initiate_chat(
        decomposer_agent,
        message=decomposer_input
    )
    decomposer_output = decomposer_agent.last_message["content"]
    initial_sql = extract_sql(decomposer_output)
    print("✓ Decomposer completed")
    
    # Step 4: Refiner agent validates and fixes the SQL
    print("[3/3] Running Refiner Agent to validate and fix the SQL...")
    refiner_input = f"Question: {question}{evidence_text}\n\nDatabase Schema:\n{formatted_schema}\n\nProposed SQL Query:\n{initial_sql}\n\nValidate and fix any issues with this SQL query."
    
    user_proxy.initiate_chat(
        refiner_agent,
        message=refiner_input
    )
    refiner_output = refiner_agent.last_message["content"]
    final_sql = extract_sql(refiner_output)
    print("✓ Refiner completed")
    
    # Step 5: Execute and validate
    try:
        result = execute_query(db_path, final_sql)
        if "error" in result:
            # If there's an error, try to fix it
            print("[Extra] SQL execution error, attempting fix...")
            fix_input = f"Error executing SQL: {result['error']}\n\nQuestion: {question}{evidence_text}\n\nDatabase Schema:\n{formatted_schema}\n\nFailed SQL Query:\n{final_sql}\n\nPlease fix the query."
            
            user_proxy.initiate_chat(
                refiner_agent,
                message=fix_input
            )
            fix_output = refiner_agent.last_message["content"]
            final_sql = extract_sql(fix_output)
            print("✓ Fix completed")
            
            # Verify the fix worked
            final_result = execute_query(db_path, final_sql)
            if "error" in final_result:
                print(f"Fix failed: {final_result['error']}")
    except Exception as e:
        print(f"Error executing query: {e}")
    
    return final_sql 