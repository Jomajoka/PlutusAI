"""
Defines: API Gateway (Cognito-authorized) + all Lambdas (ingest-csv,
generate-dashboard, chat-agent, run-simulation) and their DynamoDB/S3/Bedrock permissions.
Open decisions (plan Section 10): chat transport, shared-code packaging
(layer vs bundle), pandas via AWS SDK-for-pandas layer, Bedrock model/region in config.
"""
