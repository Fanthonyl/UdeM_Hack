import sqlite3
import bcrypt
from datetime import date
import json
from garminconnect import Garmin


DB_FILE = "data/users.db"

def init_db():
    """Crée les tables users et activities si elles n'existent pas"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # supprime garmin_id et garmin_password du user 1
    # cursor.execute("""
    # UPDATE users
    # SET weight = 70, birth_date = '2001-06-08'
    # WHERE id = 8 OR id = 9
    # """)

    #detele table activities
    # cursor.execute("""
    # DROP TABLE IF EXISTS activities
    # """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        birth_date TEXT,
        weight REAL,
        height REAL,
        gender TEXT CHECK(gender IN ('M', 'F')),
        garmin_id TEXT DEFAULT NULL,
        garmin_password TEXT DEFAULT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        activity_name TEXT,
        start_time TEXT,
        calories REAL,
        bmrCalories REAL,
        steps INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS poids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        poid REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pdv (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        calories REAL,
        total_fat_PDV REAL,
        sugar_PDV REAL,
        sodium_PDV REAL,
        protein_PDV REAL,
        saturated_fat_PDV REAL,
        carbohydrates_PDV REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def import_garmin_data(garmin_id, garmin_password):
    try:
        print(garmin_id, garmin_password)
        client = Garmin(garmin_id, garmin_password)
        client.login()
        
        # Get latest activities
        activities = client.get_activities(0, 5)  # Fetch last 5 activities
        # Convert activities to a list of dictionaries
        filtered_activities = [
            {
                "id": activity["activityId"],
                "activity_name": activity["activityName"],
                "start_time": activity["startTimeLocal"],
                "calories": activity["calories"],
                "bmrCalories": activity["bmrCalories"],
                "steps": activity["steps"]
            }
            for activity in activities
        ]
        return filtered_activities
    except Exception as e:
        print(e)
        return None

def add_activity(user_id, garmin_id, garmin_password):
    """Ajoute une activité à un utilisateur sans doublons"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get activities from Garmin
    activities = import_garmin_data(garmin_id, garmin_password)
    if activities is None:
        return False
    for activity in activities:
        cursor.execute("""
        INSERT INTO activities (id, user_id, activity_name, start_time, calories, bmrCalories, steps) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""", 
        (activity["id"], user_id, activity["activity_name"], activity["start_time"], activity["calories"], activity["bmrCalories"], activity["steps"]))

    conn.commit()
    conn.close()
    return True


def get_garmin_id(user_id):
    """Récupère l'identifiant Garmin et le mot de passe d'un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT garmin_id, garmin_password FROM users WHERE id = ?", (user_id,))
    garmin_id, garmin_password = cursor.fetchone()
    conn.close()
    return garmin_id, garmin_password

def get_activities(username):
    """Récupère toutes les activités d'un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT activity_name, start_time, calories, caloriesBmr, steps 
    FROM activities 
    JOIN users ON activities.user_id = users.id 
    WHERE users.username = ?
    """, (username,))

    activities = cursor.fetchall()
    conn.close()
    return activities

def add_poids(user_id, poid):
    """Ajoute une nouvelle entrée de poids pour un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO poids (user_id, poid, date) VALUES (?, ?, ?)
    """, (user_id, poid, date.today()))
    conn.commit()
    conn.close()

def get_poids(user_id):
    """Récupère l'historique de poids d'un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT poid, date FROM poids WHERE user_id = ? ORDER BY date DESC
    """, (user_id,))
    poids = cursor.fetchall()  
    conn.close()
    return poids    

def add_pdv(user_id, calories, total_fat_PDV, sugar_PDV, sodium_PDV, protein_PDV, saturated_fat_PDV, carbohydrates_PDV):
    """Ajoute une entrée de pourcentage de valeurs nutritionnelles"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO pdv (user_id, calories, total_fat_PDV, sugar_PDV, sodium_PDV, protein_PDV, saturated_fat_PDV, carbohydrates_PDV, date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, calories, total_fat_PDV, sugar_PDV, sodium_PDV, protein_PDV, saturated_fat_PDV, carbohydrates_PDV, date.today()))
    conn.commit()
    conn.close()

def get_pdv(user_id):
    """Récupère les valeurs nutritionnelles pour un utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT calories, total_fat_PDV, sugar_PDV, sodium_PDV, protein_PDV, saturated_fat_PDV, carbohydrates_PDV, date 
    FROM pdv WHERE user_id = ? ORDER BY date DESC
    """, (user_id,))
    pdv_data = cursor.fetchall()
    conn.close()
    return pdv_data

def hash_password(password):
    """Hash le mot de passe"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed_password):
    """Vérifie si le mot de passe correspond au hash"""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def register_user(username, password, birth_date, height, weight, gender, garmin_id=None, garmin_password=None):
    """Ajoute un utilisateur dans la base avec les nouvelles données"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        garmin_password_hash = hash_password(garmin_password) if garmin_password else None
        
        cursor.execute("""
        INSERT INTO users (username, password_hash, birth_date, height, weight, gender, garmin_id, garmin_password) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, password_hash, birth_date.strftime('%Y-%m-%d'), height, weight, gender, garmin_id, garmin_password_hash))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # L'utilisateur existe déjà
    finally:
        conn.close()
        
def get_user(username):
    """Récupère les infos d'un utilisateur par son username"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_info(username, weight=None, height=None, birth_date=None, gender=None, garmin_id=None, garmin_password=None):
    """Met à jour les informations de l'utilisateur"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    garmin_password_hash = hash_password(garmin_password) if garmin_password else None
    cursor.execute("""
    UPDATE users 
    SET weight = ?, height = ?, birth_date = ?, gender = ?, garmin_id = ?, garmin_password = ?
    WHERE username = ?
    """, (weight, height, birth_date, gender, garmin_id, garmin_password_hash, username))
    conn.commit()
    conn.close()