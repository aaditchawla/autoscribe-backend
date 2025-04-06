import openai
import os
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_text(text, target_language):
    """Translate text using GPT-3.5"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful translator. Translate the following text to {target_language}. Maintain the same formatting including markdown and bullet points."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise Exception(f"Error translating text: {str(e)}")

if __name__ == "__main__":
    # Test the translation function
    test_text = "# Meeting Summary\n\n## Key Decisions\n- Decision 1\n- Decision 2\n\n## Action Items\n- Action 1\n- Action 2"
    translated = translate_text(test_text, "French")
    print("Original:")
    print(test_text)
    print("\nTranslated:")
    print(translated) 