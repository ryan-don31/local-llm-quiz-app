from flask import Flask, request, render_template, jsonify

app = Flask(__name__, template_folder="templates")

@app.route("/")
def home():
    pass

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    pass

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    pass

if __name__ == "__main__":
    app.run(debug=True)