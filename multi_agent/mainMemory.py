class MainMemory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MainMemory, cls).__new__(cls)
            cls._instance.jwt = None
        return cls._instance

    def set_token(self, jwt: str):
        self.jwt = jwt

    def get_token(self) -> str:
        return self.jwt

# global instance
mainMemory = MainMemory()
