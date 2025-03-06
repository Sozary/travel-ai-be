import random
import json
import asyncio
from typing import AsyncGenerator
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

def openai_stream_response(user_prompt: str, api_key: str, trip_type: str = "standard", start_day: int = 1, total_days: int = 7):
    """
    Calls OpenAI API and streams the itinerary response in real-time.
    """
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing API key")

    remaining_days = total_days - start_day + 1
    generate_days = min(4, remaining_days)  # Generate max 4 days per request
    should_continue = (start_day + generate_days) <= total_days

    print(f"DEBUG: remaining_days={remaining_days}, generate_days={generate_days}, should_continue={should_continue}")

    
    # Define the prompt for OpenAI
    prompt = f"""
    You are an AI travel assistant. Your job is to generate a highly personalized, detailed, and structured travel itinerary based on the user's request.

     ## **User Request**
    - **User Input:** "{user_prompt}"
    - **Trip Type:** '{trip_type}'
    - **Start from day {start_day}**.
    - **Generate exactly 4 days of itinerary**.
    - **Do NOT summarize previous days**.
    - **Start from day {start_day}**.
    - **Generate exactly {generate_days} days**.
    - **Continue generating days until total_days ({total_days}) is fully reached**.
    - **Set `"continue"` to {str(should_continue).lower()} exactly as provided**.
    - **If total_days is reached, `"continue"` must be `false`. Otherwise, it must be `true`**.


    ## **Critical JSON Output Rule**
    - `"continue"` must be **exactly `{str(should_continue).lower()}`**, and it **must not** be `false` unless the full trip has been generated.
    - `"next_start_day"` must be **exactly `{start_day + generate_days if should_continue else total_days}`**.

    
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
      - `"location"`: The exact location with `"Name of the place,City, Country"` format (e.g., `"Eiffel Tower, Paris, France"`).
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
      "accommodation": "Boutique hotel",
      "continue": {str(should_continue).lower()},
      "next_start_day": {start_day + generate_days if should_continue else total_days}
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

    print(f"prompt: {prompt}")
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

    try:
        # OpenAI API call with streaming enabled
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            stream=True
        )

        for chunk in response:
            content = chunk.choices[0].delta.content  # Extract streamed content

            if content:
                yield content  # Send it immediately to frontend


    except Exception as e:
        print(f"Error during OpenAI streaming: {e}")
        yield json.dumps({"error": "Failed to fetch itinerary from OpenAI."})

def extract_total_days(user_prompt: str, api_key: str) -> int:
    """
    Calls OpenAI to extract the total number of days from the user's request.
    """
    client = openai.OpenAI(api_key=api_key)

    prompt = f"""
    You are a travel assistant. Extract the number of days the user wants for their trip.

    ## **User Input:**
    "{user_prompt}"

    ## **Output Format:**
    Return a **single integer** representing the number of days in the trip.
    If the user did not specify a number of days, **guess based on their request**.

    **Example Responses:**
    - "I want a 10-day trip to Japan" → `10`
    - "Plan me a week-long trip to Thailand" → `7`
    - "A weekend in Paris" → `2`
    - "A long vacation in Spain" → `14`
    - "No duration mentioned" → `7` (default to a reasonable guess)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.5
        )

        extracted_days = int(response.choices[0].message.content.strip())
        total_days = min(max(1, extracted_days), 5)
        return total_days
    except Exception as e:
        print(f"Error extracting total days: {e}")
        return 7  # Default to 7 days if extraction fails



@app.get("/generate-itinerary/")
def get_itinerary(destination: str, api_key: str = Query(...), trip_type: str = "standard", start_day: int = Query(1)):
    """
    Automatically extracts `total_days` from the user's prompt before generating the itinerary.
    """
    total_days = extract_total_days(destination, api_key)  # Auto-detect total days

    return StreamingResponse(
        openai_stream_response(destination, api_key, trip_type, start_day, total_days),
        media_type="text/event-stream"
    )

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
    Streams the fake itinerary day by day with varying chunk sizes, simulating real-time API streaming.
    """
    yield '{"days": [\n'  # Start of JSON array

    for i, day in enumerate(FAKE_ITINERARY["days"]):
        await asyncio.sleep(random.uniform(0.5, 1.5))  # Simulating varied network latency

        # Convert day to JSON and break it into random-sized chunks
        chunk = json.dumps(day, ensure_ascii=False)
        chunk_size = random.randint(20, 100)  # Random chunk size between 20-100 characters
        chunks = [chunk[i:i+chunk_size] for i in range(0, len(chunk), chunk_size)]

        for part in chunks:
            await asyncio.sleep(random.uniform(0.2, 0.6))  # Simulating varied response speeds
            yield part

        yield ",\n" if i < len(FAKE_ITINERARY["days"]) - 1 else "\n"  # Comma for separation

    # Stream the remaining details
    await asyncio.sleep(random.uniform(0.5, 1.5))
    yield f'], "total_budget": "{FAKE_ITINERARY["total_budget"]}",\n'
    
    await asyncio.sleep(random.uniform(0.5, 1.5))
    yield f'"transportation": {json.dumps(FAKE_ITINERARY["transportation"])},\n'
    
    await asyncio.sleep(random.uniform(0.5, 1.5))
    yield f'"accommodation": "{FAKE_ITINERARY["accommodation"]}"}}\n'  # End of JSON

@app.get("/generate-itinerary-fake/")
async def get_itinerary_fake(destination: str, trip_type: str = "standard"):
    """
    Streams the fake AI-generated travel itinerary **as it's being generated** for real-time frontend updates.
    """
    return StreamingResponse(generate_fake_itinerary_stream(destination, trip_type), media_type="text/event-stream")
