from django.http import HttpRequest, HttpResponseNotFound


class HideAdminFromNonStaffMiddleware:
    """Run this after django.contrib.auth.middleware.AuthenticationMiddleware"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.path.startswith("/admin") and not request.user.is_staff:
            print("NON-STAFF WAS TRYING TO ACCESS ADMIN!")
            return HttpResponseNotFound()
        else:
            return self.get_response(request)
