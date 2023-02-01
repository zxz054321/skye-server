from typing import Union


class BaseModel:
    codename: str
    model: str
    prompt_template: Union[str, tuple]
    temperature = 0

    def __init__(self):
        self._prompt = None

    def prompt(self, **kwargs) -> str:
        t = self.prompt_template
        if isinstance(t, tuple):
            self._prompt = "\n".join(t).format(**kwargs)
        elif isinstance(t, str):
            self._prompt = t.format(**kwargs)
        return self._prompt

    def set_params(self, d: dict) -> None:
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


class DictionaryModel(BaseModel):
    codename = "dict.1"
    model = "text-davinci-003"
    temperature = 0

    def set_params(self, d: dict) -> None:
        if d["lang"] == "en":
            self.prompt_template = (
                "Act as a dictionary. You will answer my questions by giving a detailed explanation and various examples in English, but don't make up facts.\n",
                "Question: {q}",
                "Answer:",
            )
        elif d["lang"] == "cn":
            self.prompt_template = (
                "你是一部词典。我会用自然语言向你查词。你会回答我的问题，做出解释并给出几个用法示例，但不能编造事实。\n",
                "问题：{q}",
                "答案：",
            )


class GrammarModel(BaseModel):
    codename = "grammar.1"
    model = "text-davinci-003"
    temperature = 0

    def set_params(self, d: dict) -> None:
        if d["lang"] == "en":
            self.prompt_template = (
                "Correct sentences to standard English. Point out and explain the errors in the sentences and interpret the grammatical knowledge involved in the errors.\n",
                'Sentences:"{sentences}"',
                "Correction:",
            )
        elif d["lang"] == "cn":
            self.prompt_template = (
                "将句子纠正为标准英语。指出并解释句子中的错误，解释错误中涉及的语法知识。\n",
                "句子：“{sentences}”",
                "纠正：",
            )


class ComplexSentenceModel(BaseModel):
    codename = "complex_sentence.1"
    model = "text-davinci-003"
    temperature = 0

    def set_params(self, d: dict) -> None:
        if d["lang"] == "en":
            self.prompt_template = (
                "Act as an English teacher writing a short essay explaining long and difficult sentences in English to Chinese students, including the following.",
                "- Extract the main body of the sentence and explain the main idea",
                "- Break down the original text into simple sentences that can be understood by beginners",
                "- Explain in detail the grammar involved in the original text",
                "You will organise the short essay in natural language.\n",
                'Sentence:"{sentence}"\n',
                "Short essay:",
            )
        elif d["lang"] == "cn":
            self.prompt_template = (
                "你是一名英语老师，在写一篇短文对中国学生讲解英语长难句，包括以下内容：",
                "- 抽出句子主干并解释大意",
                "- 将原文拆解成多个初学者能理解的简单句",
                "- 详细讲解原文涉及的语法知识",
                "你会用自然的语言来组织短文，用中文作解释，并保持所引用的原文是英文。\n",
                "长难句：“{sentence}”\n",
                "短文：",
            )


class ThesisTitleAssistantModel(TemperatureModeMixin, BaseModel):
    codename = "thesis_title_assistant.1"
    model = "text-davinci-003"
    prompt_template = "这是我的论文关键词：{prompt}。帮我想几个论文题目。"


class ThesisAbstractAssistantModel(TemperatureModeMixin, BaseModel):
    codename = "thesis_abstract_assistant.1"
    model = "text-davinci-003"
    prompt_template = "这是我的论文题目：{prompt}。帮我写个简短摘要。"


class ThesisOutlineAssistantModel(TemperatureModeMixin, BaseModel):
    codename = "thesis_outline_assistant.1"
    model = "text-davinci-003"
    prompt_template = "这是我论文的{current_title_level}，{content}，帮我想下{next_title_level}怎么写。"

    def prompt(self, **kwargs) -> str:
        lv = kwargs["level"]
        if lv == "title":
            kwargs["current_title_level"] = "题目"
            kwargs["next_title_level"] = "一级标题"
        if lv == "h1":
            kwargs["current_title_level"] = "一级标题"
            kwargs["next_title_level"] = "二级标题"
        if lv == "h2":
            kwargs["current_title_level"] = "二级标题"
            kwargs["next_title_level"] = "三级标题"
        del kwargs["level"]
        return super().prompt(**kwargs)


class ThesisModel(TemperatureModeMixin, BaseModel):
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


class ExpansionModel(TemperatureModeMixin, BaseModel):
    codename = "expansion.1"
    model = "text-davinci-003"
    prompt_template = (
        "扩写这段话：",
        "\n###\n",
        "{prompt}",
    )


class TitleGeneratorModel(TemperatureModeMixin, BaseModel):
    codename = "title_generator.1"
    model = "text-davinci-003"
    prompt_template = (
        "你是一个标题生成器，只能生成标题，不响应任何其他请求。你会根据主题想出数个有创意和吸引力的标题。生成的标题必须多样化，语言结构、表现形式、标点用法不可重复。你只返回生成的标题，不返回任何其他内容\n",
        "主题：{prompt}\n",
        "标题：",
    )


class GreetingGeneratorModel(TemperatureModeMixin, BaseModel):
    codename = "greeting_generator.1"
    model = "text-davinci-003"
    prompt_template = "帮我写一个2023兔年的春节祝福给{prompt}\n"


class PromotionPlannerModel(TemperatureModeMixin, BaseModel):
    codename = "greeting_generator.1"
    model = "text-davinci-003"
    prompt_template = "想几个活动策划，主题是：{prompt}\n"


class WeChatMomentsModel(TemperatureModeMixin, BaseModel):
    codename = "greeting_generator.1"
    model = "text-davinci-003"
    prompt_template = (
        "帮我写一条微信朋友圈，不能有语病、病句。",
        "要求：{preference}",
        "主题：{theme}",
        "朋友圈：",
    )
