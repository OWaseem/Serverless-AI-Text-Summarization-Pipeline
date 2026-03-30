# Serverless AI Text Summarization Pipeline

A production-style serverless pipeline that accepts text via a REST API, summarizes it using Amazon Bedrock (Claude Haiku 4.5), tags its sentiment, and stores the results in DynamoDB for fast retrieval — all without managing a single server.

---

## What Is This Project?

At its core, this project solves a real problem: **people and businesses deal with enormous amounts of text** — articles, reports, legal documents, emails, research papers — and reading all of it manually takes time they don't have.

This pipeline automates two things:
1. **Summarization** — takes a long piece of text and condenses it to the key points (up to 80% shorter)
2. **Sentiment tagging** — automatically labels the tone (positive, negative, or neutral) without anyone reading it

The result is stored persistently and retrievable instantly — so you're not just summarizing in real time, you're building a **searchable knowledge base** of processed documents.

---

## Why Not Just Use a Summarizer Website?

You might wonder: why build this when you could just paste text into QuillBot or TLDR This?

**A summarizer website:**
- Requires a human to open a browser, paste text, click a button, and read the result
- Handles one document at a time, manually
- Stores nothing — results disappear when you close the tab
- Can't be integrated into any other system

**This pipeline:**
- Any application, script, or system can send text to the API and get a summary back **automatically** — no human involved
- Results are **stored permanently** in DynamoDB and retrievable by ID at any time
- Can handle **thousands of requests simultaneously** without any manual work
- Can be plugged into larger systems — a news app auto-summarizing articles, a CRM auto-tagging customer feedback, a hospital summarizing patient notes overnight

> A summarizer website is like a **calculator** — useful when a human sits down and uses it manually.
> This pipeline is like a **spreadsheet formula** — it runs automatically, every time, on any data, without anyone touching it.

**Ownership matters too.** Your data stays in your own AWS account — not on a third-party server. You control the model, the prompt, the output format, and the cost.

---

## Who Is This For?

| Use Case | How They Use It |
|---|---|
| Law firms | Auto-summarize contracts and case files |
| News organizations | Tag article sentiment before publishing |
| Customer support teams | Triage thousands of feedback responses automatically |
| Research teams | Ingest and condense academic papers at scale |
| Developers | Drop this into any existing system via a single API call |

---

## Why Serverless?

This pipeline runs on AWS Lambda — meaning there is no server to manage, patch, or monitor.

1. **No idle cost** — you pay only when the API is actually called. A traditional server costs money 24/7 whether it's being used or not.
2. **Auto-scales automatically** — if 1,000 requests hit at once, AWS spins up 1,000 instances in parallel. A traditional server would queue them or crash.
3. **Zero maintenance** — the infrastructure takes care of itself. No downtime, no intervention needed.

---

## Architecture

```
Client (any app or API caller)
         │
         ▼
    API Gateway  ◄── API Key Authentication (x-api-key header required)
         │
         ├── POST /summarize ──────► SummarizeFunction (Lambda)
         │                                    │
         │                          Bedrock Guardrails
         │                    (content filter + PII check)
         │                                    │
         │                          ┌─────────┴──────────┐
         │                          ▼                    ▼
         │                   Amazon Bedrock          DynamoDB
         │                 (Claude Haiku 4.5)      (store result)
         │                 summarize + sentiment
         │
         └── GET /summary/{id} ───► RetrieveFunction (Lambda)
                                              │
                                              ▼
                                          DynamoDB
                                        (fetch by ID)

CloudWatch automatically logs all Lambda activity.
```

---

## What Powers This?

### API Gateway
The entry point. Receives HTTP requests and routes them to the correct Lambda function. All endpoints are protected by **API key authentication** — unauthorized requests are rejected before they ever reach the pipeline.

### AWS Lambda
Serverless compute. Runs the pipeline logic in response to each request — no server required. Auto-scaling is built in by design.

### Amazon Bedrock (Claude Haiku 4.5)
The AI brain. Sends text to Anthropic's Claude Haiku 4.5 model via AWS's managed Bedrock service and gets back a structured summary and sentiment label. Claude Haiku 4.5 is the latest and most efficient model in its class — optimized for speed and high-volume workloads.

### DynamoDB
Persistent storage. Every result is saved with its ID, original text, summary, sentiment, and timestamp. Built for sub-10ms retrieval — results come back in under 100ms.

### Amazon Bedrock Guardrails
A content safety layer that runs on every request before the text reaches the model. It blocks hate speech, sexual content, and graphic violence, anonymizes personally identifiable information (names, emails, phone numbers), and hard-blocks sensitive data like social security numbers and credit card numbers. Requests that violate the policy are rejected with a 400 error — the model never sees the content and nothing is stored.

### CloudWatch
Automatic logging. Every invocation is logged — timestamps, duration, memory usage, errors — with zero configuration.

---

## API Reference

All requests require the header:
```
x-api-key: <your-api-key>
```

### POST /summarize
Submits text for summarization and sentiment tagging.

**Request body:**
```json
{
  "text": "Your long-form text goes here..."
}
```

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "summary": "Condensed version of the text.",
  "sentiment": "neutral",
  "timestamp": "2026-03-29T00:09:31.272043+00:00"
}
```

### GET /summary/{id}
Retrieves a previously stored result by ID.

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "original_text": "Your original text...",
  "summary": "Condensed version of the text.",
  "sentiment": "neutral",
  "timestamp": "2026-03-29T00:09:31.272043+00:00"
}
```

---

## Usage Examples

The pipeline is a standard HTTP API — anything that can make a web request can use it. Place the text you want summarized in the `"text"` field of the request body.

### Postman
1. Import `postman/collection.json` into Postman
2. Set the `base_url` collection variable to your API Gateway URL
3. Add header `x-api-key` with your API key value
4. Open **POST /summarize** → go to the **Body** tab → paste your text into the `"text"` field
5. Hit **Send** — the response returns your summary, sentiment, and a record ID
6. Use that ID with **GET /summary/{id}** to retrieve the result at any time

### curl (terminal)
```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod/summarize \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{"text": "Paste any long-form text here and the pipeline will summarize it and tag its sentiment automatically."}'
```

### Python
```python
import requests

response = requests.post(
    "https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod/summarize",
    headers={
        "x-api-key": "your-api-key",
        "Content-Type": "application/json"
    },
    json={"text": "Paste any long-form text here."}
)
print(response.json())
```

### JavaScript
```javascript
const response = await fetch("https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod/summarize", {
  method: "POST",
  headers: {
    "x-api-key": "your-api-key",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ text: "Paste any long-form text here." })
});

const data = await response.json();
console.log(data);
```

Replace `your-api-id` with your API Gateway URL and `your-api-key` with your API key value.

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| IaC framework | AWS SAM | Purpose-built for serverless, minimal boilerplate |
| AI model | Claude Haiku 4.5 | Latest Haiku — fastest and most capable in class |
| Bedrock API | `converse` | Universal API compatible across all Claude models |
| Authentication | API Key (x-api-key) | Protects endpoints from abuse without requiring full user auth |
| Database | DynamoDB on-demand | No capacity planning, free-tier friendly, sub-10ms reads |
| Runtime | Python 3.11 | Stable Lambda runtime with full boto3 support |
| Lambda timeout | 30 seconds | Bedrock calls typically take 2–5s, leaving ample buffer |
| Content safety | Bedrock Guardrails | Blocks harmful content and anonymizes PII before the model sees it |

---

<details>
<summary><strong>For Developers — Deploy Your Own Instance</strong></summary>

### Prerequisites

- An AWS account
- AWS CLI installed and configured (`aws configure`)
- AWS SAM CLI installed
- Claude Haiku 4.5 access via Amazon Bedrock — go to Bedrock → Model catalog → Claude Haiku 4.5 → subscribe
- Postman for testing

### Deployment

```bash
# Build the project
sam build

# First-time deploy
sam deploy --guided

# Subsequent deploys
sam build
sam deploy
```

After deploying, SAM outputs:
- **SummarizeApiUrl** — your API Gateway base URL
- **ApiKeyId** — go to AWS Console → API Gateway → API Keys → find your key → click Show to retrieve the value

### Testing with Postman

1. Import `postman/collection.json` into Postman
2. Set the `base_url` collection variable to your API Gateway URL
3. Add header `x-api-key` with your key value to each request
4. Run **POST /summarize** → copy the `id` from the response
5. Run **GET /summary/{id}** using that ID
6. Check CloudWatch → Log Management to view Lambda logs

</details>
