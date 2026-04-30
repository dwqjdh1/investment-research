from skills.base import Skill


class SkillRegistry:
    """技能注册中心 — 全局单例，按名称查找和调用技能"""

    _instance: "SkillRegistry | None" = None
    _skills: dict[str, Skill] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_all(self) -> list[dict]:
        return [s.to_dict() for s in self._skills.values()]

    def execute(self, name: str, **kwargs):
        skill = self.get(name)
        if skill is None:
            raise KeyError(f"技能 '{name}' 未注册")
        return skill.execute(**kwargs)

    def register_many(self, skills: list[Skill]) -> None:
        for skill in skills:
            self.register(skill)


registry = SkillRegistry()
