
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)


def generate_health_remarks(patient):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return "AI service unavailable: Gemini API key is not configured."

    patient_details = {
        "glucose": patient.get("glucose"),
        "haemoglobin": patient.get("haemoglobin"),
        "cholesterol": patient.get("cholesterol"),
    }

    instructions = (
        "You are an educational health-risk assessment assistant for a "
        "student project. Assess the supplied glucose, haemoglobin, and "
        "cholesterol measurements for possible health concerns. Do not merely "
        "define the measurements. Write 4 to 6 short sentences in plain text. "
        "Identify any measurement that may warrant medical review and describe "
        "the possible concern cautiously. Glucose interpretation depends on "
        "whether the test was fasting, random, or otherwise, and on its units. "
        "Haemoglobin and cholesterol interpretation also depends on units, "
        "patient context, and laboratory reference ranges. Do not assume missing "
        "units or test conditions, invent a disease, give a numerical risk "
        "probability, or claim a confirmed diagnosis. If the available details "
        "are insufficient to assess a particular risk, say so clearly. Do not "
        "recommend medicines or treatment. End by advising consultation with a "
        "qualified healthcare professional. State that the remarks are a "
        "preliminary AI assessment, not a medical diagnosis."
    )

    try:
        response = requests.post(
            API_URL,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "system_instruction": {
                    "parts": [{"text": instructions}]
                },
                "contents": [{
                    "parts": [{
                        "text": (
                            "Assess these patient-entered measurements and "
                            "provide possible health-risk remarks for the "
                            "application: "
                            f"{patient_details}. "
                            "Focus on possible concerns, not just definitions."
                        )
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 250,
                },
            },
            timeout=(10, 45),
        )

        if not response.ok:
            print("Gemini HTTP status:", response.status_code)
            print("Gemini API error:", response.text[:2000])
            response.raise_for_status()

        data = response.json()

        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if part.get("text"):
                    return part["text"].strip()

        print("Gemini returned no text:", str(data)[:1000])
        return "No AI assessment was returned. Please try again."

    except requests.Timeout:
        print("Gemini request timed out.")
        return "AI service timed out. Please try again."

    except requests.RequestException as error:
        print("Gemini API request failed:", str(error))
        return "AI service unavailable. Check the VS Code terminal."

    except (ValueError, KeyError, TypeError) as error:
        print("Gemini response processing error:", str(error))
        return "Unable to process the AI response."
