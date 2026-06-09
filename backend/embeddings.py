"""
embeddings.py — OpenAI Embeddings Manager

Wraps OpenAI's text-embedding-ada-002 model for generating vector embeddings.
Supports dynamic API key injection so each user session can use its own key.
"""

from langchain_openai import OpenAIEmbeddings


class EmbeddingsManager:
    """
    Factory for creating OpenAI embedding instances.

    Why a manager class instead of a global instance?
    - The API key can come from environment variables OR from the user's session.
    - Each request might use a different key, so we create embeddings on-demand.
    """

    # The embedding model to use — ada-002 offers the best cost/quality balance
    DEFAULT_MODEL = "text-embedding-ada-002"

    @staticmethod
    def get_embeddings(api_key: str, model: str = None) -> OpenAIEmbeddings:
        """
        Create an OpenAI embeddings instance with the given API key.

        Args:
            api_key: OpenAI API key. Required.
            model: Embedding model name. Defaults to text-embedding-ada-002.

        Returns:
            A LangChain OpenAIEmbeddings instance ready to embed text.

        Raises:
            ValueError: If no API key is provided.
        """
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set it via the OPENAI_API_KEY environment variable or in the Settings panel."
            )

        return OpenAIEmbeddings(
            model=model or EmbeddingsManager.DEFAULT_MODEL,
            openai_api_key=api_key,
        )
