from typing import Union


class BaseModel:
    codename: str
    model: str
    prompt_template: Union[str, tuple]
    temperature = 0

    def __init__(self):
        self._prompt = None

    def prompt(self, **kwargs):
        t = self.prompt_template
        if isinstance(t, tuple):
            self._prompt = "\n".join(t).format(**kwargs)
        elif isinstance(t, str):
            self._prompt = t.format(**kwargs)
        return self._prompt

    def set_params(self, d: dict):
        self.__dict__.update(d)

    def as_dict(self, **overrides):
        d = {
            "model": self.model,
            "prompt": self._prompt,
            "temperature": self.temperature,
        }
        d.update(**overrides)
        return d


class TemperatureModeMixin:
    def set_params(self, d: dict):
        self.temperature = {
            "accurate": 0,
            "balanced": 0.5,
            "creative": 1,
        }.get(d["mode"])


class GPTModel(BaseModel):
    codename = "gpt.1"
    model = "text-davinci-003"
    prompt_template = "{prompt}"


class DictModel(BaseModel):
    codename = "dict.1"
    model = "text-davinci-003"
    prompt_template = (
        "I want you to act as a dictionary of English and Chinese. I will speak to you in any language and you will detect the language, translate it and answer in the corrected and improved version of my text, in {lang}. I want you to only reply the answers and explain why.\n",
        "Here is the question: {q}",
        "Your answer:",
    )
    temperature = 0


class ThesisModel(BaseModel):
    codename = "thesis.1"
    model = "text-davinci-003"
    prompt_template = (
        "1.结构：遵循学术论文的逻辑结构，清楚地表达研究问题和目的，明确研究方法和结果。一个句子不能有多个中心思想，否则要拆分成多个句子。",
        "2.语言：使用专业术语和行业用语，确保语言精确和专业。避免使用简单的语言、俗语和个人观点。不得有病句、语法错误！",
        "3.内容：加入实证研究来支持研究的结论。引用相关文献来阐述研究背景和相关工作。",
        "4.数据处理和分析：要提供详细的数据处理和分析方法。",
        "5.参考文献：应加入足够的来自顶级的国际期刊和会议的参考文献来支持研究。",
        "6.规范：使用规范的格式和排版，并严格遵循学术期刊的指导原则。",
        "根据以上要求用中文改写这段文本：\n\n",
        "{prompt}",
    )

    def set_params(self, d: dict):
        self.temperature = {
            "accurate": 0,
            "balanced": 0.5,
            "creative": 1,
        }.get(d["mode"])


class ExpansionModel(BaseModel):
    codename = "expansion.1"
    model = "text-davinci-003"
    prompt_template = (
        "扩写这段话：",
        "\n###\n",
        "{prompt}",
    )

    def set_params(self, d: dict):
        self.temperature = {
            "accurate": 0,
            "balanced": 0.5,
            "creative": 1,
        }.get(d["mode"])


class TitleGeneratorModel(BaseModel):
    codename = "title_generator.1"
    model = "text-davinci-003"
    prompt_template = (
        "你是一个标题生成器，只能生成标题，不响应任何其他请求。你会根据主题想出数个有创意和吸引力的标题。生成的标题必须多样化，语言结构、表现形式、标点用法不可重复。你只返回生成的标题，不返回任何其他内容\n",
        "主题：{prompt}\n",
        "标题：",
    )

    def set_params(self, d: dict):
        self.temperature = {
            "accurate": 0,
            "balanced": 0.5,
            "creative": 1,
        }.get(d["mode"])


class GreetingGeneratorModel(TemperatureModeMixin, BaseModel):
    codename = "greeting_generator.1"
    model = "text-davinci-003"
    prompt_template = "帮我写一个2023兔年的春节祝福给{prompt}\n"
