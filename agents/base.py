class Agent:
    """Agent基类 — 一个有明确输入/输出的可调度单元。
    子类通过类属性定义 name, description, input_keys, output_keys。
    """

    name: str = ""
    description: str = ""
    input_keys: list[str] = []
    output_keys: list[str] = []

    def __init__(self, **kwargs):
        # 允许实例化时覆盖类属性
        for key, val in kwargs.items():
            if hasattr(self.__class__, key):
                setattr(self, key, val)

    @property
    def _name(self) -> str:
        return type(self).name or self.__class__.__name__

    def validate_input(self, context: dict) -> bool:
        return all(k in context for k in self.input_keys)

    def execute(self, context: dict) -> dict:
        raise NotImplementedError
