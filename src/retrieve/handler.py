import json
import boto3
import os

# ---------------------------------------------------------------------------
# AWS client initialized outside the handler for warm-start performance.
# Same pattern as the summarize Lambda.
# ---------------------------------------------------------------------------
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def lambda_handler(event, context):
    """
    Entry point for the GET /summary/{id} Lambda.

    API Gateway extracts the {id} path parameter and puts it in:
    event["pathParameters"]["id"]
    """

    # -----------------------------------------------------------------------
    # Step 1: Extract the ID from the URL path
    #
    # When someone calls GET /summary/abc-123, API Gateway parses the URL
    # and puts {"id": "abc-123"} into event["pathParameters"].
    # -----------------------------------------------------------------------
    path_params = event.get("pathParameters") or {}
    record_id = path_params.get("id", "").strip()

    if not record_id:
        return _response(400, {"error": "Missing required path parameter: id"})

    # -----------------------------------------------------------------------
    # Step 2: Look up the record in DynamoDB
    #
    # get_item() does a direct key lookup — this is O(1), not a scan.
    # That's why DynamoDB can return results in under 10ms.
    # If the key doesn't exist, DynamoDB returns an empty response (no error).
    # -----------------------------------------------------------------------
    result = table.get_item(Key={"id": record_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": f"No record found with id: {record_id}"})

    return _response(200, item)


def _response(status_code, body):
    """
    Formats a Lambda response in the shape API Gateway expects.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
