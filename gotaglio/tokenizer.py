from .lazy_imports import tiktoken


class Tokenizer:
    """
    Tokenizer class for encoding text into token IDs using the tiktoken library.

    This class lazily loads the tokenizer to avoid unnecessary overhead in scenarios
    where tokenization is not required. The tokenizer uses the "cl100k_base" encoding.

    Methods
    -------
    encode(text: str) -> list[int]
      Encodes the input text into a list of token IDs.

    """
    def __init__(self):
        self._tokenizer = None

    def encode(self, text: str) -> list[int]:
        # Lazily load the tokenizer here so that we don't slow down
        # other scenarios that don't need it.
        if self._tokenizer is None:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        return self._tokenizer.encode(text)


tokenizer = Tokenizer()
