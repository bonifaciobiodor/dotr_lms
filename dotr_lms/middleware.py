from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """
    Adds a Content-Security-Policy header to every response using the
    CONTENT_SECURITY_POLICY setting defined in settings.py.
    Uses Report-Only mode when DEBUG=True so violations are logged to the
    browser console without blocking anything during development.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._policy = self._build_policy()
        self._header = (
            'Content-Security-Policy-Report-Only' if settings.DEBUG
            else 'Content-Security-Policy'
        )

    def __call__(self, request):
        response = self.get_response(request)
        if self._policy:
            response[self._header] = self._policy
        return response

    @staticmethod
    def _build_policy():
        csp_config = getattr(settings, 'CONTENT_SECURITY_POLICY', {})
        directives = csp_config.get('DIRECTIVES', {})
        parts = []
        for directive, sources in directives.items():
            if sources:
                parts.append(f"{directive} {' '.join(sources)}")
        return '; '.join(parts)
