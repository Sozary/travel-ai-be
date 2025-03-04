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

# Fake Itinerary Data (to simulate OpenAI streaming response)
FAKE_ITINERARY = {
    "days": [
        {"day": 1, "city": "Paris", "activities": ["Visit the Louvre Museum", "Stroll through the Tuileries Garden"], "transport": "Metro"},
        {"day": 2, "city": "Paris", "activities": ["Explore Montmartre and visit the Sacré-Cœur", "Dinner cruise on the Seine River"], "transport": "Walking and funicular"},
        {"day": 3, "city": "Paris", "activities": ["Visit Notre Dame Cathedral", "Explore the Latin Quarter"], "transport": "Metro"},
        {"day": 4, "city": "Paris", "activities": ["Day trip to Versailles", "Visit the Palace and Gardens of Versailles"], "transport": "RER train"},
        {"day": 5, "city": "Paris", "activities": ["Visit the Eiffel Tower", "Picnic at Champ de Mars"], "transport": "Walking"}
    ],
    "total_budget": "2500 euros",
    "transportation": ["Metro", "Walking", "Funicular", "RER train"],
    "accommodation": "Boutique hotel"
}

async def generate_fake_itinerary_stream(destination: str, trip_type: str) -> AsyncGenerator[str, None]:
    """
    Streams the fake itinerary day by day as if it were a real-time response.
    """
    yield '{"days": [\n'  # Start of JSON array

    for i, day in enumerate(FAKE_ITINERARY["days"]):
        await asyncio.sleep(1)  # Simulate delay in response
        chunk = json.dumps(day, ensure_ascii=False)
        if i < len(FAKE_ITINERARY["days"]) - 1:
            yield chunk + ",\n"  # Comma between objects
        else:
            yield chunk + "\n"  # No comma for last object

    # Stream the remaining details
    await asyncio.sleep(1)
    yield f'], "total_budget": "{FAKE_ITINERARY["total_budget"]}",\n'
    await asyncio.sleep(1)
    yield f'"transportation": {json.dumps(FAKE_ITINERARY["transportation"])},\n'
    await asyncio.sleep(1)
    yield f'"accommodation": "{FAKE_ITINERARY["accommodation"]}"}}\n'  # End of JSON

@app.get("/generate-itinerary-fake/")
async def get_itinerary(destination: str, trip_type: str = "standard"):
    """
    Streams the fake AI-generated travel itinerary **as it's being generated** for real-time frontend updates.
    """
    return StreamingResponse(generate_fake_itinerary_stream(destination, trip_type), media_type="text/event-stream")
