import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from fpl_gaffer.integrations.api.app.routes.onboarding import (
    register_user,
    request_phone_verification,
)
from fpl_gaffer.integrations.api.app.utils.phone import normalize_phone_number
from fpl_gaffer.integrations.api.app.utils.schemas import (
    OnboardingRequest,
    PhoneVerificationRequest,
)


class _FakeFPLApi:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class OnboardingApiTests(unittest.IsolatedAsyncioTestCase):
    def test_phone_normalization_handles_twilio_and_spacing(self):
        self.assertEqual(
            normalize_phone_number("whatsapp:+234 701-234-5678"),
            "+2347012345678",
        )

    async def test_register_user_links_valid_fpl_team(self):
        profile_manager = Mock()
        profile_manager.extract_user_data = AsyncMock(
            return_value={
                "name": "Deju FC",
                "player_first_name": "Deju",
                "player_last_name": "Adejo",
            }
        )

        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.FPLOfficialAPIClient",
                return_value=_FakeFPLApi(),
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.FPLUserProfileManager",
                return_value=profile_manager,
            ) as manager_cls,
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.whatsapp_service.check_phone_verification",
                new_callable=AsyncMock,
                return_value=True,
            ) as check_phone,
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.database_service.upsert_user_by_phone",
                new_callable=AsyncMock,
                return_value={"id": "user-1", "phone": "+2347012345678", "full_name": "Deju"},
            ) as upsert_user,
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.fpl_service.link_fpl_team",
                new_callable=AsyncMock,
                return_value="team-1",
            ) as link_fpl_team,
        ):
            response = await register_user(
                OnboardingRequest(
                    name=" Deju ",
                    phone="whatsapp:+234 701-234-5678",
                    fpl_id=12345,
                    verification_code="123456",
                )
            )

        manager_cls.assert_called_once()
        check_phone.assert_awaited_once_with(phone="+2347012345678", code="123456")
        profile_manager.extract_user_data.assert_awaited_once_with(mode="api")
        upsert_user.assert_awaited_once_with(
            full_name="Deju",
            phone="+2347012345678",
        )
        link_fpl_team.assert_awaited_once()
        self.assertEqual(response.status, "success")
        self.assertEqual(response.user_id, "user-1")
        self.assertEqual(response.phone, "+2347012345678")
        self.assertEqual(response.fpl_id, 12345)
        self.assertEqual(response.fpl_team_id, "team-1")
        self.assertEqual(response.team_name, "Deju FC")

    async def test_register_user_rejects_invalid_fpl_id(self):
        profile_manager = Mock()
        profile_manager.extract_user_data = AsyncMock(return_value={})

        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.whatsapp_service.check_phone_verification",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.FPLOfficialAPIClient",
                return_value=_FakeFPLApi(),
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.FPLUserProfileManager",
                return_value=profile_manager,
            ),
        ):
            with self.assertRaises(HTTPException) as exc:
                await register_user(
                    OnboardingRequest(
                        name="Deju",
                        phone="+2347012345678",
                        fpl_id=12345,
                        verification_code="123456",
                    )
                )

        self.assertEqual(exc.exception.status_code, 400)

    async def test_register_user_requires_phone_verification_before_linking(self):
        with (
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.whatsapp_service.check_phone_verification",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.database_service.upsert_user_by_phone",
                new_callable=AsyncMock,
            ) as upsert_user,
            patch(
                "fpl_gaffer.integrations.api.app.routes.onboarding.fpl_service.link_fpl_team",
                new_callable=AsyncMock,
            ) as link_fpl_team,
        ):
            with self.assertRaises(HTTPException) as exc:
                await register_user(
                    OnboardingRequest(
                        name="Deju",
                        phone="+2347012345678",
                        fpl_id=12345,
                        verification_code="000000",
                    )
                )

        self.assertEqual(exc.exception.status_code, 403)
        upsert_user.assert_not_awaited()
        link_fpl_team.assert_not_awaited()

    async def test_request_phone_verification_sends_code(self):
        with patch(
            "fpl_gaffer.integrations.api.app.routes.onboarding.whatsapp_service.start_phone_verification",
            new_callable=AsyncMock,
            return_value=True,
        ) as start_phone:
            response = await request_phone_verification(
                PhoneVerificationRequest(phone="whatsapp:+234 701-234-5678")
            )

        start_phone.assert_awaited_once_with("+2347012345678")
        self.assertEqual(response.status, "sent")
        self.assertEqual(response.phone, "+2347012345678")


if __name__ == "__main__":
    unittest.main()
