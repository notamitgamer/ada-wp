import sys

# --- ADD THESE TWO LINES ---
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
# ---------------------------

from Backend.Chatbot import ChatBot

query = sys.argv[1]
sender = sys.argv[2]
# Get the new sender name argument
sender_name = sys.argv[3]

try:
    # We no longer pass sender name or session info
    response = ChatBot(query, sender, sender_name).strip()
except Exception as e:
    response = f"❌ Python Error: {e}"

print(response)