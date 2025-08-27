const {
    default: makeWASocket,
    makeCacheableSignalKeyStore,
    useMultiFileAuthState,
    DisconnectReason
} = require("@whiskeysockets/baileys");

const { Boom } = require("@hapi/boom");
const pino = require("pino");
const { exec } = require("child_process");
const fs = require("fs");
const qrcode = require("qrcode-terminal");

const logger = pino().child({ level: "silent" });

// This is a simpler script that no longer manages session state or complex message types.
// It simply passes the message and sender to the Python backend.

const runPythonScript = (text, sender, sock, senderName) => {
    // Escape double quotes in the text to prevent issues in the shell command
    const escapedText = text.replace(/"/g, '\\"');
    
    // Check if the script is running on Windows
    const isWindows = process.platform === 'win32';
    
    // Use 'python' instead of 'python3' for Windows for better compatibility
    const pythonCommand = isWindows ? 'python' : 'python3';
    
    // Pass the sender's name as a third argument to the Python script
    exec(`${pythonCommand} ai.py "${escapedText}" "${sender}" "${senderName}"`, (error, stdout, stderr) => {
        if (error) {
            console.error("❌ Python Error:", error.message);
            return;
        }

        const reply = stdout.trim();
        if (!reply) {
            console.log("⚠️ No reply returned.");
            return;
        }
        
        // This version no longer handles complex JSON replies.
        // It assumes all responses from Python are plain text.
        sock.sendMessage(sender, { text: reply });
        console.log(`📤 To ${sender}: ${reply}`);
    });
};

async function startSock() {
    const { state, saveCreds } = await useMultiFileAuthState(
        "./baileys_auth_info",
    );
    
    const version = [6, 7, 18];
    console.log(`Using baileys version ${version.join('.')}`);

    const sock = makeWASocket({
        version,
        logger: pino({ level: "silent" }),
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' }).child({ level: 'silent' })),
        },
        browser: ["Ubuntu", "Chrome", "110.0.0.0"],
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (connection === "close") {
            let reason = new Boom(lastDisconnect?.error)?.output?.statusCode;
            if (
                reason === DisconnectReason.badSession ||
                reason === DisconnectReason.loggedOut
            ) {
                console.log("Logged out. Please scan the QR code again.");
                startSock();
            } else {
                console.log("Connection closed. Reconnecting...");
                startSock();
            }
        } else if (qr) {
            qrcode.generate(qr, { small: true });
            console.log("Scan the QR code above to connect your WhatsApp bot.");
        } else if (connection === "open") {
            console.log("✅ WhatsApp bot is ready and running!");
        }
    });

    sock.ev.on("messages.upsert", async ({ messages, type }) => {
        const msg = messages[0];
        if (!msg.message || msg.key.fromMe) return;

        const sender = msg.key.remoteJid;
        // Get the sender's name from the message key, defaulting to the number if not available
        const senderName = msg.pushName || sender.split('@')[0];
        const text =
            msg.message.conversation ||
            msg.message.extendedTextMessage?.text ||
            msg.message.imageMessage?.caption ||
            msg.message.videoMessage?.caption;

        if (!text) return;

        console.log(`📥 From ${sender}: ${text}`);
        
        // Pass the sender's name to the Python script
        runPythonScript(text, sender, sock, senderName);
    });
}

startSock();