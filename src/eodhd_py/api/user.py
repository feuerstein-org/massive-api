"""User API endpoint."""

from typing import Any

from eodhd_py.base import BaseEodhdApi


class UserApi(BaseEodhdApi):
    """
    UserApi endpoint class.

    Provides access to EODHD's User API endpoint, which returns information
    about the user's subscription, API usage limits, and current usage statistics.
    """

    async def get_user_info(self) -> dict[str, Any]:
        """
        Get user subscription and API usage information.

        Note: the apiRequests and remaining_daily_limit fields may not be up-to-date
        until after making a new request. The apiRequestsDate indicates the last update date.

        If you made 0 requests today, apiRequests will reflect the last valid value (e.g. from 2 days ago).

        Returns:
            JSON response as a dictionary containing:
            - name: User's name
            - email: User's email
            - subscriptionType: Type of subscription
            - paymentMethod: Payment method string or "Not Available"
            - apiRequests: Number of API requests made
            - apiRequestsDate: Date for the `apiRequests` counter (YYYY-MM-DD)
            - dailyRateLimit: Daily rate limit (integer)
            - extraLimit: Any extra limit applied (integer)
            - inviteToken: Invite token or null
            - inviteTokenClicked: Number of times invite token was clicked
            - subscriptionMode: Subscription mode (e.g., "demo", "free")
            - canManageOrganizations: Boolean indicating organization management rights

        Raises:
            aiohttp.ClientError: If the HTTP request fails

        """
        return await self._make_request("user", df_output=False)
