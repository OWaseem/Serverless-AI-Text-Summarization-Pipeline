# Serverless AI Text Summarization Pipeline

A production-style serverless pipeline that accepts text via a REST API, summarizes it using Amazon Bedrock (Claude 3 Haiku), tags its sentiment, and stores the results in DynamoDB for fast retrieval — all without managing a single server.

---

## What Is This Project?

At its core, this project solves a real problem: **people and businesses deal with enormous amounts of text** — articles, reports, legal documents, emails, research papers — and reading all of it manually takes time they don't have.

This pipeline automates two things:
1. **Summarization** — takes a long piece of text and condenses it to the key points (up to 80% shorter)
2. **Sentiment tagging** — automatically labels the tone (positive, negative, or neutral) without anyone reading it

The result is stored persistently and retrievable instantly — so you're not just summarizing in real time, you're building a **searchable knowledge base** of processed documents.

---

## Why Build This Instead of Using a Summarizer Website?

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

**Ownership matters too.** When you use someone else's website, your data goes to their servers and you're dependent on their uptime and pricing. When you own the pipeline, your data stays in your AWS account and you control everything.

---

## Who Benefits From This?

| Use Case | How They Use It |
|---|---|
| Law firms | Auto-summarize contracts and case files |
| News organizations | Tag article sentiment before publishing |
| Customer support teams | Triage thousands of feedback responses automatically |
| Research teams | Ingest and condense academic papers at scale |
| Developers | Use this architecture as a blueprint for any AI automation task |

---

## Why Serverless?

This project could have been built on a traditional server (like an EC2 instance). Serverless is better here for three reasons:

1. **No idle cost** — you pay only when someone actually calls the API. A traditional server costs money 24/7 whether it's being used or not.
2. **Auto-scales automatically** — if 1,000 requests hit at once, AWS Lambda spins up 1,000 instances in parallel. A traditional server would queue them or crash.
3. **Zero maintenance** — no patching, no uptime monitoring, no server management. The infrastructure takes care of itself.

---

## Architecture

```
Client (Postman / any app)
         │
         ▼
    API Gateway
         │
         ├── POST /summarize ──────► SummarizeFunction (Lambda)
         │                                    │
         │                          ┌─────────┴──────────┐
         │                          ▼                    ▼
         │                   Amazon Bedrock          DynamoDB
         │                 (Claude 3 Haiku)        (store result)
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

## AWS Services Used

### API Gateway
The front door of the application. It receives HTTP requests from the outside world and routes them to the correct Lambda function. Think of it as a traffic controller — it doesn't do any processing itself, it just directs requests to the right place.

### AWS Lambda
The serverless compute layer. Lambda runs your Python code in response to events (in this case, API Gateway requests). It spins up automatically when needed and shuts down when done — you never manage a server.

### Amazon Bedrock
AWS's managed AI service. Instead of training a model yourself, you send a prompt to Bedrock and get an AI-generated response back. This project uses **Claude 3 Haiku** by Anthropic — the fastest and most cost-efficient Claude model, ideal for hitting sub-100ms processing targets.

**Why Claude 3 Haiku specifically?**
- Fastest response time in the Claude 3 family
- Cheapest per token (~$0.00025 per 1,000 input tokens)
- More than capable enough for summarization and sentiment tagging
- Available directly through Amazon Bedrock — no separate Anthropic account needed

### DynamoDB
AWS's fully managed NoSQL database. It stores the summarization results (original text, summary, sentiment, timestamp) keyed by a unique ID. DynamoDB is built for single-digit millisecond retrieval — which is how this pipeline achieves sub-100ms read performance.

### CloudWatch
AWS's logging and monitoring service. Every Lambda invocation automatically writes logs to CloudWatch — what was received, what was sent to Bedrock, what was stored, and any errors. Zero configuration required.

---

## Project Structure

```
Serverless_AI_Text_Summarization_Pipeline/
├── template.yaml          # SAM template — defines ALL AWS infrastructure as code
├── samconfig.toml         # SAM deploy config (region, stack name, S3 bucket)
├── requirements.txt       # Python dependencies
├── src/
│   ├── summarize/
│   │   └── handler.py    # POST /summarize — calls Bedrock, writes to DynamoDB
│   └── retrieve/
│       └── handler.py    # GET /summary/{id} — reads from DynamoDB
└── postman/
    └── collection.json   # Pre-built Postman collection to test both endpoints
```

### What is AWS SAM?
AWS SAM (Serverless Application Model) is a framework for defining serverless infrastructure as code. Instead of clicking through the AWS Console to create Lambda functions, API Gateway routes, and DynamoDB tables manually, you define everything in a single `template.yaml` file and deploy it with two commands. This makes the infrastructure version-controlled, repeatable, and shareable.

---

## API Reference

### POST /summarize
Summarizes a piece of text and tags its sentiment.

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
  "sentiment": "positive"
}
```

### GET /summary/{id}
Retrieves a previously stored summarization result by ID.

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "original_text": "Your original text...",
  "summary": "Condensed version of the text.",
  "sentiment": "positive",
  "timestamp": "2025-09-15T14:23:01.123456"
}
```

---

## Prerequisites

Before deploying, make sure you have:

- [ ] An AWS account
- [ ] [AWS CLI](https://aws.amazon.com/cli/) installed and configured (`aws configure`)
- [ ] [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- [ ] Amazon Bedrock model access enabled for **Claude 3 Haiku** in the AWS Console (Bedrock → Model access → Request access)
- [ ] [Postman](https://www.postman.com/downloads/) installed for testing

---

## Deployment

```bash
# 1. Build the project (packages Lambda code and dependencies)
sam build

# 2. Deploy to AWS (first time — walks you through setup)
sam deploy --guided

# On subsequent deploys:
sam deploy
```

After deploying, SAM will output your **API Gateway URL**. Copy it — you'll need it in Postman.

---

## Testing with Postman

1. Open Postman and import `postman/collection.json`
2. Set the `base_url` collection variable to your API Gateway URL
3. Run **POST /summarize** with sample text
4. Copy the `id` from the response
5. Run **GET /summary/{id}** using that ID
6. Check AWS Console → CloudWatch → Log Groups to see Lambda logs

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| IaC framework | AWS SAM | Purpose-built for serverless, minimal boilerplate |
| AI model | Claude 3 Haiku | Fastest + cheapest Claude model, hits latency targets |
| Database | DynamoDB on-demand | No capacity planning, free-tier friendly, sub-10ms reads |
| Runtime | Python 3.11 | Latest stable Lambda runtime, best boto3 support |
| Lambda timeout | 30 seconds | Bedrock calls typically take 2–5s, leaving ample buffer |
| Prompt design | Structured JSON output | Forces Haiku to return `{summary, sentiment}` — makes parsing reliable |
