from supabase import create_client, Client
from fpl_gaffer.settings import settings
from fpl_gaffer.integrations.api.app.utils.logger import logger
from typing import Optional, Dict, Any
import httpx
from jose import jwt, jwk
from jose.exceptions import JWTError


class SupabaseClient:
    """
    Supabase client for database operations and JWT verification.
    Uses asymmetric JWT verification with JWKS endpoint.
    """

    def __init__(self):
        self.SUPABASE_URL = settings.SUPABASE_URL
        self.SUPABASE_SERVICE_ROLE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY

        self.client: Client = create_client(
            self.SUPABASE_URL,
            self.SUPABASE_SERVICE_ROLE_KEY
        )

        self._jwks_cache: Optional[Dict[str, Any]] = None
        self.http_client = httpx.AsyncClient()

    async def get_jwks(self) -> Dict[str, Any]:
        """
        Fetch JWKS from Supabase endpoint with caching.
        JWKS are cached for 10 minutes as per Supabase Edge cache.
        """
        if self._jwks_cache is None:
            try:
                response = await self.http_client.get(f"{self.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
                response.raise_for_status()

                self._jwks_cache = response.json()
                logger.info("JWKS fetched and cached successfully")

            except Exception as e:
                logger.error(f"Failed to fetch JWKS: {str(e)}")
                raise

        return self._jwks_cache

    def get_signing_key(self, kid: str, jwks_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the signing key matching the kid from JWKS."""
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                return key

        raise ValueError(f"Unable to find signing key with kid: {kid}")

    async def verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token using asymmetric JWKS verification.
        Returns decoded token claims if valid, None otherwise.
        """
        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                logger.warning("JWT missing kid in header")
                return None

            # Get JWKS
            jwks_data = await self.get_jwks()

            # Find the signing key
            signing_key_data = self.get_signing_key(kid, jwks_data)

            # Convert JWK to PEM format for verification
            public_key = jwk.construct(signing_key_data)

            # Verify and decode the JWT
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256", "ES256", "EdDSA"],  # Support multiple asymmetric algorithms
                audience="authenticated",  # Supabase default audience
                options={"verify_aud": True, "verify_exp": True}
            )

            logger.info(f"JWT verified successfully for user {decoded.get('sub')}")
            return decoded

        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error during JWT verification: {str(e)}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from Supabase auth.users table."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None

    async def create_user(self, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[str]:
        """Create user in database."""
        try:
            data = {}
            if email:
                data["email"] = email

            if phone:
                data["phone"] = phone

            response = self.client.table("users").insert(data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]["id"]

            return None
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None

    async def refresh_jwks_cache(self):
        """Force refresh of JWKS cache."""
        self._jwks_cache = None
        await self.get_jwks()


supabase_client = SupabaseClient()
