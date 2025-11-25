import time
import tempfile
from flask import Flask, request, render_template, jsonify

app = Flask(__name__, template_folder="ui")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded (use key 'pdf')"}), 400
    
    pdf_file = request.files["pdf"]
    if pdf_file.filename == "" or pdf_file.filname is None:
        return jsonify({"error": "Empty or nonexistent filename"}), 400
    
    tmp = None
    start = time.perf_counter()
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_file.save(tmp.name)
        tmp.close()

        # Import here so rag.py can be implemented later
        from app.rag import extract_text_from_file  # noqa: E402

        extracted = extract_text_from_file(tmp.name)
        latency = time.perf_counter() - start

        # Optionally log telemetry if telemetry module exists
        try:
            from app.telemetry import log_request  # noqa: E402
            log_request({
                "endpoint": "/upload_pdf",
                "timestamp": time.time(),
                "latency_s": latency,
                "pathway": "upload",
            })
        except Exception:
            pass

        return jsonify({"text": extracted.get("text", ""), "meta": extracted.get("meta", {})})
    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {e}"}), 500
    finally:
        # Do not delete tmp here if you want to reuse file in local debugging.
        # If you want to always remove: uncomment the next two lines.
        # import os; os.unlink(tmp.name)
        pass


@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    text = data.get("text")
    title = data.get("title", "")
    top_k = int(data.get("top_k", 4))

    if not text:
        return jsonify({"error", "Missing 'text' in request body"}), 400
    
    try:
        from app.safety import check_input_safety
        ok, reason = check_input_safety(text)
        if not ok:
            return jsonify({"error": "Input failed safety check", "reason": reason}), 400
    except Exception:
        pass

    start = time.perf_counter()
    try:
        retrieved = []
        try:
            from app.rag import search
            retrieved = search(text, top_k=top_k)
            pathway = "RAG"
        except Exception:
            retrieved = [{"text": text}]
            pathway = "none"

        from app.llm import generate_quiz
        quiz = generate_quiz(retrieved, title=title)

        latency = time.perf_counter() - start

        try:
            from app.telemetry import log_request
            log_request({
                "endpoint": "/generate_quiz",
                "timestamp": time.time(),
                "latency_s": latency,
                "pathway": pathway,
                "top_k": top_k
            })
        except Exception:
            pass

        return jsonify({"quiz": quiz, "meta": {"pathway": pathway, "latency_s": latency}})
    except Exception as e:
        return jsonify({"error": f"Failed to generate quiz: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)