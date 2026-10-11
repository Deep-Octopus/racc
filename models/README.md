# Models

Small checkpoints only.

| Path | Contents |
| --- | --- |
| `tfidf_checkpoint.joblib` | Frozen TF-IDF vectorizer and linear heads. |
| `tfidf_vocabulary.json` | The vectorizer vocabulary, token to index, plus `text_chars`, `tfidf_features`, and the horizon names. |
| `tfidf_hyperparameters.json` | Fit split, selection split, threshold `protect_min_risk`, and the static-head training counts. |
| `qwen3_0.6b_lora/adapter_model.safetensors` | LoRA weights for the 0.6B ranker. |
| `qwen3_0.6b_lora/adapter_config.json` | LoRA config. `base_model_name_or_path` is the public id `Qwen/Qwen3-0.6B`. |
| `qwen3_0.6b_lora/training.json` | Epochs, steps, losses, sequence length, and seed. |

The base weights of Qwen3-0.6B are not in this package. Load them with the public model id `Qwen/Qwen3-0.6B` and apply the adapter. The ranker is a sequence-classification LoRA on `q_proj` and `v_proj` with rank 8, alpha 16, and dropout 0.05. The tokenizer and the base vocabulary are part of that public model and are not copied here.

Loading the joblib needs scikit-learn, joblib, and numpy. The version that wrote the file was scikit-learn 1.9.1. `reproduce_tables.py` does not load it.
