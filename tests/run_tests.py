import json
import os
import sys

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from app.safety import check_input_safety
    from app.llm import generate_quiz
except ImportError as e:
    print(f"CRITICAL: Could not import app modules. Make sure you are running this from the root directory or tests directory. {e}")
    sys.exit(1)

TEST_FILE = os.path.join(os.path.dirname(__file__), "tests.json")

def run_safety_test(test_case):
    """
    Checks if the safety guardrail correctly identifies safe vs unsafe inputs.
    """
    input_text = test_case["input"]
    expected = test_case["expected_result"] # "pass" or "fail"
    
    is_safe, reason = check_input_safety(input_text)
    
    # If expected "pass", is_safe should be True
    # If expected "fail", is_safe should be False
    if expected == "pass" and is_safe:
        return True, "OK"
    elif expected == "fail" and not is_safe:
        return True, f"OK (Caught: {reason})"
    else:
        return False, f"Expected {expected}, got safe={is_safe} ({reason})"

def run_generation_test(test_case):
    """
    Checks if the LLM generates valid JSON with the required keys.
    """
    topic = test_case["input"]
    context_text = test_case.get("context", "Placeholder context.")
    expected_keys = test_case.get("expected_keys", [])
    
    # Mock context structure expected by generate_quiz
    mock_context = [{"text": context_text}]
    
    try:
        # Call the actual LLM function
        # Note: This requires Ollama to be running!
        quiz = generate_quiz(mock_context, topic)
        
        if not isinstance(quiz, list):
            return False, "Output is not a list"
        
        if len(quiz) == 0:
            return False, "Output list is empty"
            
        first_q = quiz[0]
        missing = [k for k in expected_keys if k not in first_q]
        
        if missing:
            return False, f"Missing keys: {missing}"
            
        return True, "Valid JSON Schema"
        
    except Exception as e:
        return False, f"Exception during generation: {str(e)}"

def main():
    print("Loading tests from:", TEST_FILE)
    with open(TEST_FILE, 'r') as f:
        tests = json.load(f)
        
    passed = 0
    total = len(tests)
    
    print(f"Running {total} tests...\n")