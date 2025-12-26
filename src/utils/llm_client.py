from google import genai
from google.genai import types
import os
from typing import Optional
import json

class LLMClient:
    """Wrapper for Google Gemini API using google-genai SDK."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.2):
        self.api_key = "AIzaSyBddBdG8b3_mn0q9C9I2F-njTQbvF7-THM"
        # os.getenv("GEMINI_API_KEY", "AIzaSyAgh14_O7pQKYGlFdHN6s0BwnX1VEXuqss")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found in environment variables.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature
        
        print("Successfully retrieved the list of models:")
        try:
            # New SDK list_models returns an iterator of Model objects
            for model in self.client.models.list():
                # Filter or just print typical ones to avoid noise if too many
                if "gemini" in model.name:
                    print(f"Model name: {model.name}")
        except Exception as e:
            print(f"Error listing models: {e}")

    def generate(self, prompt: str) -> str:
        """Generates text from the LLM."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature
                )
            )
            return response.text
        except Exception as e:
            print(f"Error generating content: {e}")
            return ""

    def _sanitize_schema(self, schema: dict) -> dict:
        """
        Recursively remove keys that standard Pydantic schema generation includes 
        but Gemini API might not support or supports differently (e.g. 'title', 'additionalProperties').
        """
        if not isinstance(schema, dict):
            return schema
            
        # keys to strip
        for key in ["title", "additionalProperties", "description"]:
             # Note: description is usually fine, but title is often noise. 
             # additionalProperties is the main offender.
             if key in schema:
                 del schema[key]
        
        # Recurse
        for key, value in schema.items():
            if isinstance(value, dict):
                self._sanitize_schema(value)
            elif isinstance(value, list):
                for item in value:
                    self._sanitize_schema(item)
        
        return schema

    def generate_json(self, prompt: str, pydantic_model) -> Optional[object]:
        """Generates structured JSON output using Pydantic extraction."""
        # The new SDK supports structured output natively with 'response_schema' or 'response_mime_type'.
        # Passing pydantic model to response_schema is the most robust way.
        
        # Sanitize schema to avoid "additionalProperties" or other errors
        raw_schema = pydantic_model.model_json_schema()
        clean_schema = self._sanitize_schema(raw_schema)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    response_mime_type="application/json",
                    response_schema=clean_schema
                )
            )
            
            # If we used response_schema with pydantic, response.parsed might be available?
            # Or we just parse response.text.
            # google-genai 0.3+ typically returns a parsed object if response_schema is set?
            # Let's try response.parsed first, fallback to text.
            
            if hasattr(response, 'parsed') and response.parsed:
                # If we passed a dict schema, the SDK returns a dict/list.
                # We need to convert it back to the Pydantic model for the caller.
                if isinstance(response.parsed, (dict, list)):
                    return pydantic_model.model_validate(response.parsed)
                return response.parsed
            
            # Fallback for manual parsing
            return pydantic_model.model_validate_json(response.text)
            
        except Exception as e:
             print(f"Error generating JSON: {e}")
             try:
                 with open("debug_llm_error.txt", "w") as f:
                     f.write(str(e))
             except: pass
             return None
