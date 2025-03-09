import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import helper functions from our CSV-based recommendation module.
from helpers.database import get_user  # to fetch user info (as used in informations.py)
from helpers.recipe_recommandation import propose_recipes, get_food_image_url

import streamlit as st
import pandas as pd
from PIL import Image
from datetime import datetime

# Import our YOLO-based fridge analysis function from our custom module.
from helpers.food_detection import analyse_frigo

@st.cache_data
def load_food_data():
    return pd.read_csv(r'data/processed_recipes_with_categories.csv')

food_data = load_food_data()

def calculate_bmr(weight, height, age, gender):
    """Calculates the Basal Metabolic Rate using the Mifflin-St Jeor equation."""
    # Convert input values to float, providing defaults if conversion fails.
    try:
        weight = float(weight)
    except (ValueError, TypeError):
        weight = 70.0
    try:
        height = float(height)
    except (ValueError, TypeError):
        height = 175.0
    try:
        age = float(age)
    except (ValueError, TypeError):
        age = 30

    if gender == 'M':
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161


def get_daily_calories_from_garmin():
    """Dummy function simulating daily calories burned from a Garmin API."""
    return 300

def show():
    st.title("Show me the Food! I'll tell you what to eat 🍔🥗")

    # Retrieve user info from session state using the database helper.
    username = st.session_state.get("user")
    if not username:
        st.warning("You must be logged in to access this page.")
        return
    user = get_user(username)
    
    # Use user info for nutritional calculations (default values if not set).
    weight = user[4] if user[4] else 70.0
    height = user[5] if user[5] else 175.0
    # Assuming user[3] is in the format 'YYYY-MM-DD'
    birth_date_str = user[3]
    if birth_date_str:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    else:
        age = 30  # Default age if no birth date is provided
    gender = user[6]
    
    # --- Fridge Scanner Section ---
    st.header("Fridge Scanner")
    uploaded_image = st.file_uploader("Upload an image of your fridge", type=["jpg", "jpeg", "png"])
    detected_ingredients = []
    if uploaded_image is not None:
        # Save the uploaded image to disk as a temporary file.
        temp_image_path = os.path.join("data", "fridge_images", "temp_uploaded.jpg")
        with open(temp_image_path, "wb") as f:
            f.write(uploaded_image.read())
        
        # Analyze the saved image using the YOLO model.
        with st.spinner('Analyzing the fridge...'):
            detected_ingredients = analyse_frigo(temp_image_path)
        st.write("Detected ingredients:", detected_ingredients)
        
        # Display the annotated image saved by the model.
        annotated_image_path = os.path.join("data", "fridge_images", "output", os.path.basename(temp_image_path))
        if os.path.exists(annotated_image_path):
            st.image(annotated_image_path, caption="Annotated Fridge Image", use_container_width=True)
        else:
            st.write("No image uploaded. You can manually select the ingredients.")

    
    # --- Ingredient Selection (Fixed List of 30) ---
    ingredient_options = [
        "apple", "banana", "beef", "blueberries", "bread", "butter", "carrot",
        "cheese", "chicken", "chicken_breast", "chocolate", "corn", "eggs",
        "flour", "goat_cheese", "green_beans", "ground_beef", "ham", "heavy_cream",
        "lime", "milk", "mushrooms", "onion", "potato", "shrimp", "spinach",
        "strawberries", "sugar", "sweet_potato", "tomato"
    ]
    
    # Preselect detected ingredients that are in our fixed list.
    default_selection = [ing for ing in detected_ingredients if ing in ingredient_options]
    
    manual_selection = st.multiselect(
        "Select ingredients",
        ingredient_options,
        default=default_selection
    )
    selected_ingredients = manual_selection if manual_selection else default_selection

    # --- Nutritional Calculations ---
    st.header("Nutritional Needs")
    bmr = calculate_bmr(weight, height, age, gender)
    daily_calories_burned = get_daily_calories_from_garmin()
    tdee = bmr + daily_calories_burned
    # Create a DataFrame for the nutritional information
    nutritional_data = {
        "Metric": ["BMR (Basal Metabolic Rate)", "Daily Calories Burned (Simulated Garmin)", "TDEE (Total Daily Energy Expenditure)"],
        "Value": [f"{bmr:.0f} calories/day", f"{daily_calories_burned} calories", f"{tdee:.0f} calories/day"]
    }

    df_nutritional = pd.DataFrame(nutritional_data)

    # Display the table with styling
    st.subheader("Your Nutritional Overview")
    st.markdown("Here’s a summary of your current nutritional metrics:")

    st.dataframe(df_nutritional.style.set_properties(subset=["Value"], **{
        "background-color": "#f5f5f5", "color": "#333", "text-align": "center"}))
        
    # Make the goal column bold for better visibility
    st.markdown(f""" 
    **⬇️ Lose Weight** < {tdee:.0f} cal/day < ⬆️ Gain Weight**
    """)


    # --- Recipe Recommendations ---
    st.header("Recipe Recommendations")
    if st.button("Find Recipes"):
        if selected_ingredients:
            matching_recipes = propose_recipes(selected_ingredients)
            if not matching_recipes.empty:
                top_recipes = matching_recipes.head(10)  # Limit to top 10 recipes
                st.write(f"Found a top-{len(top_recipes)} matching recipes!")

                for idx, recipe in top_recipes.iterrows():
                    st.subheader(recipe["name"].capitalize())
                    
                    # Création de colonnes pour mieux organiser l'affichage
                    col1, col2 = st.columns([2, 1])  # 2/3 pour image + infos, 1/3 pour ingrédients
                    
                    with col1:
                        # Lien cliquable sur l'image
                        image_url = get_food_image_url(recipe["id"])
                        if image_url:
                            recipe_url = f"https://www.food.com/recipe/{recipe['name'].lower().replace(' ', '-')}-{recipe['id']}"  # Génère le lien vers la recette
                            st.markdown(f'<a href="{recipe_url}" target="_blank"><img src="{image_url}" alt="{recipe["name"]}" style="width:100%;"></a>', unsafe_allow_html=True)
                        else:
                            st.write("No image available.")

                        
                        # Affichage du temps de cuisson et de la description
                        st.write(f"⏳ **Cooking time**: {recipe['minutes']} minutes")
                        st.write(f"📜 **Author's description:** {recipe['description']}")
                        
                        # Affichage des PDV sous forme de tableau
                        pdv_data = {
                            "Calories": [recipe["calories"]],
                            "Fat PDV": [recipe["total_fat_PDV"]],
                            "Sugar PDV": [recipe["sugar_PDV"]],
                            "Sodium PDV": [recipe["sodium_PDV"]],
                            "Protein PDV": [recipe["protein_PDV"]],
                            "Saturated Fat PDV": [recipe["saturated_fat_PDV"]],
                            "Carbohydrates PDV": [recipe["carbohydrates_PDV"]],
                        }
                        # Convert the dictionary to a DataFrame
                        df = pd.DataFrame(pdv_data)

                        # Function to format numbers
                        def format_number(val, is_first_value=False):
                            if isinstance(val, (int, float)):
                                if is_first_value:  # No decimals for the first value
                                    return int(val)
                                else:  # Add "%" for the others and round to 2 decimals
                                    return f"{val:.2f}%"
                            return val

                        # Apply the formatting to the whole DataFrame
                        # Apply the formatting to the whole DataFrame using apply instead of applymap
                        df_formatted = df.apply(lambda col: col.apply(lambda x: format_number(x, is_first_value=False)))

                        df_formatted.iloc[0, 0] = format_number(df_formatted.iloc[0, 0], is_first_value=True).replace('%','')  # Ensure no decimals for the first value

                    
                    with col2:
                        # Affichage des ingrédients à droite
                        st.write("🛒 **Ingredients:**")
                        for ingredient in recipe["ingredients_list"].split(", "):
                            st.write("- {}".format(ingredient.replace('\"', '').strip().strip("[").strip("]").strip("'")))
                    
                    # Display the table with formatted values
                    st.table(df_formatted.style.hide(axis="index"))
            else:
                st.warning("No recipes found with these ingredients. Try adding more!")
        else:
            st.warning("Please select at least one ingredient.")


    
    st.markdown("""
    *Note:* This demo uses CSV data for recipes. The CSV is static and loaded only once.
    """)

if __name__ == "__main__":
    show()
