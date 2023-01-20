import uuid
from hashlib import sha1
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    inviter = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name="invitee_set"
    )
    name = models.CharField(max_length=191)
    invitation_code = models.CharField(
        max_length=191,
        unique=True,
        blank=True,
        # the field must be null:
        # the code will be generated when the user attempts to retrieve it for the first time
        null=True,
    )
    is_vip = models.BooleanField(
        "VIP status",
        default=False,
        help_text="Designates whether the user can use General Model.",
    )

    def assure_invitation_code(self):
        if not self.invitation_code:
            h = str(uuid.uuid4()).replace("-", "").upper()
            code = "-".join((h[:4], h[4:8], h[8:12], h[12:16]))
            self.invitation_code = code
        return self.invitation_code

    def __str__(self):
        return self.user.email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, inviter=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


def generate_redeem_code():
    h = sha1()
    h.update(str(uuid4()).encode("utf-8"))
    return h.hexdigest().upper()


class RedeemCodeManager(models.Manager):
    def generate_new_code(self, amount):
        return self.create(code=generate_redeem_code(), amount=amount)


class RedeemCode(models.Model):
    redeemer = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=True,
        # the field must be null:
        # the code is newborn and hasn't been redeemed yet
        null=True,
    )
    code = models.CharField(max_length=40, unique=True, default=generate_redeem_code)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    redeemed_at = models.DateTimeField(
        blank=True,
        # the field must be null:
        # the code is newborn and hasn't been redeemed yet
        null=True,
    )

    objects = RedeemCodeManager()

    def __str__(self):
        return self.code


class Gift(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    amount = models.PositiveIntegerField()
    gifted_at = models.DateTimeField(auto_now_add=True)


class Completion(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    model = models.CharField(max_length=20)
    prompt = models.JSONField()
    completion = models.TextField()
    finish_reason = models.CharField(max_length=50)
    prompt_usage = models.PositiveIntegerField()
    completion_usage = models.PositiveIntegerField()
    total_usage = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
