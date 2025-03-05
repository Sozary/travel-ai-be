import os
import json
import openai
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import random

# Load environment variables
load_dotenv()

# Get OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PORT = int(os.environ.get("PORT", 8000))


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}

def openai_stream_response(user_prompt: str, api_key: str, trip_type: str = "standard"):
    """
    Calls OpenAI API and streams the itinerary response in real-time.
    """
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing API key")


    # Define the prompt for OpenAI
    prompt = f"""
    You are an AI travel assistant. Your job is to generate a highly personalized, detailed, and structured travel itinerary based on the user's request.

    ## **User Request**
    - **User Input:** "{user_prompt}"
    - **Trip Type:** '{trip_type}'
    
    ## **Response Rules**
    - **Respect the user's request**: If they specify the **number of days**, generate that exact number of days.
    - **Budget awareness**: If the user mentions a budget, tailor recommendations accordingly (e.g., luxury hotels, budget hostels, expensive vs. affordable restaurants).
    - **Activity Balance**:
      - If the user **does not specify** a number of activities per day, adjust based on the trip type:
        - **Relaxing trips**: Fewer activities with **longer stays** at locations.
        - **Exploration trips**: More activities, with a mix of famous landmarks and hidden gems.
        - **Adventure trips**: Activities with action-oriented experiences (e.g., hiking, diving).
        - **Cultural trips**: Museums, historical sites, immersive experiences.
      - If the user **does specify** how many activities they want per day, strictly follow that.
    - **Include Restaurants**: If the user mentions food, restaurants, or cuisine preferences, include recommended restaurants in the itinerary.

    ## **Activity Naming Rules**
    - **For specific places (landmarks, restaurants, attractions, museums, etc.)**, always include:
      - `"name"`: The **specific** name of the attraction.
      - `"location"`: The exact location in `"City, Country"` format (e.g., `"Eiffel Tower, Paris, France"`).
    - **For general explorations, city strolls, or district visits**:
      - `"name"`: A broad descriptor (e.g., `"Explore Montmartre"`, `"Stroll through Old Town"`).
      - `"location"`: The **district or city** (e.g., `"Montmartre, Paris, France"` or `"Old Town, Prague, Czech Republic"`).
    - **Example Corrections:**
      - ❌ `"Explore Avignon"` (too vague) → ✅ `"Explore Palais des Papes"` with `"location": "Palais des Papes, Avignon, France"`.
      - ❌ `"Discover Rome"` (too broad) → ✅ `"Walk through Trastevere"` with `"location": "Trastevere, Rome, Italy"`.

    ## **Itinerary Output Format**
    Your response must be a valid JSON object:

    ```json
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
            }},
            {{
              "name": "Le Petit Bouillon Pharamond",
              "location": "Paris, France",
              "duration": "1 hour",
              "transport_to_next": "Walking",
              "type": "restaurant"
            }}
          ]
        }},
        {{
          "day": 2,
          "activities": [
            {{
              "name": "Eiffel Tower",
              "location": "Eiffel Tower, Paris, France",
              "duration": "1 hour 30 minutes",
              "transport_to_next": "Taxi"
            }},
            {{
              "name": "Seine River Cruise",
              "location": "Seine River, Paris, France",
              "duration": "2 hours",
              "transport_to_next": "Walking"
            }},
            {{
              "name": "Le Procope",
              "location": "Paris, France",
              "duration": "1 hour",
              "transport_to_next": "Walking",
              "type": "restaurant"
            }}
          ]
        }}
      ],
      "total_budget": "2500 euros",
      "transportation": ["Metro", "Walking", "Taxi"],
      "accommodation": "Boutique hotel"
    }}
    ```

    ## **Additional Itinerary Guidelines**
    - **Use diverse transportation modes**: Walking, metro, taxi, bicycle, ferry, train, etc.
    - **Provide variety**: Do not only include famous landmarks—add hidden gems, scenic spots, and unique local experiences.
    - **Time-aware recommendations**: Ensure that travel time between locations is reasonable.
    - **Include food stops & local experiences**:
      - If the user requests food or restaurants, add well-rated local restaurants.
      - If the user doesn’t specify, assume at least **one meal per day at a recommended restaurant**.
    - **Adapt to seasons**: If the user mentions travel dates, consider **weather conditions** and recommend season-appropriate activities.
    - **Evening activities**: Suggest nightlife, bars, or cultural evening events if relevant.
    - If this response does not reach the number of days requested, **continue where it left off**.
    - Ensure the JSON format remains valid.


    Ensure the response is in **valid JSON format**.
    """

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

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
def get_itinerary(destination: str, api_key: str = Query(...), trip_type: str = "standard"):
    """
    Streams the AI-generated travel itinerary as it's being generated.
    """
    return StreamingResponse(openai_stream_response(destination, api_key, trip_type), media_type="text/event-stream")


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
        {
          "name": "Explore Avignon",
          "location": "Palais des Papes, Avignon, France",
          "duration": "2 hours",
          "transport_to_next": "Walking"
        },
        {
          "name": "Pont Saint-Bénézet",
          "location": "Pont Saint-Bénézet, Avignon, France",
          "duration": "1 hour",
          "transport_to_next": "Walking"
        },
        {
          "name": "La Fourchette",
          "location": "Avignon, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 2,
      "activities": [
        {
          "name": "Drive to Lyon",
          "location": "Lyon, France",
          "duration": "3 hours",
          "transport_to_next": "Van"
        },
        {
          "name": "Parc de la Tête d'Or",
          "location": "Lyon, France",
          "duration": "2 hours",
          "transport_to_next": "Walking"
        },
        {
          "name": "Bouchon Des Filles",
          "location": "Lyon, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 3,
      "activities": [
        {
          "name": "Drive to Dijon",
          "location": "Dijon, France",
          "duration": "2 hours",
          "transport_to_next": "Van"
        },
        {
          "name": "Palace of the Dukes",
          "location": "Dijon, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking"
        },
        {
          "name": "Le Bistrot des Halles",
          "location": "Dijon, France",
          "duration": "1 hour",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 4,
      "activities": [
        {
          "name": "Drive to Reims",
          "location": "Reims, France",
          "duration": "3 hours 30 minutes",
          "transport_to_next": "Van"
        },
        {
          "name": "Visit Notre-Dame de Reims",
          "location": "Reims, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking"
        },
        {
          "name": "Le Jardin Les Crayères",
          "location": "Reims, France",
          "duration": "1 hour",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 5,
      "activities": [
        {
          "name": "Drive to Paris",
          "location": "Paris, France",
          "duration": "2 hours",
          "transport_to_next": "Van"
        },
        {
          "name": "Louvre Museum",
          "location": "Louvre Museum, Paris, France",
          "duration": "3 hours",
          "transport_to_next": "Metro"
        },
        {
          "name": "Le Petit Bouillon Pharamond",
          "location": "Paris, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 6,
      "activities": [
        {
          "name": "Montmartre",
          "location": "Montmartre, Paris, France",
          "duration": "2 hours",
          "transport_to_next": "Metro"
        },
        {
          "name": "Sacré-Cœur",
          "location": "Sacré-Cœur, Paris, France",
          "duration": "1 hour",
          "transport_to_next": "Walking"
        },
        {
          "name": "Le Refuge des Fondus",
          "location": "Paris, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
      ]
    },
    {
      "day": 7,
      "activities": [
        {
          "name": "Drive to Brittany",
          "location": "Rennes, Brittany, France",
          "duration": "4 hours",
          "transport_to_next": "Van"
        },
        {
          "name": "Explore Rennes",
          "location": "Rennes, Brittany, France",
          "duration": "2 hours",
          "transport_to_next": "Walking"
        },
        {
          "name": "Creperie Saint Georges",
          "location": "Rennes, Brittany, France",
          "duration": "1 hour 30 minutes",
          "transport_to_next": "Walking",
          "type": "restaurant"
        }
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
