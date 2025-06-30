import os
import requests
import deepl
import json 
from dotenv import load_dotenv


load_dotenv()

# --- Global API Key Loading and DeepL Translator Initialization ---
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
DEEPL_API_TYPE = os.getenv('DEEPL_API_TYPE', 'free').lower()

if RAPIDAPI_KEY is None:
    print("FATAL ERROR: RAPIDAPI_KEY not found in .env file. Exiting.")
    exit(1)
if DEEPL_API_KEY is None:
    print("FATAL ERROR: DEEPL_API_KEY not found in .env file. Exiting.")
    exit(1)

print("RapidAPI Key loaded.")
print("DeepL API Key loaded.")

translator = None
try:
    if DEEPL_API_TYPE == 'free':
        translator = deepl.Translator(DEEPL_API_KEY, server_url="https://api-free.deepl.com")
        print("Using DeepL Free API.")
    else:
        translator = deepl.Translator(DEEPL_API_KEY)
        print("Using DeepL Pro API.")
    
    user_usage = translator.get_usage()
    if user_usage.any_limit_reached:
        print("WARNING: DeepL quota limit reached or warning received. Translations might fail.")
    elif user_usage.character:
        print(f"DeepL Characters Used: {user_usage.character.count}, Limit: {user_usage.character.limit}")

except deepl.DeepLError as e:
    print(f"FATAL ERROR: DeepL Translator initialization failed: {e}")
    print("Please check your DeepL API key and API type ('free' or 'pro'). Exiting.")
    exit(1)

def translate_text(text, target_language='fr'):
    # ... (translate_text function remains the same) ...
    """
    Translates the given text to the target language using DeepL.
    Returns the translated text or an error message if translation fails.
    """
    if not text:
        return ""
    if translator is None:
        return f"[Translation Error: DeepL translator not initialized]"

    try:
        result = translator.translate_text(text, target_lang=target_language)
        return result.text
    except deepl.exceptions.DeepLError as e:
        print(f"DeepL translation API error for '{text}': {e}")
        return f"[Translation API Error]"
    except Exception as e:
        print(f"An unexpected error occurred during translation for '{text}': {e}")
        return f"[Translation Error]"


def get_and_translate_recipe(query: str, cuisine: str = "French", target_language: str = "fr") -> dict:
    """
    Fetches a recipe from Spoonacular API, translates its elements using DeepL,
    and returns the structured recipe data.
    """
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

    BASE_URL = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/recipes/complexSearch"

    params = {
        "cuisine": cuisine,
        "query": query,
        "number": 1,
        "addRecipeInformation": True
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com"
    }

    print(f"\n--- Fetching Recipe: Cuisine='{cuisine}', Query='{query}' ---")

    try:
        response = requests.get(BASE_URL, params=params, headers=headers)
        
        if response.status_code == 401:
            recipe_data["error"] = "RapidAPI Spoonacular: Unauthorized. Check your RapidAPI key."
            print(recipe_data["error"])
            return recipe_data
        elif response.status_code == 402:
            recipe_data["error"] = "RapidAPI Spoonacular: Quota Exceeded. You've reached your daily limit."
            print(recipe_data["error"])
            return recipe_data
        elif response.status_code == 403:
            recipe_data["error"] = "RapidAPI Spoonacular: Forbidden. Check your subscription or API permissions."
            print(recipe_data["error"])
            return recipe_data
        elif response.status_code == 404:
            recipe_data["error"] = "RapidAPI Spoonacular: Endpoint not found. Check URL."
            print(recipe_data["error"])
            return recipe_data
        
        response.raise_for_status()
        data = response.json()
        print("RapidAPI Spoonacular Response received successfully.")

        # --- DEBUGGING STEP 1: Print the full API response data ---
        print("\n--- RAW SPOONACULAR API RESPONSE (FULL) ---")
        print(json.dumps(data, indent=2))
        print("-------------------------------------------\n")

        # Store RapidAPI quota information
        recipe_data["spoonacular_quota"]["request"] = response.headers.get('X-RateLimit-Requests-Remaining')
        recipe_data["spoonacular_quota"]["used_total"] = response.headers.get('X-RateLimit-Requests-Used')
        recipe_data["spoonacular_quota"]["left"] = response.headers.get('X-RateLimit-Requests-Remaining')

        if data and data.get('results'):
            first_recipe = data['results'][0]

            # --- DEBUGGING STEP 2: Print the first recipe object ---
            print("\n--- RAW FIRST RECIPE OBJECT ---")
            print(json.dumps(first_recipe, indent=2))
            print("---------------------------------\n")

            recipe_data["title_en"] = first_recipe.get('title')
            recipe_data["cooking_time_minutes"] = first_recipe.get('readyInMinutes')

            if recipe_data["title_en"]:
                recipe_data["title_fr"] = translate_text(recipe_data["title_en"], target_language)

            ingredients_list = first_recipe.get('extendedIngredients', [])
            
            # --- DEBUGGING STEP 3: Confirm what was pulled for ingredients_list ---
            print(f"DEBUG: 'extendedIngredients' extracted: {ingredients_list}")


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
        recipe_data["error"] = f"HTTP Error from RapidAPI Spoonacular: {e.response.status_code} - {e.response.text}"
        print(recipe_data["error"])
    except requests.exceptions.ConnectionError as e:
        recipe_data["error"] = f"Connection Error to RapidAPI Spoonacular: {e}. Check internet connection or API server."
        print(recipe_data["error"])
    except requests.exceptions.Timeout as e:
        recipe_data["error"] = f"Timeout Error from RapidAPI Spoonacular: {e}. API server too slow."
        print(recipe_data["error"])
    except requests.exceptions.RequestException as e:
        recipe_data["error"] = f"General Request Error from RapidAPI Spoonacular: {e}"
        print(recipe_data["error"])
    except KeyError as e:
        recipe_data["error"] = f"Error parsing RapidAPI Spoonacular JSON response: Missing expected key '{e}'. Response structure might have changed."
        print(recipe_data["error"])
    except Exception as e:
        recipe_data["error"] = f"An unexpected error occurred during recipe fetching/processing: {e}"
        print(recipe_data["error"])

    return recipe_data



# --- Main execution block ---
if __name__ == "__main__":
    search_query = "Coq Au Vin"
    # search_query = "Pasta"
    # search_query = "NonExistentRecipe12345" # Test no results
    # search_query = "Boeuf Bourguignon"
    # search_query = "Pizza" # Good for testing ingredients

    print("\nStarting debug run of get_recipes.py directly.\n")
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
        if recipe_details["ingredients"]:
            for ingredient in recipe_details["ingredients"]:
                print(f"- {ingredient.get('name_en')} (FR: {ingredient.get('name_fr')})")
        else:
            print("No ingredients were parsed or found in the response.")
        
        print("\nRapidAPI Quota Info:")
        quota = recipe_details["spoonacular_quota"]
        print(f"  Request Used: {quota.get('request')}")
        print(f"  Total Used Today: {quota.get('used_total')}")
        print(f"  Remaining: {quota.get('left')}")
    else:
        print("No recipe data retrieved or unknown error occurred.")
        if recipe_details.get("error"):
            print(f"Error Message: {recipe_details['error']}")

    print("\nScript finished.")