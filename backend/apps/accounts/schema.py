"""OpenAPI extensions for account authentication."""

from drf_spectacular.authentication import SessionScheme


class CsrfDeferredSessionScheme(  # type: ignore[no-untyped-call]
    SessionScheme
):
    """Describe deferred-CSRF authentication as session-cookie auth."""

    target_class = "apps.accounts.api.views._CsrfDeferredSessionAuthentication"
    name = "csrfDeferredCookieAuth"
    priority = 0
