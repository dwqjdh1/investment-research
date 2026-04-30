class Skill:
    """技能基类 — 可复用的能力单元，支持管道组合"""

    name: str = ""
    description: str = ""
    input_schema: dict = {}
    output_schema: dict = {}

    def execute(self, **kwargs):
        raise NotImplementedError

    def __or__(self, next_skill: "Skill") -> "SkillPipeline":
        return SkillPipeline([self, next_skill])

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


class SkillPipeline:
    """技能管道 — 串联多个技能依次执行"""

    def __init__(self, skills: list[Skill]):
        self.skills = skills

    def execute(self, **kwargs):
        result = kwargs
        for skill in self.skills:
            result = skill.execute(**result)
            if not isinstance(result, dict):
                result = {"_result": result}
        return result

    def __or__(self, next_skill: Skill) -> "SkillPipeline":
        return SkillPipeline(self.skills + [next_skill])
