from flask import Flask, request, jsonify
from get_recipes import get_and_translate_recipe

app = Flask(__name__)

# Basic route for testing if the server is running8@app.route('/')
def home():
    return "Welcome to the Recipe API! Use /api/search?dish=<your_dish_query>"

@app.route('/api/search', methods=['GET'])
def search_recipe():
    """
    API endpoint to search for recipes and return structured data
    Requires a 'dish' query parameter
    Example: /api/search?dish=ratatouille
    """
    dish_query = requests.args.get('dish')

    if not dish_query:
        #return error if 'dish' parameter is missing
        return jsonify({"error": "Missing 'dish' query parameter. "
        "Example: /api/search?dish-ratatouille"}), 400
    
    print(f"Received API request for dish: {dish_query}")

    #calling from get_recipes.py
    recipe_data = get_and_translate_recipe(query = dish_query,
                                           cuisine="French",
                                           target_language="fr")
    
    if recipe_data.get("error"):
        status_code = 500
        if "Quota Exceeded" in recipe_data["error"] or "Unauthorized" in recipe_data["error"]:
            status_code = 402 # or 403 or 401 based on exact error type
        
        elif "No recipes found" in recipe_data["error"]:
            status_code = 404

        return jsonify(recipe_data), status_code
    
    else:
        return jsonify(recipe_data)
    

if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=5000)

