"""Local embedding and reranking models, run with ONNX Runtime (no torch).

No Django and only lazy heavy imports, so the Docker build can import it to pre-bake
the models offline (see backend/Dockerfile) without pulling the rest of the app.
Single source of truth shared by the runtime code and the image bake.
"""

import threading

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MAX_TOKENS = 128  # the model's sentence_bert_config max_seq_length
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
RERANKER_MAX_TOKENS = 512

# local models share one device; concurrent inference aborts the process on Metal (MPS)
INFERENCE_LOCK = threading.Lock()


class _OnnxModel:
    def __init__(self, repo: str, max_tokens: int):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        self.session = ort.InferenceSession(
            hf_hub_download(repo, "onnx/model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = Tokenizer.from_file(hf_hub_download(repo, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=max_tokens)
        self.tokenizer.enable_padding()
        self._inputs = {i.name for i in self.session.get_inputs()}

    def _run(self, batch):
        import numpy as np

        encoded = self.tokenizer.encode_batch(batch)
        arrays = {
            "input_ids": np.array([e.ids for e in encoded], dtype=np.int64),
            "attention_mask": np.array(
                [e.attention_mask for e in encoded], dtype=np.int64
            ),
            "token_type_ids": np.array([e.type_ids for e in encoded], dtype=np.int64),
        }
        feeds = {k: v for k, v in arrays.items() if k in self._inputs}
        return self.session.run(None, feeds)[0], arrays["attention_mask"]


class OnnxEmbedder(_OnnxModel):
    """Same vectors as SentenceTransformer(DEFAULT_EMBEDDING_MODEL).encode()."""

    def __init__(self, repo: str = DEFAULT_EMBEDDING_MODEL):
        super().__init__(repo, EMBEDDING_MAX_TOKENS)
        self.dimensions = self.session.get_outputs()[0].shape[-1]

    def encode(self, texts: list[str], batch_size: int = 32):
        import numpy as np

        out = np.empty((len(texts), self.dimensions), dtype=np.float32)
        # longest first, so each batch pads only to its own longest text
        order = sorted(range(len(texts)), key=lambda i: -len(texts[i]))
        for start in range(0, len(order), batch_size):
            idx = order[start : start + batch_size]
            hidden, mask = self._run([texts[i] for i in idx])
            weights = mask[..., None].astype(hidden.dtype)
            # mean pooling over real tokens, as in the model's 1_Pooling config
            out[idx] = (hidden * weights).sum(1) / np.clip(weights.sum(1), 1e-9, None)
        return out


class OnnxCrossEncoder(_OnnxModel):
    """Same scores as CrossEncoder(RERANKER_MODEL).predict(): raw relevance logits."""

    def __init__(self, repo: str = RERANKER_MODEL):
        super().__init__(repo, RERANKER_MAX_TOKENS)

    def predict(self, pairs: list[tuple[str, str]]):
        return self._run(pairs)[0][:, 0]
