"""
Stub for litellm_client to enable testing in worktree.
Replace with actual implementation when merging to main.
"""
import logging

logger = logging.getLogger(__name__)


def get_client():
    """
    Stub get_client function.

    Returns a mock client that can be used for testing.
    In production, this would return the actual LiteLLM client.

    Returns:
        StubClient: A mock client for testing purposes
    """
    logger.warning("Using stub litellm_client - LLM features disabled")

    class StubClient:
        """Stub client that provides basic LLM interface without actual calls."""

        def __init__(self):
            self.logger = logging.getLogger("StubClient")

        def complete(self, *args, **kwargs):
            """
            Stub completion method.

            This simulates an LLM completion but returns a static response.
            In production, this would make actual API calls to the LLM.

            Returns:
                dict: Response in LiteLLM format with stub content
            """
            self.logger.warning("LLM completion called but disabled in stub mode")
            return {
                "choices": [{
                    "message": {
                        "content": "LLM enhancement disabled (stub mode)"
                    }
                }]
            }

        def chat_completion(self, *args, **kwargs):
            """
            Stub chat completion method.

            Alias for complete() method for compatibility.

            Returns:
                dict: Response in LiteLLM format with stub content
            """
            return self.complete(*args, **kwargs)

    return StubClient()
