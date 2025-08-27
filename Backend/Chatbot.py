import json, requests, datetime, re
from groq import Groq
import os
import pytz
import google.generativeai as genai
import time

# ─── Configuration ─────────────────────────────────────────────────────────────
USERNAME = "Amit Dutta"
ASSISTANT_NAME = "Ada"
USER_INFO = "I am Amit Dutta, a student who just completed high school this year from New Barrackpore Colony Boys High School, New Barrackpore. My current plan is to pursue BSc Hons in Computer Science. I live in Madhyamgram, North 24 Parganas. I was born on 05/07/2006, which makes me 19 years old. I tend to talk more than me!"

# --- AI API Keys ---
GEMINI_API = 'AIzaSyAcoWjo1JsFiAPYAJs8xFjW0LhPeSq-NZk'

# --- Search API Keys ---
SERPER_KEY = '07adc673c274ea9087c5b0bb3d24e72006999f4d'
YOUTUBE_KEY = 'AIzaSyDXwFWA8rz4XkYjw8O0q8gdeB9jkZrOl7w'

# --- AI Clients ---
# client_groq = Groq(api_key=GROQ_API)
genai.configure(api_key=GEMINI_API)
client_gemini = genai.GenerativeModel('gemini-1.5-flash')

# Define the Indian Standard Timezone
IST = pytz.timezone('Asia/Kolkata')

# ─── Utility Functions ─────────────────────────────────────────────────────────

def RealtimeInformation():
    now_utc = datetime.datetime.now(pytz.utc)
    now_ist = now_utc.astimezone(IST)
    return f"The current date and time is {now_ist.strftime('%A, %d %B %Y')} {now_ist.strftime('%H:%M:%S')} IST"

def load_guest_names():
    try: return json.load(open("Data/GuestNames.json"))
    except (FileNotFoundError, json.JSONDecodeError): return {}

def save_guest_names(data):
    json.dump(data, open("Data/GuestNames.json", "w"), indent=4)

def is_first_time_user(sender_number, sender_name):
    guest_names = load_guest_names()
    is_first_time = sender_number not in guest_names

    if is_first_time:
        guest_names[sender_number] = {
            "name": sender_name,
            "last_message_time": datetime.datetime.now(IST).isoformat()
        }
        save_guest_names(guest_names)
        return True, sender_name
    else:
        user_data = guest_names[sender_number]
        last_message_time_str = user_data.get("last_message_time")
        
        # Check if the session has expired (1 hour timeout)
        if last_message_time_str:
            last_message_time = datetime.datetime.fromisoformat(last_message_time_str).astimezone(IST)
            time_difference = datetime.datetime.now(IST) - last_message_time
            if time_difference > datetime.timedelta(hours=1):
                # Session expired, return True for new session
                user_data["last_message_time"] = datetime.datetime.now(IST).isoformat()
                save_guest_names(guest_names)
                return True, user_data["name"]

        # Update timestamp for active session
        user_data["last_message_time"] = datetime.datetime.now(IST).isoformat()
        save_guest_names(guest_names)
        return False, user_data["name"]

# ─── Search Functions ──────────────────────────────────────────────────────────

def search_google(query):
    try:
        headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
        data = {"q": query}
        r = requests.post("https://google.serper.dev/search", headers=headers, json=data).json()
        if "organic" in r and r["organic"]:
            result = r["organic"][0]
            return f"{result['title']}\n{result['snippet']}\n🔗 {result['link']}"
        return "No result found."
    except Exception as e:
        print(f"Google search failed: {e}")
        return "Google search failed."

def search_youtube(query):
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={YOUTUBE_KEY}&type=video&maxResults=1"
        res = requests.get(url).json()
        if "items" in res and res["items"]:
            vid = res["items"][0]
            title = vid["snippet"]["title"]
            link = f"https://youtube.com/watch?v={vid['id']['videoId']}"
            return f"📺 {title}\n🔗 {link}"
        return "No YouTube video found."
    except Exception as e:
        print(f"YouTube search failed: {e}")
        return "YouTube search failed."

# ─── LLM Interaction Functions ──────────────────────────────────────────────────

# Removed call_groq function and Groq-related imports as per previous request.

def call_gemini(query):
    try:
        retries = 0
        while retries < 5:
            try:
                response = client_gemini.generate_content(query)
                if response.parts:
                    return response.text.strip()
                else:
                    return "Sorry, I couldn't generate a response. The API returned no content."
            except genai.types.generation_types.BlockedPromptException:
                return "I'm sorry, I cannot respond to that. The content is blocked."
            except Exception as e:
                retries += 1
                wait_time = (2 ** retries)
                print(f"Gemini API error: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        return "I'm sorry, I am unable to process your request at this time. Please try again later."
    except Exception as e:
        print(f"Gemini API error: {e}")
        return f"I'm sorry, I encountered an error while processing your request: {e}"

# ─── Main Chatbot Logic ────────────────────────────────────────────────────────

def ChatBot(Query, sender_number, sender_name):
    try:
        messages = json.load(open("Data/ChatLog.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        messages = []

    SystemChatBot_Gemini = f"""You are {ASSISTANT_NAME}, a powerful AI created by {USERNAME}. Your creator, {USERNAME}, has provided the following information about themselves: {USER_INFO}
Your primary goal is to provide accurate, clear, and helpful answers. You are capable of communicating in English, Hindi, and Bengali.
STRICT RULE: When the user speaks in English, Hindi, or Bengali, you MUST respond ENTIRELY in that specific language. Do NOT mix languages.
Example: If the user asks in Bengali, your WHOLE response must be in Bengali.
The 'RealtimeInformation' provided in a subsequent system message is the CURRENT DATE AND TIME in Indian Standard Time (IST). You MUST use this exact 'RealtimeInformation' to answer questions about the current date, time, or "now". Do NOT use any other source or perform any timezone conversions on it.
"""
    # ── First-Time User / New Session Greeting ──
    is_new_session, tracked_name = is_first_time_user(sender_number, sender_name)
    if is_new_session:
        return (f"Hello {tracked_name}! "
                "Sorry for the inconvenience, Amit is currently offline. "
                "I am Ada, his personal AI assistant. Please chat with me in English. "
                "I'm here to help with your questions!")

    lowered = Query.lower().strip()

    if lowered.startswith("search "):
        return search_google(Query.replace("search", "").strip())
    elif "youtube" in lowered:
        return search_youtube(Query.replace("youtube", "").strip())
    elif "what can you do" in lowered:
        return "I can answer general questions using my knowledge base, and I can perform web searches for information or find YouTube videos for you."
    else:
        gemini_prompt = f"Using this system information: {SystemChatBot_Gemini}\nThis realtime info: {RealtimeInformation()}\nThis chat history: {messages}.\nAnswer the user's question: {Query}"
        answer = call_gemini(gemini_prompt)

        messages.append({"role": "user", "content": Query})
        messages.append({"role": "assistant", "content": answer})
        json.dump(messages, open("Data/ChatLog.json", "w"), indent=4)
        return answer