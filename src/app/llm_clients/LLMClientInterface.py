class LLMClientInterface:
    def generate(self, prompt: str, msg_id: int) -> str:
        pass

    def get_llm_info(self) -> dict:
        pass
