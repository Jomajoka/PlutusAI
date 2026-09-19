// Thin wrapper around API Gateway endpoints.
// Until backend Lambdas are ready, mock each function below to match the
// contracts in docs/implementation-plan.md so frontend work isn't blocked.
// NOTE: no business_id parameters -- the backend derives it from the auth token.

export async function getUploadUrl(filename) { /* -> Module A (create_upload_url), then PUT file to S3 */ }
export async function getDashboard() { /* -> Module B (generate-dashboard) */ }
export async function sendChatMessage(sessionId, message) { /* -> Module C (chat-agent); transport TBD */ }
export async function listScenarios() { /* -> read-only convenience over the Scenarios table */ }
