from flask import Flask, request, jsonify
from Backend.Chatbot import ChatBot # Make sure this path is correct: Backend/Chatbot.py
import uuid
import os # Import os for directory check

app = Flask(__name__)

# --- Ensure Data directory exists (same as in Chatbot.py) ---
if not os.path.exists("Data"):
    os.makedirs("Data")

@app.route('/')
def home():
    """Basic route to confirm the server is running."""
    return "Your AI Chatbot API is running! Access the /chat endpoint via POST."

@app.route('/chat', methods=['POST'])
def chat():
    """
    API endpoint for handling chat messages.
    Expects a JSON payload with 'message' and optionally 'user_id'.
    """
    data = request.get_json()

    user_message = data.get('message')
    user_id = data.get('user_id') # Get user_id from the frontend

    if not user_message:
        return jsonify({"response": "Error: 'message' field is required.", "user_id": user_id}), 400

    if not user_id:
        # If no user_id is provided by the frontend, generate a new one for a guest session.
        # In a real application, you'd manage this with user authentication or persistent sessions.
        user_id = str(uuid.uuid4())
        print(f"New guest session initiated: {user_id}")

    # Construct a sender_number compatible with your ChatBot logic
    # Using 'web_user_' prefix to distinguish from WhatsApp users
    sender_for_chatbot = f"web_user_{user_id}@website.com"

    try:
        # Call your core AI logic
        ai_response = ChatBot(user_message, sender_for_chatbot)
        return jsonify({"response": ai_response, "user_id": user_id})
    except Exception as e:
        print(f"Error processing chat request: {e}")
        return jsonify({"response": "I'm sorry, something went wrong on my end.", "user_id": user_id}), 500

if __name__ == '__main__':
    # When deployed to Railway, Railway will usually set the PORT environment variable.
    # For local testing, you can run it on port 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
