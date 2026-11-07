import hashlib
import math
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    name: str
    dimension: int

    @abstractmethod
    def embed(self, texts):
        raise NotImplementedError


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline lexical embeddings for synthetic development data."""

    name = "local_hashing_v1"
    dimension = 384

    def embed(self, texts):
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text):
        vector = [0.0] * self.dimension
        for token in TOKEN_RE.findall(text.casefold()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimension
            vector[index] += -1.0 if value & 1 else 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude:
            vector = [value / magnitude for value in vector]
        return vector


def get_embedding_provider():
    provider_name = settings.KNOWLEDGE_EMBEDDING_PROVIDER
    if provider_name == LocalHashingEmbeddingProvider.name:
        return LocalHashingEmbeddingProvider()
    raise ImproperlyConfigured(f"Unknown knowledge embedding provider: {provider_name}")
