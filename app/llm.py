import json
import ollama
from typing import List, Dict

def _clean_json_response(response: str) -> str:
    """
    Helper to strip markdown code blocks if the LLM adds them.
    Example: ```json [...] ``` -> [...]
    """
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def generate_quiz(context_chunks: List[Dict], topic: str, model: str = "llama3.2:3b") -> List[Dict]:
    """
    Generates a quiz based on the retrieved RAG context.
    Returns a list of dicts: [{question, options, answer}]
    """
    
    # 1. Construct the Context String
    # We join the top retrieved chunks into a single block of text
    context_text = "\n\n---\n\n".join([c["text"] for c in context_chunks])
    
    # 2. Define the System Prompt
    # We explicitly tell the model strictly JSON format is required.
    system_prompt = (
        "You are a strict educational assistant. Your task is to generate a quiz based ONLY on the provided text context. "
        "You must output a valid JSON array of objects. "
        "Do not include any conversational text, preamble, or markdown formatting outside the JSON."
        "\n\nJSON Schema per question:"
        "\n{"
        "\n  \"question\": \"str\","
        "\n  \"options\": [\"str\", \"str\", \"str\", \"str\"],"
        "\n  \"answer\": \"str\" (must be one of the options)"
        "\n}"
    )

    # 3. Define the User Prompt
    user_prompt = (
        f"Context:\n{context_text}\n\n"
        f"Task: Generate 3 multiple-choice questions about '{topic}' based on the context above."
    )

    try:
        # 4. Call Ollama
        response = ollama.chat(model=model, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ])
        
        content = response['message']['content']
        
        # 5. Parse JSON
        cleaned_json_str = _clean_json_response(content)
        quiz_data = json.loads(cleaned_json_str)
        
        # Verify structure roughly
        if isinstance(quiz_data, list):
            return quiz_data
        else:
            # If model returned a single object instead of list
            return [quiz_data]

    except json.JSONDecodeError:
        # Fallback if model fails to generate valid JSON
        print(f"LLM JSON Error. Raw output: {content}") # useful for debugging logs
        return [{
            "question": f"The AI could not generate a valid quiz for '{topic}'.",
            "options": ["Try Again", "Check PDF", "Simplify Topic", "Check Logs"],
            "answer": "Check Logs"
        }]
    except Exception as e:
        return [{
            "question": f"System Error: {str(e)}",
            "options": ["Error", "Error", "Error", "Error"],
            "answer": "Error"
        }]