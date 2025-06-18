import os
import requests
import deepl # Add this import
from dotenv import load_dotenv

load_dotenv()

# Get the API keys
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY') # Get DeepL key
DEEPL_API_TYPE = os.getenv('DEEPL_API_TYPE', 'free').lower() # 'free' or 'pro'

if SPOONACULAR_API_KEY is None:
    print("Error: SPOONACULAR_API_KEY not found in .env file.")
    exit()
if DEEPL_API_KEY is None:
    print("Error: DEEPL_API_KEY not found in .env file.")
    exit()

print("Spoonacular API Key loaded successfully.")
print("DeepL API Key loaded successfully.")


# Initialize DeepL Translator (global scope or passed around, but for a script, global is fine)
translator = None
try:
    if DEEPL_API_TYPE == 'free':
        translator = deepl.Translator(DEEPL_API_KEY, server_url="https://api-free.deepl.com")
        print("Using DeepL Free API.")
    else: # Default to Pro if not explicitly 'free'
        translator = deepl.Translator(DEEPL_API_KEY)
        print("Using DeepL Pro API.")
    # Optional: Verify authentication
    user_usage = translator.get_usage()
    if user_usage.any_limit_reached:
        print("DeepL quota limit reached or warning received. Translations might fail.")
    elif user_usage.character:
        print(f"DeepL Characters Used: {user_usage.character.count}, Limit: {user_usage.character.limit}")
except deepl.DeepLError as e:
    print(f"Error initializing DeepL Translator: {e}")
    print("Please check your DeepL API key and API type ('free' or 'pro').")
    translator = None # Ensure translator is None if initialization fails


def translate_text(text, target_language='fr'):
    """
    Translates the given text to the target language using DeepL.
    """
    if not text or not translator:
        return "" # Return empty string if no text or translator isn't initialized

    try:
        # DeepL automatically detects source language, so we only specify target.
        result = translator.translate_text(text, target_lang=target_language)
        return result.text
    except deepl.exceptions.DeepLError as e:
        print(f"DeepL translation error: {e}")
        # Common errors: quota exceeded (429), invalid auth (403), etc.
        return f"[Translation Error: {e}]"
    except Exception as e:
        print(f"An unexpected error occurred during translation: {e}")
        return f"[Translation Error: {e}]"




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
        print(f"No recipes found for '{params["query"]}' in {params["cuisine"]} cuisine.")

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
