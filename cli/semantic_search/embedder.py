"""
Embedding abstraction for semantic search.

We start with sentence-transformers (BAAI/bge-small-en-v1.5) on CPU. The
`Embedder` interface is intentionally tiny so a future ONNXRuntime-backed
implementation can be dropped in without touching the service or the API layer.

BGE models expect a query prefix for retrieval and normalized vectors; both are
handled here so callers only deal in plain text.
"""

import logging

logger = logging.getLogger(__name__)

# BGE retrieval instruction prepended to *queries* (not to documents).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Token the model was trained with for subword handling.
MODEL_MAX_SEQ = 512


class Embedder:
    """Minimal embedder contract used by the service."""

    def embed(self, texts):
        """Return a list of float vectors (one per input text)."""
        raise NotImplementedError

    def embed_query(self, text):
        """Embed a single search query (with the BGE retrieval prefix)."""
        return self.embed([QUERY_PREFIX + text])[0]


class SentenceTransformerEmbedder(Embedder):
    """sentence-transformers backed embedder (CPU, normalized vectors)."""

    def __init__(self, model_name):
        # Imported lazily so the package can be imported without the heavy dep.
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s ...", model_name)
        self._model = SentenceTransformer(model_name)
        self._model.max_seq_length = MODEL_MAX_SEQ
        # CPU-only, single thread keeps a weak box responsive.
        import torch

        torch.set_num_threads(1)
        logger.info("Embedding model %s loaded.", model_name)

    def embed(self, texts):
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=16,
        )
        return [v.tolist() for v in vectors]
