#!/usr/bin/env python3
"""
Create DynamoDB Local table for local development.
Run once after `docker compose up -d`.

Usage:
    python infra/setup-local-db.py
"""
import boto3
from botocore.exceptions import ClientError

ENDPOINT = "http://localhost:8000"
TABLE_NAME = "platform-advisor-main"
REGION = "us-east-1"

dynamodb = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)


def create_table():
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        print(f"Table '{TABLE_NAME}' created successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{TABLE_NAME}' already exists — skipping.")
        else:
            raise


def seed_demo_customer():
    import uuid
    from datetime import datetime, timezone

    dynamodb_resource = boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )
    table = dynamodb_resource.Table(TABLE_NAME)
    now = datetime.now(timezone.utc).isoformat()
    cust_id = "cust_demo00000001"

    try:
        table.put_item(
            Item={
                "PK": f"CUSTOMER#{cust_id}",
                "SK": "METADATA",
                "customer_id": cust_id,
                "name": "Acme Financial Corp",
                "industry": "Financial Services",
                "contact_email": "demo@acmefinancial.com",
                "notes": "Demo customer — pre-loaded for local development",
                "created_by": "system",
                "created_at": now,
                "updated_at": now,
                "session_count": 0,
                "GSI1PK": "CUSTOMERS",
                "GSI1SK": now,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
        print(f"Demo customer '{cust_id}' seeded.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("Demo customer already exists — skipping seed.")
        else:
            raise


if __name__ == "__main__":
    create_table()
    seed_demo_customer()
    print("Local DB setup complete.")
