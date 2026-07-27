#!/usr/bin/env python3
"""
Create a Bedrock Knowledge Base for Platform Advisor.

Steps:
  1. Create S3 bucket for KB documents
  2. Upload all knowledge-base/ documents
  3. Create IAM role for the KB
  4. Create OpenSearch Serverless policies + collection
  5. Create the Knowledge Base
  6. Create the data source
  7. Start ingestion
  8. Write KB_ID to agentcore.json
"""
from __future__ import annotations
import boto3
import json
import os
import pathlib
import sys
import time

ACCOUNT_ID  = "616627284001"
REGION      = "us-east-1"
KB_BUCKET   = f"platform-advisor-kb-{ACCOUNT_ID}"
KB_PREFIX   = "knowledge-base/"
ROLE_NAME   = "platform-advisor-kb-role"
COLL_NAME   = "platform-advisor-kb"
KB_NAME     = "platform-advisor"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
EMBED_ARN   = f"arn:aws:bedrock:{REGION}::foundation-model/{EMBED_MODEL}"

REPO_ROOT  = pathlib.Path(__file__).parent.parent
KB_DIR     = REPO_ROOT / "knowledge-base"
AGENTCORE_JSON = REPO_ROOT / "PlatformAdvisorAgent" / "agentcore" / "agentcore.json"

sess = boto3.Session(profile_name="platform-advisor", region_name=REGION)
s3   = sess.client("s3")
iam  = sess.client("iam")
aoss = sess.client("opensearchserverless")
ba   = sess.client("bedrock-agent")

# ── Step 1: S3 bucket ──────────────────────────────────────────────────────────

def ensure_s3_bucket():
    print(f"[1/8] Creating S3 bucket: {KB_BUCKET}")
    try:
        s3.create_bucket(Bucket=KB_BUCKET)
        print(f"      Created {KB_BUCKET}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"      Already exists — skipping")
    # Block all public access
    s3.put_public_access_block(
        Bucket=KB_BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        },
    )

# ── Step 2: Upload documents ───────────────────────────────────────────────────

def upload_documents():
    print(f"[2/8] Uploading documents from {KB_DIR} → s3://{KB_BUCKET}/{KB_PREFIX}")
    uploaded = 0
    for path in KB_DIR.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".txt", ".pdf", ".json"):
            # Skip graph.json (large, machine-readable only)
            if path.name == "graph.json":
                continue
            key = KB_PREFIX + str(path.relative_to(KB_DIR))
            s3.upload_file(str(path), KB_BUCKET, key)
            print(f"      ✓ {key}")
            uploaded += 1
    print(f"      {uploaded} files uploaded")

# ── Step 3: IAM role ───────────────────────────────────────────────────────────

def ensure_iam_role() -> str:
    print(f"[3/8] Creating IAM role: {ROLE_NAME}")
    trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": ACCOUNT_ID},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:knowledge-base/*"
                },
            },
        }],
    }
    try:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description="Bedrock Knowledge Base role for Platform Advisor",
        )
        role_arn = resp["Role"]["Arn"]
        print(f"      Created {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=ROLE_NAME)["Role"]["Arn"]
        print(f"      Already exists — {role_arn}")

    # Inline policy: S3 read + Bedrock embed + AOSS
    inline = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    f"arn:aws:s3:::{KB_BUCKET}",
                    f"arn:aws:s3:::{KB_BUCKET}/*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": EMBED_ARN,
            },
            {
                "Effect": "Allow",
                "Action": ["aoss:APIAccessAll"],
                "Resource": f"arn:aws:aoss:{REGION}:{ACCOUNT_ID}:collection/*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="platform-advisor-kb-policy",
        PolicyDocument=json.dumps(inline),
    )
    print("      Inline policy attached")
    return role_arn

# ── Step 4: OpenSearch Serverless ─────────────────────────────────────────────

def ensure_aoss_collection() -> str:
    """Returns the collection ARN."""
    print(f"[4/8] Setting up OpenSearch Serverless collection: {COLL_NAME}")

    enc_name = f"{COLL_NAME}-enc"
    net_name = f"{COLL_NAME}-net"
    acc_name = f"{COLL_NAME}-access"

    # Encryption policy
    try:
        aoss.create_security_policy(
            name=enc_name,
            type="encryption",
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{COLL_NAME}"]}],
                "AWSOwnedKey": True,
            }),
        )
        print("      Encryption policy created")
    except aoss.exceptions.ConflictException:
        print("      Encryption policy already exists")

    # Network policy (public access for API)
    try:
        aoss.create_security_policy(
            name=net_name,
            type="network",
            policy=json.dumps([{
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/{COLL_NAME}"]},
                    {"ResourceType": "dashboard", "Resource": [f"collection/{COLL_NAME}"]},
                ],
                "AllowFromPublic": True,
            }]),
        )
        print("      Network policy created")
    except aoss.exceptions.ConflictException:
        print("      Network policy already exists")

    # Data access policy — allow KB role + caller principal
    caller_arn = sess.client("sts").get_caller_identity()["Arn"]
    # Normalize assumed-role ARN → IAM user/role ARN for data access
    # e.g. arn:aws:sts::acct:assumed-role/role/session → arn:aws:iam::acct:role/role
    if ":assumed-role/" in caller_arn:
        parts = caller_arn.split("/")
        caller_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{parts[1]}"

    role_arn_for_access = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
    try:
        aoss.create_access_policy(
            name=acc_name,
            type="data",
            policy=json.dumps([{
                "Rules": [
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{COLL_NAME}/*"],
                        "Permission": [
                            "aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex",
                            "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument",
                        ],
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{COLL_NAME}"],
                        "Permission": ["aoss:CreateCollectionItems", "aoss:DescribeCollectionItems", "aoss:UpdateCollectionItems"],
                    },
                ],
                "Principal": [role_arn_for_access, caller_arn],
            }]),
        )
        print("      Data access policy created")
    except aoss.exceptions.ConflictException:
        print("      Data access policy already exists")

    # Create collection
    try:
        resp = aoss.create_collection(
            name=COLL_NAME,
            type="VECTORSEARCH",
            description="Platform Advisor knowledge base vector store",
        )
        coll_id = resp["createCollectionDetail"]["id"]
        print(f"      Collection created (id={coll_id}) — waiting for ACTIVE...")
    except aoss.exceptions.ConflictException:
        existing = aoss.list_collections(collectionFilters={"name": COLL_NAME})
        coll_id = existing["collectionSummaries"][0]["id"]
        print(f"      Collection already exists (id={coll_id})")

    # Wait for ACTIVE
    for _ in range(40):
        details = aoss.batch_get_collection(ids=[coll_id])["collectionDetails"]
        if details and details[0]["status"] == "ACTIVE":
            coll_arn = details[0]["arn"]
            endpoint  = details[0].get("collectionEndpoint", "")
            print(f"      ACTIVE — endpoint: {endpoint}")
            return coll_arn
        print("      ... waiting 15s for collection to become ACTIVE")
        time.sleep(15)

    raise RuntimeError("Collection did not become ACTIVE within 10 minutes")

# ── Step 5: Create Knowledge Base ─────────────────────────────────────────────

def create_knowledge_base(role_arn: str, coll_arn: str) -> str:
    print(f"[5/8] Creating Knowledge Base: {KB_NAME}")

    # Check if it already exists
    existing = ba.list_knowledge_bases()
    for kb in existing.get("knowledgeBaseSummaries", []):
        if kb["name"] == KB_NAME and kb["status"] not in ("DELETE_UNSUCCESSFUL", "DELETING", "FAILED"):
            print(f"      Already exists — id={kb['knowledgeBaseId']}")
            return kb["knowledgeBaseId"]

    resp = ba.create_knowledge_base(
        name=KB_NAME,
        description="Platform Advisor architecture patterns, anti-patterns, and compliance overlays",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": EMBED_ARN,
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": coll_arn,
                "vectorIndexName": "platform-advisor-index",
                "fieldMapping": {
                    "vectorField": "embedding",
                    "textField": "text",
                    "metadataField": "metadata",
                },
            },
        },
    )
    kb_id = resp["knowledgeBase"]["knowledgeBaseId"]
    print(f"      Created — id={kb_id}")

    # Wait for ACTIVE
    for _ in range(20):
        detail = ba.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
        if detail["status"] == "ACTIVE":
            print("      Status: ACTIVE")
            return kb_id
        if detail["status"] == "FAILED":
            raise RuntimeError(f"Knowledge Base creation FAILED: {detail.get('failureReasons')}")
        print(f"      ... waiting 10s (status={detail['status']})")
        time.sleep(10)

    raise RuntimeError("Knowledge Base did not become ACTIVE")

# ── Step 6: Create data source ─────────────────────────────────────────────────

def create_data_source(kb_id: str) -> str:
    print(f"[6/8] Creating S3 data source")

    existing = ba.list_data_sources(knowledgeBaseId=kb_id)
    for ds in existing.get("dataSourceSummaries", []):
        if ds["name"] == "platform-advisor-docs":
            print(f"      Already exists — id={ds['dataSourceId']}")
            return ds["dataSourceId"]

    resp = ba.create_data_source(
        knowledgeBaseId=kb_id,
        name="platform-advisor-docs",
        description="Knowledge base documents from knowledge-base/",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{KB_BUCKET}",
                "inclusionPrefixes": [KB_PREFIX],
            },
        },
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 512,
                    "overlapPercentage": 20,
                },
            }
        },
    )
    ds_id = resp["dataSource"]["dataSourceId"]
    print(f"      Created — id={ds_id}")
    return ds_id

# ── Step 7: Start ingestion ────────────────────────────────────────────────────

def start_ingestion(kb_id: str, ds_id: str):
    print(f"[7/8] Starting ingestion job")
    resp = ba.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    job_id = resp["ingestionJob"]["ingestionJobId"]
    print(f"      Job started — id={job_id}")
    print(f"      Ingestion runs async. Check status with:")
    print(f"      aws bedrock-agent get-ingestion-job --knowledge-base-id {kb_id} --data-source-id {ds_id} --ingestion-job-id {job_id}")
    return job_id

# ── Step 8: Wire KB_ID into agentcore.json ────────────────────────────────────

def wire_kb_id(kb_id: str):
    print(f"[8/8] Wiring KNOWLEDGE_BASE_ID={kb_id} into agentcore.json")
    with open(AGENTCORE_JSON) as f:
        cfg = json.load(f)

    for runtime in cfg.get("runtimes", []):
        for env in runtime.get("envVars", []):
            if env["name"] == "KNOWLEDGE_BASE_ID":
                env["value"] = kb_id
                break

    with open(AGENTCORE_JSON, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"      agentcore.json updated")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== Platform Advisor — Bedrock Knowledge Base Setup ===\n")
    ensure_s3_bucket()
    upload_documents()
    role_arn = ensure_iam_role()
    # Small delay so IAM propagates
    print("      Waiting 10s for IAM propagation...")
    time.sleep(10)
    coll_arn = ensure_aoss_collection()
    kb_id    = create_knowledge_base(role_arn, coll_arn)
    ds_id    = create_data_source(kb_id)
    start_ingestion(kb_id, ds_id)
    wire_kb_id(kb_id)

    print(f"\n✓ Done! Knowledge Base ID: {kb_id}")
    print(f"\nNext steps:")
    print(f"  1. Wait 2-3 min for ingestion to complete")
    print(f"  2. cd PlatformAdvisorAgent && agentcore deploy --target default --yes")

if __name__ == "__main__":
    main()
