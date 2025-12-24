import google.generativeai as genai
import os
from typing import Optional

class LLMClient:
    """Wrapper for Google Gemini API."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.2):
        api_key = os.getenv("GEMINI_API_KEY","AIzaSyC0uFl313N3gyLmDTu4SKkLoNDLoqoGaJ8")
        if not api_key:
            # For prototype/local dev, we warn but allow init (might fail later)
            print("WARNING: GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=api_key)
        models = genai.list_models() 
    
        print("Successfully retrieved the list of models:")
        for model in models:
            print(f"Model name: {model.name}, Supported capabilities: {model.supported_generation_methods}")
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
            )
        )

    def generate(self, prompt: str) -> str:
        """Generates text from the LLM."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating content: {e}")
            return ""

    def generate_json(self, prompt: str, pydantic_model) -> Optional[object]:
        """Generates structured JSON output using Pydantic extraction (simulated or native)."""
        # For now, we'll prompt for JSON and try to parse it, 
        # or use native structured output if available/stable.
        # Adding a specific instruction for JSON
        json_prompt = f"{prompt}\n\nRespond strictly in valid JSON format matching this schema: {pydantic_model.model_json_schema()}"
        
        try:
             # Using response_mime_type="application/json" for better results
            response = self.model.generate_content(
                json_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return pydantic_model.model_validate_json(response.text)
        except Exception as e:
             print(f"Error generating JSON: {e}")
             return None
