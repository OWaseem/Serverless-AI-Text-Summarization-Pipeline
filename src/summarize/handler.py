import json
import boto3
import uuid
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# AWS Clients — initialized OUTSIDE the handler function intentionally.
#
# Lambda reuses the same execution environment for multiple invocations
# (this is called a "warm start"). By initializing clients here once,
# we avoid reconnecting to AWS on every single request — faster performance.
# ---------------------------------------------------------------------------
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])  # Injected by template.yaml at deploy time

# Guardrail config — injected at deploy time via template.yaml environment variables.
# The guardrail runs automatically on both the input (your text) and the model's output.
# If content violates the policy, Bedrock returns stopReason = "guardrail_intervened"
# instead of a normal response — we handle that case below.
GUARDRAIL_ID = os.environ["GUARDRAIL_ID"]
GUARDRAIL_VERSION = os.environ["GUARDRAIL_VERSION"]


def lambda_handler(event, context):
    """
    Entry point for the POST /summarize Lambda.

    `event`   — contains everything about the incoming HTTP request
                 (headers, body, path, method, etc.)
    `context` — metadata about the Lambda invocation (timeout, memory, etc.)
                 We don't need it here but Lambda always passes it.
    """

    # -----------------------------------------------------------------------
    # Step 1: Parse the request body
    #
    # API Gateway sends the HTTP body as a string inside event["body"].
    # We use json.loads() to convert that string into a Python dictionary
    # so we can access individual fields like body["text"].
    # -----------------------------------------------------------------------
    try:
        body = json.loads(event.get("body", "{}"))
        text = body.get("text", "").strip()

        if not text:
            return _response(400, {"error": "Request body must include a non-empty 'text' field."})

    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON in request body."})

    # -----------------------------------------------------------------------
    # Step 2: Build the prompt for Claude 3 Haiku
    #
    # A "prompt" is the instruction we send to the AI model. How you write
    # the prompt directly affects the quality and format of the output.
    #
    # We're asking Haiku to return a JSON object with exactly two fields:
    #   - "summary": the condensed version of the text
    #   - "sentiment": one of positive / negative / neutral
    #
    # Telling the model to respond in JSON makes it easy to parse reliably.
    # -----------------------------------------------------------------------
    prompt = f"""You are a text analysis assistant. Analyze the following text and respond with ONLY a valid JSON object — no explanation, no markdown, no code fences.

The JSON must have exactly these two fields:
- "summary": a concise summary of the text (at most 3 sentences)
- "sentiment": one of exactly these values: "positive", "negative", or "neutral"

Text to analyze:
{text}"""

    # -----------------------------------------------------------------------
    # Step 3: Call Amazon Bedrock (Claude Haiku 4.5)
    #
    # We use the `converse` API — Bedrock's newer, standardized way to call
    # any model. Unlike `invoke_model` which has model-specific request formats,
    # `converse` works consistently across all Claude models.
    #
    # We send:
    #   - modelId: which model to use
    #   - messages: a list of conversation turns (just one user turn here)
    #   - inferenceConfig: settings like max tokens (caps the response length)
    # -----------------------------------------------------------------------
    try:
        bedrock_response = bedrock.converse(
            modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            inferenceConfig={
                "maxTokens": 512
            },
            # Guardrail runs on both the incoming text (input) and the model's reply (output).
            # If either violates the policy, stopReason will be "guardrail_intervened"
            # and Bedrock will NOT return the model's output.
            guardrailConfig={
                "guardrailIdentifier": GUARDRAIL_ID,
                "guardrailVersion": GUARDRAIL_VERSION,
                "trace": "enabled"
            }
        )

        # Check if the guardrail blocked this request before attempting to parse
        stop_reason = bedrock_response.get("stopReason", "")
        if stop_reason == "guardrail_intervened":
            # Log the trace so we can see which filter triggered (visible in CloudWatch)
            print("GUARDRAIL_TRACE:", json.dumps(bedrock_response.get("trace", {})))
            return _response(400, {"error": "Request blocked: the submitted text contains content that violates our usage policy."})

        # The converse API returns the model's reply here:
        ai_text = bedrock_response["output"]["message"]["content"][0]["text"]

        # Claude sometimes wraps its JSON response in markdown code fences
        # like ```json ... ``` even when told not to. We strip those here
        # by finding the first { and last } and extracting just that slice.
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1
        ai_text = ai_text[start:end]

        # Parse the JSON the model returned
        ai_output = json.loads(ai_text)
        summary = ai_output["summary"]
        sentiment = ai_output["sentiment"]

    except (KeyError, json.JSONDecodeError) as e:
        return _response(502, {"error": f"Unexpected response format from Bedrock: {str(e)}"})
    except Exception as e:
        return _response(502, {"error": f"Bedrock invocation failed: {str(e)}"})

    # -----------------------------------------------------------------------
    # Step 4: Store the result in DynamoDB
    #
    # uuid4() generates a random unique ID — this becomes the record's
    # primary key and is returned to the caller so they can retrieve it later.
    #
    # We store the original text too so the GET endpoint can return it.
    # -----------------------------------------------------------------------
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    table.put_item(Item={
        "id": record_id,
        "original_text": text,
        "summary": summary,
        "sentiment": sentiment,
        "timestamp": timestamp
    })

    # -----------------------------------------------------------------------
    # Step 5: Return the response to the caller
    #
    # We return the ID so they can use it with GET /summary/{id} later.
    # -----------------------------------------------------------------------
    return _response(200, {
        "id": record_id,
        "summary": summary,
        "sentiment": sentiment,
        "timestamp": timestamp
    })


def _response(status_code, body):
    """
    Helper to format a Lambda response in the shape API Gateway expects.
    API Gateway requires statusCode and body (as a string) — this handles that.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
