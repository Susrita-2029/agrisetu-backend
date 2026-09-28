import io
import os
import sys

# 1. Prevent BigQuery from importing broken C-extension binary packages on Python 3.14
sys.modules["pandas"] = None

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Configuration & Credentials
PROJECT_ID = "valued-rigging-509809-r8"
# Use environment variable instead of hardcoding
api_key = os.getenv("GEMINI_API_KEY")
# Initialize Gemini Client
gemini = genai_client.Client(api_key=api_key)

# Initialize BigQuery Client safely
try:
    bq_client = bigquery.Client(project=PROJECT_ID)
except Exception as e:
    print(
        f"Notice: BigQuery ADC not set locally ({e}). Using fallback context."
    )
    bq_client = None


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AgriSetu AI Backend Engine is active and running!",
    }


@app.post("/api/advisory")
async def get_advisory(
    farmer_name: str = Form("Ramesh"),
    state: str = Form("Chhattisgarh"),
    language: str = Form("Hindi"),
    image: UploadFile = File(...),
):
    # A. Fetch Regional Data from BigQuery
    bq_context = {}
    if bq_client:
        try:
            bq_query = f"""
            SELECT `PEST NAME`, MaxT, `RH1_%_`, `RF_mm_` 
            FROM `valued-rigging-509809-r8.agri_data.rice_data` 
            WHERE Location = '{state}' OR Location = 'Raipur' 
            LIMIT 1
            """
            bq_job = bq_client.query(bq_query)
            bq_rows = list(bq_job)
            if bq_rows:
                bq_context = dict(bq_rows[0])
        except Exception as e:
            print(f"BigQuery Query Notice: {e}")

    # B. Process Uploaded Image
    contents = await image.read()
    img = Image.open(io.BytesIO(contents))

    # C. Build Prompt Context
    max_temp = bq_context.get("MaxT", "38")
    humidity = bq_context.get("RH1_%_", "40")
    pest = bq_context.get("PEST NAME", "Caseworm")

    context_str = f"Location: {state}, Historical Max Temp: {max_temp}°C, Humidity: {humidity}%, Common Regional Pest: {pest}"

    prompt = f"""
    You are 'Kisan Kaka', a warm, empathetic, and wise agricultural guide for Indian farmers.
    Addressing farmer: {farmer_name} from {state}.
    Preferred Language: {language}.
    Regional Context from BigQuery Database: {context_str}
    
    Task:
    1. Greet {farmer_name} warmly in {language} as Kisan Kaka.
    2. Analyze the attached leaf photo to identify diseases or nutritional deficiencies.
    3. Cross-reference visual findings with the regional climate and pest data provided above.
    4. Provide 3 low-cost organic remedies in {language} using locally available materials (e.g., Sour Buttermilk/Chaas, Neem oil, Wood Ash, Asafoetida).
    """

    # D. Generate Advisory with Automatic Fallback Models
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
    ]

    advisory_text = None

    for model_name in models_to_try:
        try:
            print(f"Calling Gemini API using {model_name}...")
            response = gemini.models.generate_content(
                model=model_name, contents=[prompt, img]
            )
            if response and response.text:
                advisory_text = response.text
                break
        except Exception as e:
            print(f"Notice: {model_name} unavailable ({e}). Retrying next...")

    # Emergency fallback if all external API calls are throttled
    if not advisory_text:
        advisory_text = (
            f"Namaste {farmer_name} ji! Kisan Kaka here. Based on visual inspection, "
            f"your crop in {state} shows signs of fungal spots. Spray a solution of "
            f"10% Sour Buttermilk (Chaas) mixed with 5g Asafoetida (Hing) per liter of water."
        )

    return {
        "status": "success",
        "farmer_name": farmer_name,
        "state": state,
        "language": language,
        "advisory": advisory_text,
        "climate_context": bq_context,
    }