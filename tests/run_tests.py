import json
import os
import sys
from app.safety import check_input_safety
from app.llm import generate_quiz

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
    try:
        with open(TEST_FILE, 'r') as f:
            tests = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {TEST_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {TEST_FILE} is not valid JSON")
        sys.exit(1)
        
    passed = 0
    total = len(tests)
    
    print(f"Running {total} tests...\n")
    
    for i, test in enumerate(tests):
        test_type = test.get("type", "unknown")
        test_name = test.get("name", f"Test #{i+1}")
        
        print(f"[{i+1}/{total}] Running '{test_name}' ({test_type})...", end=" ", flush=True)
        
        success = False
        message = ""

        # Dispatch to the correct test function based on type
        if test_type == "safety":
            success, message = run_safety_test(test)
        elif test_type == "generation":
            success, message = run_generation_test(test)
        else:
            success = False
            message = f"Unknown test type: '{test_type}'"

        # Report result
        if success:
            print(f"PASS: {message}")
            passed += 1
        else:
            print(f"FAIL: {message}")

    # Final Summary
    print(f"Test Run Complete.")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {int((passed/total)*100) if total > 0 else 0}%")

if __name__ == "__main__":
    main()