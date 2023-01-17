from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Profile, RedeemCode


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    max_num = 1
    min_num = 1
    readonly_fields = "inviter", "invitation_code"


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        # (_("Profile"), ProfileInline()),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
    inlines = (ProfileInline,)
    list_display = ("name", "email", "is_staff")

    @admin.display(ordering="profile__name")
    def name(self, obj):
        return obj.profile.name


class ProfileAdmin(admin.ModelAdmin):
    fields = ("name", "is_vip")
    actions = None

    def has_add_permission(self, request):
        return None


class RedeemCodeAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("amount",)}),
        (
            _("Redeem"),
            {
                "fields": (
                    "redeemer",
                    "redeemed_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("code",)
    list_display = ("code", "amount", "created_at", "redeemed_at")
    list_filter = ("amount",)
    search_fields = ("code",)


admin.site.site_header = "SKYE Administration"
admin.site.site_title = "SKYE Site Admin"
admin.site.site_url = None
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(RedeemCode, RedeemCodeAdmin)
