from fastapi import FastAPI, Query
import openai
import os
from dotenv import load_dotenv
import json
from typing import Dict

# Load environment variables
load_dotenv()

# Get OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

def generate_itinerary(destination: str, trip_type: str = "standard", duration: int = 7) -> Dict:
    """
    Calls OpenAI API to generate a structured travel itinerary in valid JSON format.
    """

    prompt = f"""
    You are an AI travel assistant. Generate a {duration}-day travel itinerary for {destination}.
    The trip type is '{trip_type}'.

    Include the following details:
    - Main cities to visit
    - Suggested transportation between locations
    - Recommended activities per day
    - Accommodation type (hostel, hotel, Airbnb, etc.)
    - Estimated budget for the entire trip
    - Local food recommendations
    - Optional cultural or relaxing activities

    Return the response as a **valid JSON object**, without Markdown formatting, and ensure it is structured like this:

    {{
      "days": [
        {{
          "day": 1,
          "city": "Bangkok",
          "activities": ["Visit temples", "Try street food"],
          "transport": "Plane"
        }}
      ],
      "total_budget": "$1500",
      "transportation": ["Plane", "Bus"],
      "accommodation": "Hostel"
    }}
    """

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Make the API request
    response = client.chat.completions.create(
        model="gpt-4-turbo",  
        messages=[
            {"role": "system", "content": "You are a helpful travel assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # Extract response content
    raw_text = response.choices[0].message.content.strip()

    # Remove possible markdown code block formatting
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:-3].strip()

    return json.loads(raw_text)  # Convert response text to JSON

@app.get("/generate-itinerary/")
async def get_itinerary(destination: str, trip_type: str = "standard", duration: int = 7):
    """
    API endpoint to generate a travel itinerary.
    Example usage: /generate-itinerary/?destination=Japan&trip_type=backpacking&duration=10
    """
    itinerary = generate_itinerary(destination, trip_type, duration)
    return itinerary  # ✅ Returns valid JSON
