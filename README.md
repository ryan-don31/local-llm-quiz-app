Directory structure:
``` Shell
llm-pdf-quiz-generator/
│
├── app/
│   ├── main.py     # Flask app
│   ├── rag.py      # Extracts text from pdf, chunks logic, generates the embeddings with ollama, stores vectors, retrieves top-k passages
│   ├── llm.py      # All interaction with the LLM
│   ├── safety.py   # 
│   ├── telemetry.py
│   └── ui/
│       └── templates/
│           └── index.html
│
├── data/
│   └── seed_pdfs/
│       └── example.pdf
│
├── tests/
│   ├── tests.json
│   └── run_tests.py
│
├── logs/
│   └── requests.jsonl
│
├── README.md
├── requirements.txt
├── .env.example
└── run.sh

```