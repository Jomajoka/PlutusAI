"""
Module A -- Data Ingestion.
Trigger: S3 ObjectCreated. Client obtains a presigned upload URL first (key prefixed
with the caller's business_id, derived from the JWT).
Steps: map CSV columns -> internal schema, validate, batch-write to DynamoDB,
report rejected rows instead of failing the whole file. Preserve extra columns.
Output: { business_id, records: [{date, product, units_sold, unit_price, unit_cost, ...extras}] }
Test in isolation: upload a sample CSV, confirm records land in DynamoDB.
See docs/implementation-plan.md Module A for the full contract.
"""

def handler(event, context):
    raise NotImplementedError

def create_upload_url(event, context):
    """API endpoint: returns a presigned S3 PUT URL for the caller's business."""
    raise NotImplementedError
