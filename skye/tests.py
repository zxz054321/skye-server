from django.db.models import Sum
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from skye import gpt
from .gpt_models import v1
from .models import User, RedeemCode, Gift, Completion


def _create_superuser():
    superuser = User.objects.create_superuser(
        username="sh.skyeharris@gmail.com",
        email="sh.skyeharris@gmail.com",
        password="secret",
    )
    superuser.profile.name = "Skye Harris"
    superuser.profile.invitation_code = "XXXX-XXXX-XXXX-XXXX"
    superuser.save()
    return superuser


class GPTTestModel(v1.BaseModel):
    model = "test"
    prompt_template = "{p}"
    temperature = 0.5


class GptModelsTests(SimpleTestCase):
    def test_prompt(self):
        m = GPTTestModel()
        m.prompt_template = "A,{prompt},C"
        self.assertEqual(m.prompt(prompt="B"), "A,B,C")

        m.prompt_template = "A,{B},C,{D}"
        self.assertEqual(m.prompt(B=1, D=2), "A,1,C,2")

        m.prompt_template = "line1", "{prompt}", "line3"
        self.assertEqual(m.prompt(prompt="line2"), "line1\nline2\nline3")

    def test_as_dict(self):
        m = GPTTestModel()
        m.prompt(p="Hello SKYE")
        self.assertDictEqual(
            m.as_dict(),
            {
                "model": "test",
                "prompt": "Hello SKYE",
                "temperature": 0.5,
            },
        )
        self.assertDictEqual(
            m.as_dict(temperature=1, max_token=9),
            {
                "model": "test",
                "prompt": "Hello SKYE",
                "temperature": 1,
                "max_token": 9,
            },
        )


class GptTests(SimpleTestCase):
    def test_calculate_tokens(self):
        self.assertEqual(gpt.calculate_tokens("你好"), 6)
        self.assertEqual(gpt.calculate_tokens("Hello"), 15)
        self.assertEqual(gpt.calculate_tokens("Hi你好"), 12)

    def test_load_model(self):
        self.assertIsNone(gpt.GPT.load_model("nonexistence"))

    def test_create_completion(self):
        gpt.AVAILABLE_MODELS["test"] = GPTTestModel
        gpt.GPT.TESTING = True
        gpt_instance = gpt.GPT.load_model("test")
        completion = gpt_instance.create_completion({"p": "Hello!"})
        self.assertDictEqual(
            completion,
            {
                "prompt": "Hello!",
                "completion": "Hi!",
                "finish_reason": "stop",
                "prompt_token_usage": 10,
                "completion_token_usage": 90,
                "total_token_usage": 100,
            },
        )


class ModelTests(TestCase):
    def test_redeemcode(self):
        code = RedeemCode.objects.generate_new_code(50).code
        redeemcode = RedeemCode.objects.get(code=code)
        self.assertIsNone(redeemcode.redeemer)
        self.assertEqual(50, redeemcode.amount)
        self.assertRegexpMatches(redeemcode.code, r"[A-Z0-9]{40}")
        self.assertIsNotNone(redeemcode.created_at)
        self.assertIsNone(redeemcode.redeemed_at)


class MiddlewareTests(TestCase):
    def test_hide_admin_from_non_staff_middleware(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)

        self.client.force_login(_create_superuser())
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)


class ApiTests(TestCase):
    def setUp(self):
        self.superuser = _create_superuser()

    @override_settings(GIFT_AMOUNT=5000)
    def test_register(self):
        # test illegal invitation code
        response = self.client.post(
            "/register",
            {
                "name": "attacker",
                "email": "fake@mail.com",
                "password": "secret",
                "invitation_code": "FAKE-XXXX-XXXX-XXXX",
            },
            content_type="application/json",
        )
        self.assertEqual(422, response.status_code)
        self.assertEqual("illegal_invitation_code", response.json()["error"])

        # test legal registering
        response = self.client.post(
            "/register",
            {
                "name": "friend",
                "email": "friend@mail.com",
                "password": "secret",
                "invitation_code": "XXXX-XXXX-XXXX-XXXX",
            },
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        response = self.client.post(
            "/register",
            {
                "name": "friend2",
                "email": "friend2@mail.com",
                "password": "secret",
                "invitation_code": "XXXX-XXXX-XXXX-XXXX",
            },
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)

        def sum_gifted(e):
            return User.objects.get(email=e).gift_set.aggregate(Sum("amount"))[
                "amount__sum"
            ]

        # test gifts
        self.assertEqual(sum_gifted("sh.skyeharris@gmail.com"), 10000)
        self.assertEqual(sum_gifted("friend@mail.com"), 10000)

        # test duplicate registering
        response = self.client.post(
            "/register",
            {
                "name": "friend",
                "email": "friend@mail.com",
                "password": "secret",
                "invitation_code": "XXXX-XXXX-XXXX-XXXX",
            },
            content_type="application/json",
        )
        self.assertEqual(409, response.status_code)
        self.assertEqual("user_exists", response.json()["error"])

    def test_login(self):
        user = User.objects.create_user(
            username="normaluser@mail.com",
            email="normaluser@mail.com",
            password="truesecret",
        )
        user.profile.name = "Normal User"
        user.profile.inviter = self.superuser
        user.save()

        # test nonexistent
        response = self.client.post(
            "/login",
            {"email": "nonexistent", "password": "falsesecret"},
            content_type="application/json",
        )
        self.assertEqual(401, response.status_code)

        # test false password
        response = self.client.post(
            "/login",
            {"email": "normaluser@mail.com", "password": "falsesecret"},
            content_type="application/json",
        )
        self.assertEqual(401, response.status_code)

        # test super admin with correct credentials
        response = self.client.post(
            "/login",
            {"email": "sh.skyeharris@gmail.com", "password": "secret"},
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)

        # test normal user with correct credentials
        response = self.client.post(
            "/login",
            {"email": "normaluser@mail.com", "password": "truesecret"},
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)

    def test_logout(self):
        self._login_skye()
        response = self.client.post("/logout")
        self.assertEqual(200, response.status_code)

    def test_get_user(self):
        # anonymous should receive a 401
        response = self.client.get("/user")
        self.assertEqual(401, response.status_code)

        # authenticated user should receive his/her profile
        self._login_skye()
        response = self.client.get("/user")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "data": {
                    "name": "Skye Harris",
                    "email": "sh.skyeharris@gmail.com",
                    "vip": False,
                }
            },
            response.json(),
        )

    def test_ask(self):
        self._login_skye()

        response = self.client.post(
            "/ask",
            {"model": "wrongmodel", "prompts": "hi"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "wrong_model")

        response = self.client.post(
            "/ask",
            {"model": "general", "prompts": "hi"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "wrong_model")

        user = self._get_skye_user_model()
        user.profile.is_vip = True
        user.save()

        # REAL WORLD TEST!!
        # response = self.client.post(
        #     "/ask",
        #     {"model": "general", "prompts": {"prompt": "how are you?"}},
        #     content_type="application/json",
        # )
        # self.assertEqual(response.status_code, 200)

    def test_get_invitation_code(self):
        self._login_skye()

        response = self.client.get("/invitation-code")
        self.assertEqual(200, response.status_code)
        self.assertRegexpMatches(
            response.json()["data"]["code"], r"(\w{4})-(\w{4})-(\w{4})-(\w{4})"
        )

        self._create_friend_user()
        self.assertTrue(
            self.client.login(username="friend@mail.com", password="secret")
        )
        self.assertRegexpMatches(
            response.json()["data"]["code"], r"(\w{4})-(\w{4})-(\w{4})-(\w{4})"
        )

    def test_get_invitees(self):
        self._login_skye()

        response = self.client.get("/invitees")
        self.assertEqual(200, response.status_code)

    def test_redeem(self):
        self._login_skye()

        # redeem fake code
        response = self.client.post(
            "/redeem", {"code": "fakecode"}, content_type="application/json"
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual("wrong_code", response.json()["error"])

        # when a friend got a valid code...
        skye = self._get_skye_user_model()
        friend = self._create_friend_user()
        friend.profile.inviter = skye
        self.client.force_login(friend)
        code = "5859B1E92164423D7AF2F16A1DD77A64B1BF41EF"
        RedeemCode.objects.create(code=code, amount=50)
        # she redeemed it...
        response = self.client.post(
            "/redeem", {"code": code}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        # skye should receive a gift...
        self.assertEqual(skye.gift_set.aggregate(Sum("amount"))["amount__sum"], 1)

        # redeem used code
        response = self.client.post(
            "/redeem", {"code": code}, content_type="application/json"
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual("code_used", response.json()["error"])

    def test_get_balance(self):
        self._login_skye()

        response = self.client.get("/balance")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "data": {
                    "balance": 0,
                }
            },
            response.json(),
        )

        # redeemed 10 and gifted 5
        code = "5859B1E92164423D7AF2F16A1DD77A64B1BF41EF"
        RedeemCode.objects.create(
            redeemer=self.superuser, code=code, amount=10, redeemed_at=timezone.now()
        )
        Gift.objects.create(user=self.superuser, amount=5)
        response = self.client.get("/balance")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "data": {
                    "balance": 15,
                }
            },
        )

        Completion.objects.create(
            user=self.superuser,
            prompt="",
            completion="",
            prompt_usage=2,
            completion_usage=3,
            total_usage=5,
        )
        response = self.client.get("/balance")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "data": {
                    "balance": 10,
                }
            },
        )

        Completion.objects.create(
            user=self.superuser,
            prompt="",
            completion="",
            prompt_usage=10,
            completion_usage=10,
            total_usage=20,
        )
        response = self.client.get("/balance")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "data": {
                    "balance": -10,
                }
            },
        )

    def test_get_redeemcode_history(self):
        self._login_skye()

        response = self.client.get("/redeemcodes")
        self.assertEqual(200, response.status_code)

    def test_get_gift_list(self):
        self._login_skye()

        response = self.client.get("/gifts")
        self.assertEqual(200, response.status_code)

    def _create_friend_user(self) -> User:
        friend = User.objects.create_user(
            username="friend@mail.com", email="friend@mail.com", password="secret"
        )
        friend.profile.name = "Friend"
        friend.save()
        return friend

    def _get_skye_user_model(self):
        return User.objects.get(username="sh.skyeharris@gmail.com")

    def _login_skye(self):
        self.client.force_login(self._get_skye_user_model())
