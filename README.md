# MoneySprout 🌱 — Gamified AI Financial Literacy Companion for Kids

![MoneySprout Live Demo](./demo.gif)

**MoneySprout** is an autonomous AI financial literacy companion designed to help children build healthy financial habits, learn money management concepts, track savings goals, and complete household chores through gamified interactions, AI video lessons, and digital award certificates.

Powered by **Google Cloud Agent Development Kit (ADK)** and deployed on **Google Agent Runtime**, MoneySprout pairs an interactive mascot buddy named **Sprout** with a modern dashboard UI featuring real-time financial tracking tiles, AI video generation, and dynamic A2UI surface rendering.

---

## 🚀 Key Capabilities & Implemented Features

- **🌱 Interactive AI Mascot ("Sprout")**: A warm, encouraging financial buddy tailored for kids, answering savings questions and guiding children toward long-term goals.
- **🎬 AI Video Financial Concept Lessons**: Generates 5-second animated financial literacy videos on-demand (e.g., teaching *Delayed Gratification*) using Google's **Omni model** (`gemini-omni-flash-preview`). Videos automatically sync to both the chat bubble and the dashboard's **Concept Video Tile**.
- **🏆 Gemini AI Savings Award Certificates**: Generates 3D golden celebratory milestone certificates using Google's **Gemini Image model** (`gemini-3.1-flash-lite-image`) directly saved to Cloud Storage and rendered as award cards inside the UI.
- **🎯 Real-Time Goal Tracking**: Connects to Google Cloud Firestore to manage items kids are saving for (e.g., Outdoor Bicycle, Science Kit) and tracks current progress ($85 / $120).
- **🧹 Household Chore & Allowance Ledger**: Manages chore assignments, allowance payouts, and automatically routes earned chore money into active savings goals.
- **🧠 Cross-Session Memory Bank**: Powered by Vertex AI Memory Bank to retain child preferences, savings history, and personal achievements across multiple user sessions.
- **🛡️ RAG Financial Safety Guardrails**: Grounded on Vertex AI RAG Engine to answer financial advice questions safely following age-appropriate guidelines.
- **📊 Dynamic A2UI Dashboard & Rich Cards**: Renders structured UI components (progress bars, chore check-lists, ledger tables) natively inside `adk web` and the custom web frontend.

---

## 🧰 Wired Google Cloud Services & Tools

| Service / Tool | Model / Engine | Purpose in MoneySprout |
| :--- | :--- | :--- |
| **Agent Framework** | `google-adk` (ADK 1.1.0) | Core agent lifecycle, tool binding, and workflow orchestration |
| **Agent Hosting** | Vertex AI Agent Runtime | Serverless execution of the reasoning engine over the A2A protocol |
| **Core Reasoning Agent** | `gemini-2.5-flash` | Natural language understanding, child dialogue, and tool invocation |
| **AI Video Generation** | `gemini-omni-flash-preview` | Text-to-video generation for animated financial literacy lessons |
| **AI Image Generation** | `gemini-3.1-flash-lite-image` | High-quality digital artwork for savings certificates & goal badges |
| **Long-Term Memory** | Vertex AI Memory Bank | Cross-session memory persistence and child preference retrieval |
| **Knowledge Grounding (RAG)** | Vertex AI RAG Engine | Serverless vector database (`text-embedding-004`) for child safety guardrails |
| **Database** | Google Cloud Firestore | Real-time storage for goals, chores, ledger transactions, & etiquette streaks |
| **Object Storage** | Google Cloud Storage | Host public HTTPS media assets for generated concept videos and certificates |
| **UI Framework** | FastAPI + Vanilla Modern CSS | Lightweight web proxy and responsive 6-tile dashboard interface |

---

## 📂 Project Architecture

```
moneysprout/
├── app/
│   ├── agent.py               # Main ADK Agent definition, tool registration & instructions
│   └── a2ui_utils.py          # A2UI surface builders (cards, tables, buttons)
├── frontend/
│   ├── main.py                # FastAPI proxy connecting browser to Agent Runtime over A2A
│   └── static/
│       └── index.html         # Custom dark UI (2/3 dashboard tiles, 1/3 mascot chat drawer)
├── scripts/
│   ├── record_demo.py         # Automated Playwright video recording script
│   └── setup_firestore_data.py # Initializer for Firestore goal & chore collections
├── agents-cli-manifest.yaml   # Agent Runtime deployment manifest (acli 1.1.0)
├── demo.gif                   # Recorded live application demo
└── README.md                  # Technical documentation
```

---

## 🛠️ Local Development & Setup Instructions

### Prerequisites
- Python 3.11+
- Google Cloud SDK (`gcloud`) authenticated to a GCP project with Vertex AI, Firestore, and GCS enabled.
- `agents-cli` installed (`pip install google-agents-cli`).

### 1. Set Up Environment Variables
```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-east1"
export MONEYSPROUT_MEDIA_BUCKET="moneysprout-media-YOUR_PROJECT_ID"
```

### 2. Initialize Firestore Database
Seed the initial savings goals and allowance chores in Firestore:
```bash
python3 scripts/setup_firestore_data.py
```

### 3. Test Agent Locally with ADK Web UI
Run the local ADK developer playground to inspect tools, memory, and A2UI cards:
```bash
agents-cli web
```

### 4. Run Custom Production Web Interface
Start the FastAPI proxy and custom frontend locally:
```bash
python3 -m uvicorn frontend.main:app --host 0.0.0.0 --port 8080
```
Open a browser and navigate to port `8080` to interact with Sprout and the real-time financial dashboard.

### 5. Deploy to Production
- **Deploy Agent to Agent Runtime**:
  ```bash
  agents-cli deploy --no-confirm-project
  ```
- **Deploy Frontend to Cloud Run**:
  ```bash
  gcloud run deploy moneysprout-frontend --source ./frontend --region us-east1 --allow-unauthenticated
  ```

---

## 📝 Planned Features (Future Roadmap)
- [ ] Multi-child family profile switching with parental control permissions.
- [ ] Integration with real bank sandbox APIs for virtual debit card balance syncing.
