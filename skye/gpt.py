import openai
from django.conf import settings

from .gpt_models import v1

KEYWORD_BLACKLIST = ("gpt", "openai", "chat", "microsoft", "微软", "小冰", "小度", "天猫精灵")


def test_client():
    class FakeChoice:
        text = "Hi!"
        finish_reason = "stop"

    class FakeUsage:
        prompt_tokens = 10
        completion_tokens = 90
        total_tokens = 100

    class FakeResponse:
        choices = [FakeChoice()]
        usage = FakeUsage()

    return lambda m: FakeResponse()


def openai_client():
    openai.api_key = settings.OPENAI_KEY

    def decoy():
        client = test_client()
        fake = client({})
        fake.choices[0].text = "抱歉，我不太懂你的意思。"
        fake.choices[0].finish_reason = "STOP"
        fake.usage.prompt_tokens = 0
        fake.usage.completion_tokens = 0
        fake.usage.total_tokens = 0
        return fake

    def client(params: dict):
        for kw in KEYWORD_BLACKLIST:
            if kw in params["prompt"]:
                return decoy()

        data = openai.Completion.create(**params)

        # sometimes completion_tokens is missed...
        if not hasattr(data.usage, "completion_tokens"):
            data.usage.completion_tokens = 0

        for kw in KEYWORD_BLACKLIST:
            if kw in data.choices[0].text:
                return decoy()

        return data

    return client


def calculate_tokens(s):
    return len(s) * 3


AVAILABLE_MODELS = {
    "general": v1.GPTModel,
    "dict": v1.DictionaryModel,
    "grammar": v1.GrammarModel,
    "complex_sentence": v1.ComplexSentenceModel,
    "thesis_title_assistant": v1.ThesisTitleAssistantModel,
    "thesis_abstract_assistant": v1.ThesisAbstractAssistantModel,
    "thesis_outline_assistant": v1.ThesisOutlineAssistantModel,
    "thesis_statement_expansion": v1.ThesisStatementExpansionModel,
    "thesis": v1.ThesisModel,
    "expansion": v1.ExpansionModel,
    "title_generator": v1.TitleGeneratorModel,
    "greeting_generator": v1.GreetingGeneratorModel,
    "promotion_planner": v1.PromotionPlannerModel,
    "wechat_moments": v1.WeChatMomentsModel,
}


class GPT:
    TESTING = False

    def __init__(self, model: v1.BaseModel):
        self.model = model
        self.request = test_client() if self.TESTING else openai_client()

    @staticmethod
    def load_model(name):
        if name in AVAILABLE_MODELS:
            target_model = AVAILABLE_MODELS[name]()
            return GPT(target_model)
        else:
            return None

    def create_completion(self, prompts: dict, params: dict = None):
        if params:
            self.model.set_params(params)

        prompt = self.model.prompt(**prompts)
        if settings.DEBUG:
            print("*** PROMPT DEBUG START ***\n", prompt, "\n*** PROMPT DEBUG END ***")

        max_tokens = 4096 - calculate_tokens(prompt)
        data = self.model.as_dict(max_tokens=max_tokens)
        if settings.DEBUG:
            print(data)

        response = self.request(data)
        return {
            "prompt": prompt,
            "completion": response.choices[0].text,
            "finish_reason": response.choices[0].finish_reason,
            "prompt_token_usage": response.usage.prompt_tokens,
            "completion_token_usage": response.usage.completion_tokens,
            "total_token_usage": response.usage.total_tokens,
        }
