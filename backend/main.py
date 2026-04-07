# ================= IMPORTS =================
import os
import requests
from fastapi import FastAPI, File, UploadFile
from fastapi import UploadFile, File
import json
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from pydantic import BaseModel
from io import BytesIO
import cv2
import tensorflow as tf
import shutil
from collections import Counter
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId
from fastapi import Body
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import librosa
import tensorflow_hub as hub
from fastapi import HTTPException


from pymongo import MongoClient

client = MongoClient(os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/"))
db = client["endangered"]
users_collection = db["users"]
# ================= GEO MAPPING =================

# 🇮🇳 All Indian States → India
state_to_country = {
    "andhra pradesh": "india",
    "arunachal pradesh": "india",
    "assam": "india",
    "bihar": "india",
    "chhattisgarh": "india",
    "goa": "india",
    "gujarat": "india",
    "haryana": "india",
    "himachal pradesh": "india",
    "jharkhand": "india",
    "karnataka": "india",
    "kerala": "india",
    "madhya pradesh": "india",
    "maharashtra": "india",
    "manipur": "india",
    "meghalaya": "india",
    "mizoram": "india",
    "nagaland": "india",
    "odisha": "india",
    "punjab": "india",
    "rajasthan": "india",
    "sikkim": "india",
    "tamil nadu": "india",
    "telangana": "india",
    "tripura": "india",
    "uttar pradesh": "india",
    "uttarakhand": "india",
    "west bengal": "india",
    "delhi": "india"
}

# 🌏 Countries → Continents
country_to_continent = {
    # Asia
    "india": "asia",
    "nepal": "asia",
    "bhutan": "asia",
    "bangladesh": "asia",
    "china": "asia",
    "thailand": "asia",
    "indonesia": "asia",
    "japan": "asia",
    "sri lanka": "asia",
    "malaysia": "asia",

    # Africa
    "kenya": "africa",
    "south africa": "africa",
    "nigeria": "africa",
    "egypt": "africa",

    # Europe
    "germany": "europe",
    "france": "europe",
    "uk": "europe",
    "italy": "europe",

    # North America
    "usa": "north america",
    "canada": "north america",
    "mexico": "north america",

    # South America
    "brazil": "south america",
    "argentina": "south america",

    # Oceania
    "australia": "oceania",
    "new zealand": "oceania"
}
# 🌍 CONTINENTS (GLOBAL LEVEL)
continents = [
    "asia",
    "africa",
    "europe",
    "north america",
    "south america",
    "oceania",
    "antarctica"
]

# ================= AUDIO MODEL =================
yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")

image_model = MobileNetV2(weights='imagenet')

model = LinearRegression()
years = np.array([2014, 2016, 2018, 2020, 2022, 2024]).reshape(-1, 1)

CACHE_FILE = "image_cache.json"

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        image_cache = json.load(f)
else:
    image_cache = {}

class TextInput(BaseModel):
    text: str

# ================= APP =================
app = FastAPI()
# ================= USER DATA (NEW) =================
from datetime import datetime

history_db = []
favourites_db = []
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= LOAD EXCEL (ONLY ONCE - FIXED) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "data", "processed", "animals.xlsx")

excel_data = pd.read_excel(EXCEL_PATH, sheet_name=None)

# 🔥 Combined sheet (for detection)
all_animals_df = excel_data["all_animals"].copy()

all_animals_df.columns = all_animals_df.columns.str.strip()
all_animals_df["animal_name"] = all_animals_df["animal_name"].astype(str).str.strip().str.lower()
all_animals_df["animal_type"] = all_animals_df["animal_type"].astype(str).str.strip().str.lower()

# 🔵 Individual sheets (for explore flow)
dataframes = {}

for sheet_name, df in excel_data.items():
    df.columns = df.columns.str.strip()
    df["state"] = df["state"].astype(str).str.strip().str.lower()
    df["animal_type"] = df["animal_type"].astype(str).str.strip().str.lower()
    dataframes[sheet_name] = df

# ================= LABEL CLEANING =================
def clean_species(label):
    label = label.lower()

    if "tiger" in label:
        return "tiger"
    elif "lion" in label:
        return "lion"
    elif "elephant" in label:
        return "elephant"
    elif "bear" in label:
        return "bear"
    elif "wolf" in label:
        return "wolf"
    else:
        return label

# ================= IMAGE FETCH =================
def get_image_from_wiki(animal_name):
    try:
        name = animal_name.lower()

        if "(" in name:
            name = name.split("(")[0].strip()

        replacements = {
            "bengal tiger": "tiger",
            "indian leopard": "leopard",
            "wild dog": "dhole",
            "striped hyena": "hyena",
            "indian wolf": "wolf"
        }

        if name in replacements:
            name = replacements[name]

        key = name.replace(" ", "_")

        if key in image_cache:
            return image_cache[key]

        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{key}"
        headers = {"User-Agent": "Mozilla/5.0"}

        res = requests.get(url, headers=headers, timeout=3)

        if res.status_code == 200:
            data = res.json()

            if "thumbnail" in data:
                img = data["thumbnail"]["source"]

                image_cache[key] = img
                with open(CACHE_FILE, "w") as f:
                    json.dump(image_cache, f)

                return img

        return ""

    except:
        return ""

# ================= GLOBAL SEARCH (FIXED TO USE COMBINED SHEET) =================
def search_all_animals(animal):
    animal = animal.lower().strip()

    filtered = all_animals_df[
        (all_animals_df["animal_type"] == animal) |
        (all_animals_df["animal_name"].str.contains(animal, case=False, na=False))
    ]

    unique = filtered.drop_duplicates(subset=["animal_name"])

    results = []

    for _, row in unique.iterrows():
        results.append({
            "name": row["animal_name"],
            "scientific_name": row["scientific_name"],
            "location": row["habitat_location"],
            "status": row["status"],
            "image": get_image_from_wiki(row["animal_name"])
        })

    return results

# ================= ROOT =================
@app.get("/")
def root():
    return {"message": "API running"}

# ================= HISTORY =================
@app.post("/history")
@app.post("/history")
def add_history(animal: str, source: str = "detection"):
    entry = {
        "name": animal,
        "timestamp": datetime.now().isoformat(),
        "source": source
    }

    global history_db
    history_db = [h for h in history_db if h["name"] != animal]
    history_db.insert(0, entry)

    return {"message": "Added to history", "data": entry}


@app.get("/history")
def get_history():
    return history_db


# ================= FAVOURITES =================
@app.post("/favourites")
def add_favourite(animal: str):
    if not any(f["name"] == animal for f in favourites_db):
        favourites_db.append({
            "name": animal,
            "added_at": datetime.now().isoformat()
        })

    return {"message": "Added to favourites"}


@app.get("/favourites")
def get_favourites():
    return favourites_db


# ================= QUIZ =================
import random

@app.get("/quiz")
def generate_quiz():
    animals = list(set(
        [h["name"] for h in history_db] +
        [f["name"] for f in favourites_db]
    ))

    random.shuffle(animals)
    selected = animals[:5]

    questions = []

    for animal in selected:
        questions.append({
            "question": f"What is the conservation status of {animal}?",
            "options": ["Endangered", "Vulnerable", "Extinct", "Least Concern"],
            "answer": "Endangered"
        })

    return questions

# ================= IMAGE =================
def predict_image(file):
    contents = file.file.read()
    img = image.load_img(BytesIO(contents), target_size=(224, 224))

    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)

    preds = image_model.predict(img_array)
    decoded = decode_predictions(preds, top=1)

    return clean_species(decoded[0][0][1])

@app.post("/identify-image")
async def identify_image(file: UploadFile = File(...)):
    species = predict_image(file)
    image_url = get_image_from_wiki(species)

    return {
        "species": species,
        "image": image_url,
        "results": search_all_animals(species)
    }

# ================= TEXT =================
@app.post("/identify-text")
def identify_text(data: TextInput):

    text = data.text.lower()

    if "roar" in text:
        species = "lion"
    elif "stripe" in text:
        species = "tiger"
    elif "trunk" in text:
        species = "elephant"
    elif "horn" in text:
        species = "rhino"
    else:
        species = text

    return {
        "species": species,
        "results": search_all_animals(species)
    }

# ================= VIDEO =================
def preprocess_frame(frame):
    frame = cv2.resize(frame, (224, 224))
    frame = preprocess_input(frame)
    return np.expand_dims(frame, axis=0)

def extract_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if count % 60 == 0:
            frames.append(frame)

        count += 1

    cap.release()
    return frames[:5]

def predict_frame(frame):
    processed = preprocess_frame(frame)
    preds = image_model.predict(processed)
    decoded = decode_predictions(preds, top=1)
    return decoded[0][0][1]

@app.post("/identify-video")
async def identify_video(file: UploadFile = File(...)):

    temp_path = "temp_video.mp4"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    frames = extract_frames(temp_path)
    results = []

    for frame in frames:
        label = clean_species(predict_frame(frame))
        results.append(label)

    final = Counter(results).most_common(1)[0][0]

    os.remove(temp_path)

    return {
        "species": final,
        "results": search_all_animals(final)
    }

# ================= AUDIO =================
def load_audio(file_path):
    waveform, sr = librosa.load(file_path, sr=16000)
    return waveform

def predict_audio(file_path):
    waveform = load_audio(file_path)
    scores, _, _ = yamnet_model(waveform)
    return scores.numpy().mean(axis=0).argmax()

def map_audio_to_species(class_index):
    if class_index in range(0, 50):
        return "lion"
    elif class_index in range(50, 150):
        return "tiger"
    elif class_index in range(150, 300):
        return "elephant"
    else:
        return "animal"

@app.post("/identify-audio")
async def identify_audio(file: UploadFile = File(...)):

    temp_path = "temp_audio.wav"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        species = map_audio_to_species(predict_audio(temp_path))
    except:
        species = "unknown"

    os.remove(temp_path)

    return {
        "species": species,
        "results": search_all_animals(species)
    }

# ================= EXPLORE FLOW =================
@app.get("/animal/{region}/{category}/{state}/{animal}")
def get_animals(region: str, category: str, state: str, animal: str):

    key = f"{region}_{category}"

    if key not in dataframes:
        return []

    df = dataframes[key]

    state = state.lower().strip()
    animal = animal.lower().strip()

    results = df[
        (df["state"] == state) &
        (df["animal_type"] == animal)
    ]

    return [{
        "name": r["animal_name"],
        "scientific_name": r["scientific_name"],
        "location": r["habitat_location"],
        "status": r["status"],
        "image": get_image_from_wiki(r["animal_name"])
    } for _, r in results.iterrows()]

# ================= SEARCH =================
@app.get("/search/{animal}")
def global_search(animal: str):
    return search_all_animals(animal)

# ================= COMMON ANALYSIS BUILDER =================
def build_response(row):

    populations = [
        int(row["population_2014"]),
        int(row["population_2016"]),
        int(row["population_2018"]),
        int(row["population_2020"]),
        int(row["population_2022"]),
        int(row["population_2024"]),
    ]

    years = np.array([2014, 2016, 2018, 2020, 2022, 2024]).reshape(-1, 1)

    model = LinearRegression()
    model.fit(years, populations)

    future_years = np.array([[2026], [2028]])
    preds = model.predict(future_years)

    predictions = [
        {"year": 2026, "population": int(preds[0])},
        {"year": 2028, "population": int(preds[1])}
    ]

    slope = model.coef_[0]

    if slope > 0:
        trend = "Increasing"
    elif slope < 0:
        trend = "Declining"
    else:
        trend = "Stable"

    latest = populations[-1]

    if latest < 250:
        risk = "Critical"
    elif latest < 2500:
        risk = "Endangered"
    elif latest < 10000:
        risk = "Vulnerable"
    else:
        risk = "Stable"

    image_url = get_image_from_wiki(row["animal_name"])

    return {
        "species": row["animal_name"],
        "scientific_name": row["scientific_name"],
        "state": row["state"],
        "image": image_url,
        "population_history": populations,
        "predictions": predictions,
        "trend": trend,
        "risk_level": risk
    }


@app.get("/analysis/{region}/{category}/{state}/{animal}")
def species_analysis(region: str, category: str, state: str, animal: str):

    key = f"{region}_{category}"

    if key not in dataframes:
        return {"error": "Invalid dataset"}

    df = dataframes[key]

    state = state.lower().strip()
    animal = animal.lower().strip()

    result = df[
    (df["state"].str.lower() == state) &
    (df["animal_name"].str.lower().str.contains(animal))
]

    if result.empty:
        return {"error": "Species not found"}

    row = result.iloc[0]

    # ---------------------------
    # 📊 POPULATION DATA
    # ---------------------------
    populations = [
        int(row["population_2014"]),
        int(row["population_2016"]),
        int(row["population_2018"]),
        int(row["population_2020"]),
        int(row["population_2022"]),
        int(row["population_2024"]),
    ]

    years = np.array([2014, 2016, 2018, 2020, 2022, 2024]).reshape(-1, 1)

    # ---------------------------
    # 🤖 ML MODEL
    # ---------------------------
    model = LinearRegression()
    model.fit(years, populations)

    future_years = np.array([[2026], [2028]])
    preds = model.predict(future_years)

    predictions = [
        {"year": 2026, "population": int(preds[0])},
        {"year": 2028, "population": int(preds[1])}
    ]

    # ---------------------------
    # 📈 TREND
    # ---------------------------
    slope = model.coef_[0]

    if slope > 0:
        trend = "Increasing"
    elif slope < 0:
        trend = "Declining"
    else:
        trend = "Stable"

    # ---------------------------
    # ⚠️ RISK
    # ---------------------------
    latest = populations[-1]

    if latest < 250:
        risk = "Critical"
    elif latest < 2500:
        risk = "Endangered"
    elif latest < 10000:
        risk = "Vulnerable"
    else:
        risk = "Stable"

    # ---------------------------
    # 🖼 IMAGE
    # ---------------------------
    image_url = get_image_from_wiki(row["animal_name"])

    return {
        "species": row["animal_name"],
        "scientific_name": row["scientific_name"],
        "state": row["state"],
        "image": image_url,

        "population_history": [
            {"year": 2014, "population": populations[0]},
            {"year": 2016, "population": populations[1]},
            {"year": 2018, "population": populations[2]},
            {"year": 2020, "population": populations[3]},
            {"year": 2022, "population": populations[4]},
            {"year": 2024, "population": populations[5]},
        ],

        "predictions": predictions,
        "trend": trend,
        "risk_level": risk
    }

# ================= DETECTION FLOW =================

@app.get("/detection/{animal}")
def detection_default(animal: str):

    animal = animal.lower().strip()

    df = all_animals_df

    # 🔥 FIX: use contains (important)
    result = df[df["animal_name"].str.lower().str.contains(animal)]

    if result.empty:
        return {"error": "Species not found"}

    row = result.iloc[0]

    return build_response(row)


@app.get("/detection/{animal}/{regionType}/{location}")
def detection_filtered(animal: str, regionType: str, location: str):

    animal = animal.lower().strip()
    regionType = regionType.lower().strip()
    location = location.lower().strip()

    df = all_animals_df

    # 🔥 FIX: use contains
    filtered = df[df["animal_name"].str.lower().str.contains(animal)]

    if filtered.empty:
        return {"error": "No data found"}

    # =============================
    # 🇮🇳 INDIA → STATE FILTER
    # =============================
    if regionType == "india":

        result = filtered[
            filtered["state"].str.lower() == location
        ]

    # =============================
    # 🌏 PAN ASIA → COUNTRY FILTER
    # =============================
    elif regionType == "panasia":

        result = filtered[
            filtered["state"]
            .str.lower()
            .map(state_to_country)
            == location
        ]

    # =============================
    # 🌍 GLOBAL → CONTINENT FILTER
    # =============================
    elif regionType == "global":

        result = filtered[
            filtered["state"]
            .str.lower()
            .map(state_to_country)
            .map(country_to_continent)
            == location
        ]

    else:
        return {"error": "Invalid region type"}

    if result.empty:
        return {"error": "No data found"}

    row = result.iloc[0]

    return build_response(row)


# ================= DROPDOWN LOCATIONS =================

@app.get("/detection-locations/{animal}/{regionType}")
def get_locations(animal: str, regionType: str):

    animal = animal.lower().strip()
    regionType = regionType.lower().strip()

    df = all_animals_df

    # 🔍 filter animal
    filtered = df[df["animal_name"].str.lower().str.contains(animal)]

    if filtered.empty:
        return []

    # 📍 get states
    states = (
        filtered["state"]
        .dropna()
        .str.lower()
        .unique()
        .tolist()
    )

    # 🇮🇳 INDIA → STATES
    if regionType == "india":
        return sorted(states)

    # 🌏 PAN ASIA → COUNTRIES
    elif regionType == "panasia":

        countries = {
            state_to_country[s]
            for s in states
            if s in state_to_country
        }

        return sorted(list(countries))

    # 🌍 GLOBAL → CONTINENTS
    elif regionType == "global":

        continents = {
            country_to_continent[state_to_country[s]]
            for s in states
            if s in state_to_country and state_to_country[s] in country_to_continent
        }

        return sorted(list(continents))

    return []
# ================= ADMIN APIs (FINAL FIXED) =================

from fastapi import Body, HTTPException

# ✅ GET ALL SPECIES
@app.get("/admin/species")
def get_all_species():
    return all_animals_df.to_dict(orient="records")


# ✅ GET SHEET (SAFE)
@app.get("/admin/sheet/{region}/{category}")
def get_sheet(region: str, category: str):

    key = f"{region.lower().strip()}_{category.lower().strip()}"

    if key not in dataframes:
        print("❌ Sheet not found:", key)
        return []   # ✅ NEVER crash frontend

    df = dataframes[key]

    return df.fillna("").to_dict(orient="records")  # ✅ prevent null crash


# ✅ UPLOAD FULL EXCEL (SAFE RELOAD)
@app.post("/admin/upload-excel")
async def upload_excel(file: UploadFile = File(...)):

    file_path = os.path.join(BASE_DIR, "data", "processed", "animals.xlsx")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        global excel_data, all_animals_df, dataframes

        excel_data = pd.read_excel(file_path, sheet_name=None)

        # ✅ combined
        all_animals_df = excel_data["all_animals"].copy()
        all_animals_df.columns = all_animals_df.columns.str.strip()
        all_animals_df["animal_name"] = all_animals_df["animal_name"].astype(str).str.strip().str.lower()
        all_animals_df["animal_type"] = all_animals_df["animal_type"].astype(str).str.strip().str.lower()

        # ✅ sheets
        dataframes = {}

        for sheet_name, df in excel_data.items():
            df.columns = df.columns.str.strip()
            df["state"] = df["state"].astype(str).str.strip().str.lower()
            df["animal_type"] = df["animal_type"].astype(str).str.strip().str.lower()

            dataframes[sheet_name.lower().strip()] = df

        return {"message": "Excel replaced successfully ✅"}

    except Exception as e:
        print("❌ Upload Excel Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ✅ UPLOAD TO SHEET (SAFE)
@app.post("/admin/upload/{region}/{category}")
async def upload_to_sheet(region: str, category: str, file: UploadFile = File(...)):

    key = f"{region.lower().strip()}_{category.lower().strip()}"

    if key not in dataframes:
        raise HTTPException(status_code=400, detail="Invalid sheet")

    try:
        df_new = pd.read_excel(file.file)

        df_new.columns = df_new.columns.str.strip()
        df_new["state"] = df_new["state"].astype(str).str.strip().str.lower()
        df_new["animal_type"] = df_new["animal_type"].astype(str).str.strip().str.lower()

        dataframes[key] = pd.concat([dataframes[key], df_new], ignore_index=True)

        save_all_sheets()

        return {"message": "Uploaded successfully ✅"}

    except Exception as e:
        print("❌ Upload Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ✅ DELETE (SAFE)
@app.delete("/admin/delete/{region}/{category}/{animal}")
def delete_species(region: str, category: str, animal: str):

    key = f"{region.lower().strip()}_{category.lower().strip()}"

    if key not in dataframes:
        raise HTTPException(status_code=400, detail="Invalid sheet")

    try:
        df = dataframes[key]

        print("Deleting:", animal)
        print("Before:", len(df))

        # 🔥 FLEXIBLE MATCH (better than exact eq)
        df = df[
            ~df["animal_name"]
            .astype(str)
            .str.lower()
            .str.strip()
            .str.contains(animal.lower().strip())
        ]

        print("After:", len(df))

        dataframes[key] = df
        save_all_sheets()

        return {"message": f"{animal} deleted successfully ✅"}

    except Exception as e:
        print("❌ Delete Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# ✅ UPDATE (SAFE + FLEXIBLE)
@app.put("/admin/update/{region}/{category}/{animal}")
def update_species(region: str, category: str, animal: str, updated_data: dict = Body(...)):

    key = f"{region.lower().strip()}_{category.lower().strip()}"

    if key not in dataframes:
        raise HTTPException(status_code=400, detail="Invalid sheet")

    try:
        df = dataframes[key]

        mask = df["animal_name"].astype(str).str.lower().str.strip() == animal.lower().strip()

        if not mask.any():
            raise HTTPException(status_code=404, detail="Animal not found")

        for col, value in updated_data.items():
            if col in df.columns:
                df.loc[mask, col] = value

        dataframes[key] = df
        save_all_sheets()

        return {"message": "Updated successfully ✅"}

    except Exception as e:
        print("❌ Update Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/admin/add/{region}/{category}")
def add_species(region: str, category: str, data: dict):

    file_path = os.path.join(BASE_DIR, "data", "processed", "animals.xlsx")
    sheet_name = f"{region.lower().strip()}_{category.lower().strip()}"

    df = pd.read_excel(file_path, sheet_name=sheet_name)

    print("Excel Columns:", df.columns.tolist())

    new_row = {
        "animal_name": data.get("animal_name"),
        "animal_type": data.get("animal_type"),
        "scientific_name": data.get("scientific_name"),
        "state": data.get("state"),
        "habitat_location": data.get("habitat_location"),

        "population_2014": data.get("population_2014"),
        "population_2016": data.get("population_2016"),
        "population_2018": data.get("population_2018"),
        "population_2020": data.get("population_2020"),
        "population_2022": data.get("population_2022"),
        "population_2024": data.get("population_2024"),

        "status": data.get("status")
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    return {"message": "Added successfully"}
# ✅ SAVE FUNCTION (SAFE WRITE)
def save_all_sheets():
    file_path = os.path.join(BASE_DIR, "data", "processed", "animals.xlsx")

    try:
        with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
            for sheet_name, df in dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    except Exception as e:
        print("❌ Save Error:", e)



from bson import ObjectId

from bson import ObjectId
from fastapi import HTTPException

@app.put("/update-profile")
def update_profile(data: dict = Body(...)):

    try:
        print("Incoming data:", data)   # 🔥 DEBUG

        user_id = data.get("_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="User ID missing")

        # 🔥 SAFE ObjectId conversion
        try:
            user_id = ObjectId(user_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID")

        result = users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "name": data.get("name"),
                    "email": data.get("email")
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "Profile updated successfully"}

    except Exception as e:
        print("❌ Update error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
import bcrypt

@app.post("/login")
def login(data: dict = Body(...)):
    
    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid password")

    return {
        "user": {
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    }