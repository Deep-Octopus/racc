# Protocols

Frozen `protocol.json`, `protocol.sha256`, and `seal.json` for `rv1_heldout`, `rv1_heldout_ext`, and `rv1_capacity`.

Absolute paths from the machine that ran the study were replaced by `/data/` for anonymization after sealing. The hashes in `protocol.sha256` and in each `seal.json` were recomputed on the anonymized `protocol.json`, so inside this package every seal matches the protocol bytes it covers. Hashes recorded for inputs that are not part of this package (datasets, tokenizer files, score files) are unchanged. The hashes of the original, pre-anonymization files are kept by the authors and can be provided after de-anonymization.

The `api_key` fields hold the placeholder `local-qwen` of a locally served model, and `172.17.0.1` is a private container address; neither is a credential or an identifier.
