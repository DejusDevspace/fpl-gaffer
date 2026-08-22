import unittest
from unittest.mock import AsyncMock, patch

from fpl_gaffer.modules.fpl.fpl_api import FPLOfficialAPIClient


class BootstrapCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_cache_short_circuits_second_call(self):
        """Calling get_bootstrap_data() twice should hit the network only once -
        the second call should be served from the TTL cache."""
        # Clear any prior cache state from other tests
        import fpl_gaffer.modules.fpl.fpl_api as api_mod

        api_mod._bootstrap_cache.clear()

        mock_data = {"events": [], "elements": [], "teams": []}
        client = FPLOfficialAPIClient()

        with patch.object(client, "_get", new_callable=AsyncMock, return_value=mock_data) as mock_get:
            result1 = await client.get_bootstrap_data()
            result2 = await client.get_bootstrap_data()

        # _get should only have been called once — the second call was served from cache
        mock_get.assert_called_once_with("/bootstrap-static/")
        self.assertEqual(result1, mock_data)
        self.assertEqual(result2, mock_data)

        # Cleanup
        api_mod._bootstrap_cache.clear()


class SharedClientReuseTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_instances_share_same_http_client(self):
        """Two FPLOfficialAPIClient() instances created without an explicit session
        should resolve to the same underlying httpx.AsyncClient via get_shared_http_client()."""
        import fpl_gaffer.modules.fpl.fpl_api as api_mod

        # Reset shared client to force fresh creation
        old_client = api_mod._shared_client
        api_mod._shared_client = None

        try:
            client_a = FPLOfficialAPIClient()
            client_b = FPLOfficialAPIClient()

            session_a = await client_a._get_session()
            session_b = await client_b._get_session()

            self.assertIs(session_a, session_b, "Both instances should share the same httpx.AsyncClient")
        finally:
            # Cleanup: close the client we created and restore previous state
            if api_mod._shared_client is not None:
                await api_mod._shared_client.aclose()
            api_mod._shared_client = old_client


if __name__ == "__main__":
    unittest.main()
