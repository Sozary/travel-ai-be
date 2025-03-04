import os
import json
import openai
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

# Load environment variables
load_dotenv()

# Get OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set this to your frontend's domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def openai_stream_response(user_prompt: str, trip_type: str = "standard"):
    """
    Calls OpenAI API and streams the itinerary response in real-time.
    """

    # Define the prompt for OpenAI
    prompt = f"""
    You are an AI travel assistant. Generate a travel itinerary based on the following input.

    User Input: "{user_prompt}"
    Trip type: '{trip_type}'

    Include:
    - Main cities to visit
    - Suggested transportation
    - Recommended activities per day
    - Accommodation type
    - Estimated budget
    - Local food recommendations
    - Optional cultural or relaxing activities

    **Return a valid JSON response with no Markdown formatting**:
    {{
      "days": [
        {{
          "day": 1,
          "city": "City Name",
          "activities": ["Activity 1", "Activity 2"],
          "transport": "Transport mode"
        }}
      ],
      "total_budget": "Estimated budget",
      "transportation": ["List", "of", "transport", "modes"],
      "accommodation": "Recommended accommodation type"
    }}
    """

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    try:
        # OpenAI API call with streaming enabled
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            stream=True
        )

        # Yield chunks as they arrive
        for chunk in response:
            content = chunk.choices[0].delta.content  # Extract streamed content

            if content:
                yield content  # Send it immediately to frontend

    except Exception as e:
        print(f"Error during OpenAI streaming: {e}")
        yield json.dumps({"error": "Failed to fetch itinerary from OpenAI."})


@app.get("/generate-itinerary/")
def get_itinerary(destination: str, trip_type: str = "standard"):
    """
    Streams the AI-generated travel itinerary as it's being generated.
    """
    return StreamingResponse(openai_stream_response(destination, trip_type), media_type="text/event-stream")
