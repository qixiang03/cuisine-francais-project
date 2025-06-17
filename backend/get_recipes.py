import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("SPOONACULAR_API_KEY")

if api_key:
    print(f"API Key loaded successfully: {api_key[:5]}... (showing first 5 chars)")
else:
    print("Error: SPOONACULAR_API_KEY not found in environment variables.")
    print("Please make sure you have a .env file with SPOONACULAR_API_KEY=your_key")
    exit()

BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

params = {
    "apiKey": api_key,
    "cuisine": "French",
    "query": "Salade niçoise",
    "number": 1, # Request only 1 recipe
    "addRecipeInformation": True # This is crucial for getting cooking time and ingredients in the same response
}

print(f"Attempting to fetch recipe for: Cuisine='{params['cuisine']}', Query='{params['query']}'")

try:
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
    data = response.json()
    print("API Response received successfully.")

    # --- New code to display quota information ---
    print("\n--- API Quota Information ---")
    quota_request = response.headers.get('X-API-Quota-Request')
    quota_used = response.headers.get('X-API-Quota-Used')
    quota_left = response.headers.get('X-API-Quota-Left')

    if quota_request:
        print(f"Points used by this request: {quota_request}")
    if quota_used:
        print(f"Total points used today: {quota_used}")
    if quota_left:
        print(f"Points remaining today: {quota_left}")
    else:
        print("Quota headers not found in response. (May indicate an issue or different API plan)")
    # --- End of new code ---

    # Check if any recipes were found
    if data and data.get('results'):
        first_recipe = data['results'][0]

        title = first_recipe.get('title')
        cooking_time = first_recipe.get('readyInMinutes')
        ingredients_list = first_recipe.get('extendedIngredients', [])

        print("\n--- First Recipe Details ---")
        print(f"Title: {title}")
        if cooking_time is not None:
            print(f"Cooking Time: {cooking_time} minutes")
        else:
            print("Cooking Time: Not available")

        print("Ingredients:")
        if ingredients_list:
            for ingredient in ingredients_list:
                print(f"- {ingredient.get('original')}")
        else:
            print("No ingredients found.")

    else:
        print(f"No recipes found for '{params["query"]}' in French cuisine.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred during the API request: {e}")
    # When an error (like 402 for quota exceeded) occurs, check response headers if available
    if hasattr(e, 'response') and e.response is not None:
        print("Response headers (even on error):")
        print(e.response.headers)
    exit()
except KeyError as e:
    print(f"Error parsing JSON response: Missing key {e}. Response structure might have changed or is unexpected.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
