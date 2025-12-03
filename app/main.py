import time
import os
import tempfile
from flask import Flask, request, render_template, jsonify
from app.rag import extract_text_from_file, ingest_pdf_text, search, clear_index
from app.telemetry import log_request
from app.safety import check_input_safety
from app.llm import generate_quiz


app = Flask(__name__, template_folder="ui")


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded (use key 'pdf')"}), 400
    
    pdf_file = request.files["pdf"]
    if pdf_file.filename == "" or pdf_file.filename is None:
        return jsonify({"error": "Empty or nonexistent filename"}), 400
    
    tmp = None
    start = time.perf_counter()
    try:
        # Save temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_file.save(tmp.name)
        tmp.close()

        # Extract Text
        extracted = extract_text_from_file(tmp.name)
        full_text = extracted.get("text", "")

        # Ingest into Vector DB (RAG)
        # We clear the index first to ensure the quiz is only about THIS PDF.
        # In a multi-user app, you'd handle user IDs, but for this assignment, 
        # resetting per upload is safer/cleaner.
        clear_index() 
        ingest_pdf_text(full_text)

        latency = time.perf_counter() - start

        # Telemetry
        log_request({
            "endpoint": "/upload_pdf",
            "timestamp": time.time(),
            "latency_s": latency,
            "pathway": "ingest",
            "file_size": os.path.getsize(tmp.name)
        })

        return jsonify({
            "status": "success", 
            "message": "PDF processed and indexed.", 
            "pages": extracted["meta"]["pages"]
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500
    finally:
        if tmp:
            os.unlink(tmp.name)

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz_route():
    # Parse JSON
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    topic = data.get("topic", "General Knowledge")
    top_k = int(data.get("top_k", 4))

    # Safety Check
    ok, reason = check_input_safety(topic)
    if not ok:
        return jsonify({"error": "Input failed safety check", "reason": reason}), 400

    start = time.perf_counter()
    pathway = "RAG"

    try:
        # Retrieve Context (RAG)
        retrieved_chunks = search(topic, top_k=top_k)
        
        # Fallback: if retrieval fails or finds nothing, user might be asking general questions
        # OR the PDF wasn't uploaded.
        if not retrieved_chunks:
            pathway = "LLM-only (No Context Found)"
            # We send empty context, LLM might hallucinate or refuse
            retrieved_chunks = []

        # Generate Quiz
        quiz_json = generate_quiz(retrieved_chunks, topic=topic)

        latency = time.perf_counter() - start

        # Telemetry
        log_request({
            "endpoint": "/generate_quiz",
            "timestamp": time.time(),
            "latency_s": latency,
            "pathway": pathway,
            "top_k": top_k,
            "topic": topic
        })

        return jsonify({
            "quiz": quiz_json, 
            "meta": {"pathway": pathway, "latency_s": latency}
        })

    except Exception as e:
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)