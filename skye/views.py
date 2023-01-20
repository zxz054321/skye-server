import json
from http import HTTPStatus

import openai
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_safe, require_POST

from .gpt import GPT
from .models import Profile, RedeemCode, Gift, Completion


@ensure_csrf_cookie
def csrf(request):
    return HttpResponse(status=HTTPStatus.OK)


@require_POST
def register(request):
    data = json.loads(request.body)

    # validate invitation code
    try:
        inviter_profile = Profile.objects.get(invitation_code=data["invitation_code"])
    except Profile.DoesNotExist:
        return JsonResponse(
            {"error": "illegal_invitation_code"}, status=HTTPStatus.UNPROCESSABLE_ENTITY
        )

    # try creating a new user
    try:
        user = User.objects.create_user(
            username=data["email"], email=data["email"], password=data["password"]
        )
    except IntegrityError as err:
        if "username" in str(err):
            return JsonResponse({"error": "user_exists"}, status=HTTPStatus.CONFLICT)
        raise

    # make awards
    user.profile.name = data["name"]
    user.profile.inviter = inviter_profile.user
    with transaction.atomic():
        user.save()
        Gift.objects.create(user=user, amount=settings.GIFT_AMOUNT)
        Gift.objects.create(user=user.profile.inviter, amount=settings.GIFT_AMOUNT)
    return HttpResponse(status=HTTPStatus.OK)


@require_POST
def login(request):
    data = json.loads(request.body)
    user = auth.authenticate(username=data["email"], password=data["password"])
    if user is None:
        return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
    else:
        auth.login(request, user)
        return HttpResponse(status=HTTPStatus.OK)


@csrf_exempt
def logout(request):
    auth.logout(request)
    return HttpResponse(status=HTTPStatus.OK)


@require_safe
def get_user(request):
    user = request.user
    if not user.is_authenticated:
        return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
    else:
        return JsonResponse(
            {
                "data": {
                    "name": user.profile.name,
                    "email": user.email,
                    "vip": user.profile.is_vip,
                }
            },
            status=HTTPStatus.OK,
        )


@require_POST
@login_required
def ask(request):
    user = request.user
    data = json.loads(request.body)

    # only VIP can use original GPT model
    if data["model"] == "general" and not user.profile.is_vip:
        return JsonResponse({"error": "wrong_model"}, status=HTTPStatus.BAD_REQUEST)

    # validate model
    gpt = GPT.load_model(data["model"])
    if not gpt:
        return JsonResponse({"error": "wrong_model"}, status=HTTPStatus.BAD_REQUEST)

    # check balance
    a = _account(user)
    if a["paid_balance"] + a["gifted_balance"] - a["total_usage"] < 0:
        return JsonResponse(
            {"error": "insufficient_balance"}, status=HTTPStatus.BAD_REQUEST
        )

    if "params" not in data:
        data["params"] = None
    try:
        completion = gpt.create_completion(data["prompts"], data["params"])
    except openai.error.InvalidRequestError as err:
        print(str(err))
        return JsonResponse(
            {"error": "skye_internal_error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    Completion.objects.create(
        user=user,
        model=gpt.model.codename,
        prompt=data["prompts"],
        completion=completion["completion"],
        finish_reason=completion["finish_reason"],
        prompt_usage=completion["prompt_token_usage"],
        completion_usage=completion["completion_token_usage"],
        total_usage=completion["total_token_usage"],
    )
    return JsonResponse(
        {
            "data": {
                "completion": completion["completion"] or "\n这个我不会，请换一种表述。",
                "finish_reason": completion["finish_reason"],
            }
        },
        status=HTTPStatus.OK,
    )


@require_safe
@login_required
def get_invitation_code(request):
    user = request.user
    code = user.profile.assure_invitation_code()
    user.save()
    return JsonResponse({"data": {"code": code}}, status=HTTPStatus.OK)


@require_safe
@login_required
def get_invitees(request):
    invitees = request.user.invitee_set.all()
    return JsonResponse(
        {
            "data": [
                {
                    "name": invitee.name,
                    "email": invitee.user.email,
                    "joined_at": invitee.user.date_joined,
                }
                for invitee in invitees
            ]
        },
        status=HTTPStatus.OK,
    )


@require_POST
@login_required
def redeem(request):
    data = json.loads(request.body)

    # validate the redeem code
    try:
        redeemcode = RedeemCode.objects.get(code=data["code"])
    except RedeemCode.DoesNotExist:
        return JsonResponse({"error": "wrong_code"}, status=HTTPStatus.BAD_REQUEST)
    if redeemcode.redeemer:
        return JsonResponse({"error": "code_used"}, status=HTTPStatus.BAD_REQUEST)

    # redeem and send a gift to the inviter
    user = request.user
    redeemcode.redeemer = user
    redeemcode.redeemed_at = timezone.now()
    with transaction.atomic():
        redeemcode.save()
        Gift.objects.create(
            user=user.profile.inviter, amount=int(redeemcode.amount * 0.03)
        )
    return HttpResponse(status=HTTPStatus.OK)


@require_safe
@login_required
def get_balance(request):
    a = _account(request.user)
    paid = a["paid_balance"]
    gifted = a["gifted_balance"] - a["total_usage"]
    if gifted < 0:
        # gifted balance failed to cover all usage
        paid += gifted
        gifted = 0
    return JsonResponse(
        {
            "data": {
                "paid": paid,
                "gifted": gifted,
            }
        },
        status=HTTPStatus.OK,
    )


@require_safe
@login_required
def get_redeemcode_history(request):
    history = RedeemCode.objects.filter(redeemer=request.user)
    return JsonResponse(
        {
            "data": [
                {
                    "code": redeemcode.code,
                    "amount": redeemcode.amount,
                    "redeemed_at": redeemcode.redeemed_at,
                }
                for redeemcode in history
            ]
        },
        status=HTTPStatus.OK,
    )


def _account(user):
    total_usage = user.completion_set.aggregate(Sum("total_usage"))["total_usage__sum"]
    paid_balance = user.redeemcode_set.aggregate(Sum("amount"))["amount__sum"]
    gifted_balance = user.gift_set.aggregate(Sum("amount"))["amount__sum"]
    return {
        "total_usage": total_usage or 0,
        "paid_balance": paid_balance or 0,
        "gifted_balance": gifted_balance or 0,
    }
