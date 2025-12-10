# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import urllib.parse
import random
import difflib
import os

app = FastAPI(title="SuperAgent Backend")

# Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount the frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class Query(BaseModel):
    text: str

# --- keywords & simple typo-correction ---
GREETING_KEYWORDS = ["hey","hi","hello","wassup","good morning","good evening"]
INTENT_KEYWORDS = {
    "restaurant": ["restaurant","restaurants","food","dine","cafe","eat","biriyani","pizza","chicken","burger","restaurant near"],
    "hotel": ["hotel","hotels","room","stay","lodging","resort"],
    "flight": ["flight","flights","airline","plane","ticket","fly"],
    "train": ["train","trains","railway","irctc","pnr","ticket"],
    "event": ["cricket","match","movie","concert","show","t20i","odi","football","event","ticket"],
    "product": ["buy","purchase","order","shop","amazon","flipkart","ebay","product","shampoo","dress","laptop"],
    "taxi": ["taxi","cab","ola","uber","rapido","ride"],
    "temple": ["temple","mandir","church","mosque","gurudwara","place of worship","near me","nearby"]
}

PLATFORM_TEMPLATES = {
    "restaurants": [
        ("Zomato", "https://www.zomato.com/search?query={q}"),
        ("Swiggy", "https://www.swiggy.com/search?q={q}"),
        ("Google Maps", "https://www.google.com/maps/search/{q}")
    ],
    "hotels": [
        ("Booking.com", "https://www.booking.com/searchresults.html?ss={q}"),
        ("Agoda", "https://www.agoda.com/search?city={q}")
    ],
    "flights": [
        ("MakeMyTrip", "https://www.makemytrip.com/flights/?q={q}"),
        ("Skyscanner", "https://www.skyscanner.co.in/transport/flights?query={q}")
    ],
    "trains": [
        ("IRCTC", "https://www.irctc.co.in/nget/train-search"),
        ("Google", "https://www.google.com/search?q={q}+train+tickets")
    ],
    "events": [
        ("BookMyShow", "https://in.bookmyshow.com/explore/search?q={q}"),
        ("TicketMaster", "https://www.ticketmaster.com/search?q={q}")
    ],
    "products": [
        ("Amazon", "https://www.amazon.in/s?k={q}"),
        ("Flipkart", "https://www.flipkart.com/search?q={q}"),
        ("eBay", "https://www.ebay.in/sch/i.html?_nkw={q}")
    ],
    "taxi": [
        ("Ola", "https://www.olacabs.com/search/?q={q}"),
        ("Uber", "https://www.uber.com/global/en/search/?q={q}"),
        ("Google", "https://www.google.com/search?q={q}+taxi")
    ],
    "temple": [
        ("Google Maps", "https://www.google.com/maps/search/{q}")
    ]
}

ALL_KEYWORDS = [w for kws in INTENT_KEYWORDS.values() for w in kws]

def correct_typos(text: str) -> str:
    words = text.split()
    corrected = []
    for w in words:
        cand = difflib.get_close_matches(w, ALL_KEYWORDS, n=1, cutoff=0.8)
        corrected.append(cand[0] if cand else w)
    return " ".join(corrected)

def detect_intent(text: str):
    t = text.lower().strip()
    # greetings first
    for g in GREETING_KEYWORDS:
        if t == g or t.startswith(g) or (" " + g + " ") in (" " + t + " "):
            return "greeting", None

    t_corr = correct_typos(t)
    scores = {}
    for intent, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if kw in t_corr:
                scores[intent] = scores.get(intent, 0) + 1

    if scores:
        intent = max(scores, key=lambda k: scores[k])
        if intent == "restaurant": return "restaurant", "restaurants"
        if intent == "hotel": return "hotel", "hotels"
        if intent == "flight": return "flight", "flights"
        if intent == "train": return "train", "trains"
        if intent == "event": return "event", "events"
        if intent == "product": return "product", "products"
        if intent == "taxi": return "taxi", "taxi"
        if intent == "temple": return "temple", "temple"

    for family, templates in PLATFORM_TEMPLATES.items():
        for name, _ in templates:
            if name.lower() in t:
                return family.rstrip('s'), family
    return "unknown", None

def build_results_for_family(query: str, family_key: str):
    q = urllib.parse.quote_plus(query)
    items = []
    templates = PLATFORM_TEMPLATES.get(family_key, [])
    for idx, (plat_name, url_templ) in enumerate(templates):
        item = {
            "id": f"{family_key}-{idx+1}",
            "type": family_key.rstrip('s'),
            "name": f"{query.title()} — {plat_name} results",
            "image": f"https://placehold.co/400x250?text={urllib.parse.quote_plus(plat_name)}",
            "platform": plat_name,
            "platform_url": url_templ.format(q=q)
        }
        if family_key == "restaurants":
            item.update({"timing": "Check on platform", "district": "", "dishes": []})
        if family_key == "hotels":
            item.update({"price": "Check on platform", "location": ""})
        if family_key == "flights":
            item.update({"duration": "Varies", "price": "Check platform"})
        if family_key == "trains":
            item.update({"duration": "Varies", "price": "Check platform"})
        if family_key == "events":
            item.update({"date": "Check platform", "venue": "Check platform"})
        if family_key == "products":
            item.update({"price": "Check platform"})
        if family_key == "taxi":
            item.update({"price": "Check platform", "duration": "N/A"})
        if family_key == "temple":
            item.update({"location": "Nearby", "distance": "Varies"})
        items.append(item)
    return items

# --- API routes ---
@app.get("/")
def root():
    return {"status":"ok","message":"SuperAgent backend running"}

@app.post("/ai")
def process_query(q: Query):
    text = (q.text or "").strip()
    if not text:
        return {"reply":"Please type a query.", "has_details": False, "details": []}

    intent, family = detect_intent(text)

    if intent == "greeting":
        if "sanjay" in text.lower():
            return {"reply":"Hello Sanjay! How can I assist you today?", "has_details": False, "details": []}
        return {"reply":"Hello! How can I assist you today?", "has_details": False, "details": []}

    if intent == "unknown":
        qenc = urllib.parse.quote_plus(text)
        fallback_details = [
            {"id":"fallback-1","type":"web","name":f"Search Google for '{text}'",
             "image":"https://placehold.co/400x250?text=Google",
             "platform":"Google","platform_url":f"https://www.google.com/search?q={qenc}"}
        ]
        return {"reply":f"Sorry, I couldn't detect a specific intent. I searched web for '{text}'.",
                "has_details": True, "details": fallback_details}

    details = build_results_for_family(text, family)

    reply_map = {
        "restaurants":"Here are search results for restaurants matching your query.",
        "hotels":"Here are hotels matching your query.",
        "flights":"Here are flight search pages for your query.",
        "trains":"Train search pages for your query.",
        "events":"Events & tickets search results.",
        "products":"Product search results across marketplaces.",
        "taxi":"Taxi / ride options and search pages.",
        "temple":"Places of worship (open in Google Maps)."
    }
    reply = reply_map.get(family, f"Here are results for '{text}'")
    return {"reply": reply, "has_details": bool(details), "details": details}
