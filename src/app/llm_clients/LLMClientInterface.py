class LLMClientInterface:
    def generate(self, prompt: str, msg_id: int) -> dict:
        pass

    def get_llm_info(self) -> dict:
        pass
