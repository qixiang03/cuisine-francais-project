import os
import requests
import deepl
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Global API Key Loading and DeepL Translator Initialization ---
# These remain outside the main function so they are initialized once.
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
DEEPL_API_TYPE = os.getenv('DEEPL_API_TYPE', 'free').lower() # 'free' or 'pro'

# Basic checks for API keys
if SPOONACULAR_API_KEY is None:
    print("FATAL ERROR: SPOONACULAR_API_KEY not found in .env file. Exiting.")
    exit(1) # Exit with an error code
if DEEPL_API_KEY is None:
    print("FATAL ERROR: DEEPL_API_KEY not found in .env file. Exiting.")
    exit(1)

print("Spoonacular API Key loaded.")
print("DeepL API Key loaded.")

# Initialize DeepL Translator
translator = None
try:
    if DEEPL_API_TYPE == 'free':
        translator = deepl.Translator(DEEPL_API_KEY, server_url="https://api-free.deepl.com")
        print("Using DeepL Free API.")
    else:
        translator = deepl.Translator(DEEPL_API_KEY)
        print("Using DeepL Pro API.")
    
    # Optional: Verify authentication and print usage
    user_usage = translator.get_usage()
    if user_usage.any_limit_reached:
        print("WARNING: DeepL quota limit reached or warning received. Translations might fail.")
    elif user_usage.character:
        print(f"DeepL Characters Used: {user_usage.character.count}, Limit: {user_usage.character.limit}")

except deepl.DeepLError as e:
    print(f"FATAL ERROR: DeepL Translator initialization failed: {e}")
    print("Please check your DeepL API key and API type ('free' or 'pro'). Exiting.")
    exit(1) # Exit if translator cannot be initialized

def translate_text(text, target_language='fr'):
    """
    Translates the given text to the target language using DeepL.
    Returns the translated text or an error message if translation fails.
    """
    if not text:
        return ""
    if translator is None: # Check if translator was initialized successfully
        return f"[Translation Error: DeepL translator not initialized]"

    try:
        result = translator.translate_text(text, target_lang=target_language)
        return result.text
    except deepl.exceptions.DeepLError as e:
        # Specific DeepL API errors
        print(f"DeepL translation API error for '{text}': {e}")
        return f"[Translation API Error]"
    except Exception as e:
        # General unexpected errors during translation
        print(f"An unexpected error occurred during translation for '{text}': {e}")
        return f"[Translation Error]"


def get_and_translate_recipe(query: str, cuisine: str = "French", target_language: str = "fr") -> dict:
    """
    Fetches a recipe from Spoonacular API, translates its elements using DeepL,
    and returns the structured recipe data.

    Args:
        query (str): The search term for the recipe (e.g., "boeuf bourguignon").
        cuisine (str): The cuisine type (e.g., "French").
        target_language (str): The language to translate to (e.g., "fr").

    Returns:
        dict: A dictionary containing the recipe details and metadata,
              or an error message if fetching/translation fails.
    """
    # Initialize the structured data dictionary
    recipe_data = {
        "title_en": None,
        "title_fr": None,
        "cooking_time_minutes": None,
        "ingredients": [],
        "spoonacular_quota": {
            "request": None,
            "used_total": None,
            "left": None
        },
        "error": None
    }

    # Spoonacular API base URL for Complex Search
    BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

    # Parameters for the GET request
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "cuisine": cuisine,
        "query": query,
        "number": 1,
        "addRecipeInformation": True
    }

    print(f"\n--- Fetching Recipe: Cuisine='{cuisine}', Query='{query}' ---")

    try:
        response = requests.get(BASE_URL, params=params)

        # --- Error Handling for Spoonacular API ---
        # Specific handling for common API errors before raise_for_status
        if response.status_code == 401:
            recipe_data["error"] = "Spoonacular API: Unauthorized. Check your API key."
            print(recipe_data["error"])
            return recipe_data
        elif response.status_code == 402:
            recipe_data["error"] = "Spoonacular API: Quota Exceeded. You've reached your daily limit."
            print(recipe_data["error"])
            # Still try to parse headers for quota info if possible
        elif response.status_code == 404:
            recipe_data["error"] = "Spoonacular API: Endpoint not found. Check URL."
            print(recipe_data["error"])
            return recipe_data
        
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        print("Spoonacular API Response received successfully.")

        # Store Spoonacular quota information
        recipe_data["spoonacular_quota"]["request"] = response.headers.get('X-API-Quota-Request')
        recipe_data["spoonacular_quota"]["used_total"] = response.headers.get('X-API-Quota-Used')
        recipe_data["spoonacular_quota"]["left"] = response.headers.get('X-API-Quota-Left')

        # Check if any recipes were found
        if data and data.get('results'):
            first_recipe = data['results'][0]

            # Populate original recipe details
            recipe_data["title_en"] = first_recipe.get('title')
            recipe_data["cooking_time_minutes"] = first_recipe.get('readyInMinutes')

            # Translate title
            if recipe_data["title_en"]:
                recipe_data["title_fr"] = translate_text(recipe_data["title_en"], target_language)

            # Process and translate ingredients
            ingredients_list = first_recipe.get('extendedIngredients', [])
            for ingredient_data in ingredients_list:
                original_name = ingredient_data.get('original')
                if original_name:
                    translated_name = translate_text(original_name, target_language)
                    recipe_data["ingredients"].append({
                        "name_en": original_name,
                        "name_fr": translated_name
                    })

        else:
            recipe_data["error"] = f"No recipes found for '{query}' in {cuisine} cuisine."
            print(recipe_data["error"])

    except requests.exceptions.HTTPError as e:
        # This catches errors raised by response.raise_for_status()
        recipe_data["error"] = f"HTTP Error from Spoonacular API: {e.response.status_code} - {e.response.text}"
        print(recipe_data["error"])
    except requests.exceptions.ConnectionError as e:
        recipe_data["error"] = f"Connection Error to Spoonacular API: {e}. Check internet connection or API server."
        print(recipe_data["error"])
    except requests.exceptions.Timeout as e:
        recipe_data["error"] = f"Timeout Error from Spoonacular API: {e}. API server too slow."
        print(recipe_data["error"])
    except requests.exceptions.RequestException as e:
        recipe_data["error"] = f"General Request Error from Spoonacular API: {e}"
        print(recipe_data["error"])
    except KeyError as e:
        recipe_data["error"] = f"Error parsing Spoonacular JSON response: Missing expected key '{e}'. Response structure might have changed."
        print(recipe_data["error"])
    except Exception as e:
        recipe_data["error"] = f"An unexpected error occurred during recipe fetching/processing: {e}"
        print(recipe_data["error"])

    return recipe_data

# --- Main execution block (what runs when you execute the script directly) ---
if __name__ == "__main__":
    search_query = "Pasta"
    # search_query = "Pasta" # Test another query
    # search_query = "NonExistentRecipe12345" # Test no results
    # search_query = "Boeuf Bourguignon" # Original query

    # Call the new function
    recipe_details = get_and_translate_recipe(search_query, cuisine="French", target_language="fr")

    print("\n==================================")
    print("FINAL RECIPE DATA STRUCTURE:")
    print("==================================")
    if recipe_details.get("error"):
        print(f"Status: Error - {recipe_details['error']}")
    elif recipe_details.get("title_en"):
        print(f"Title (EN): {recipe_details['title_en']}")
        print(f"Title (FR): {recipe_details['title_fr']}")
        print(f"Cooking Time: {recipe_details['cooking_time_minutes']} minutes" if recipe_details['cooking_time_minutes'] is not None else "Cooking Time: N/A")
        print("\nIngredients:")
        for ingredient in recipe_details["ingredients"]:
            print(f"- {ingredient.get('name_en')} (FR: {ingredient.get('name_fr')})")
        
        print("\nSpoonacular Quota Info:")
        quota = recipe_details["spoonacular_quota"]
        print(f"  Request Used: {quota.get('request')}")
        print(f"  Total Used Today: {quota.get('used_total')}")
        print(f"  Remaining: {quota.get('left')}")
    else:
        print("No recipe data retrieved or unknown error occurred.")
        if recipe_details.get("error"): # Display the error if it was set
            print(f"Error Message: {recipe_details['error']}")

    print("\nScript finished.")