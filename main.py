import os
import json
import openai
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import random

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
    You are an AI travel assistant. Generate a travel itinerary based on the following user input.

    User Input: "{user_prompt}"
    Trip type: '{trip_type}'

    ## **Output Structure:**
    - **Each day contains a list of activities with exact locations** (e.g., "Louvre Museum, Paris, France").
    - **Each activity has a visit duration**, formatted like "2 hours", "45 minutes", or "30 minutes".
    - **Transport mode is simplified** to: "Walking", "Metro", "Taxi", "Bus", "Bicycle", "Ferry", "Train".
    - **Output is in valid JSON format**.

    **Example JSON Output:**
    {{
      "days": [
        {{
          "day": 1,
          "activities": [
            {{
              "name": "Louvre Museum",
              "location": "Louvre Museum, Paris, France",
              "duration": "2 hours",
              "transport_to_next": "Metro"
            }},
            {{
              "name": "Tuileries Garden",
              "location": "Tuileries Garden, Paris, France",
              "duration": "45 minutes",
              "transport_to_next": "Walking"
            }}
          ]
        }}
      ],
      "total_budget": "2500 euros",
      "transportation": ["Metro", "Walking"],
      "accommodation": "Boutique hotel"
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

# Function to generate a random visit duration (for fake itinerary)
def random_duration():
    options = ["30 minutes", "45 minutes", "1 hour", "1.5 hours", "2 hours"]
    return random.choice(options)

# Fake Itinerary Data (to simulate OpenAI streaming response)
FAKE_ITINERARY = {
    "days": [
        {
            "day": 1,
            "activities": [
                {"name": "Luxembourg Gardens", "location": "Luxembourg Gardens, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"},
                {"name": "Sainte-Chapelle", "location": "Sainte-Chapelle, Paris, France", "duration": random_duration(), "transport_to_next": "Metro"},
                {"name": "Place Dauphine", "location": "Place Dauphine, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"}
            ]
        },
        {
            "day": 2,
            "activities": [
                {"name": "Montmartre", "location": "Montmartre, Paris, France", "duration": random_duration(), "transport_to_next": "Metro"},
                {"name": "Basilica of the Sacré-Cœur", "location": "Basilica of the Sacré-Cœur, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"},
                {"name": "Place du Tertre", "location": "Place du Tertre, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"}
            ]
        },
        {
            "day": 3,
            "activities": [
                {"name": "Rodin Museum", "location": "Rodin Museum, Paris, France", "duration": random_duration(), "transport_to_next": "Metro"},
                {"name": "Les Invalides", "location": "Les Invalides, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"},
                {"name": "Musée d'Orsay", "location": "Musée d'Orsay, Paris, France", "duration": random_duration(), "transport_to_next": "Walking"}
            ]
        }
    ],
    "total_budget": "2000 euros",
    "transportation": ["Metro", "Walking"],
    "accommodation": "Budget hotel"
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
async def get_itinerary_fake(destination: str, trip_type: str = "standard"):
    """
    Streams the fake AI-generated travel itinerary **as it's being generated** for real-time frontend updates.
    """
    return StreamingResponse(generate_fake_itinerary_stream(destination, trip_type), media_type="text/event-stream")
