# Worker transport implementation checklist

Before any successor worker performs its create-once write:

1. Construct the complete report object and validate it against the exact frozen schema.
2. Compute HMAC independently: remove only `worker_auth_proof`, compact sorted-key UTF-8 JSON, HMAC-SHA256, then insert the proof.
3. Serialize the complete signed object for storage as sorted-key pretty JSON with two-space indentation and a final newline.
4. Before the GitHub write, compare the exact bytes to `json.dumps(report, sort_keys=true, indent=2, ensure_ascii=false) + "\n"`; any mismatch aborts without writing.
5. Ensure no tab and no line >8192 UTF-8 bytes.
6. Write exactly the assigned report path once. Do not patch/overwrite a malformed committed report.
7. Leave post-write authoritative structural reread to the branch reconciler/MM06.

This implements the existing `BRANCH_WORKER_PROTOCOL.md` transport contract; it does not change protocol semantics.
