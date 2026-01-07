class SecureCookiesOnlyOnHTTPSMiddleware:
    """
    If request is HTTPS, ensure cookies are marked Secure.
    If request is HTTP (e.g. .onion), do NOT force Secure cookies.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # request.is_secure() respects SECURE_PROXY_SSL_HEADER
        if request.is_secure():
            # Patch Set-Cookie headers to include Secure
            cookies = response.cookies
            for key in cookies:
                cookies[key]["secure"] = True

        return response
