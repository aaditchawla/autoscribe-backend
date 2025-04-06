from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import os
import subprocess
import openai
from dotenv import load_dotenv
import tempfile
from werkzeug.utils import secure_filename
import traceback
import socket
import time
import logging
from logging.handlers import RotatingFileHandler
from translate import translate_text
from pdf_generator import create_summary_pdf
import io
from email_handler import send_summary_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Add file handler for production logging
file_handler = RotatingFileHandler('logs/server.log', maxBytes=10240000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Load environment variables
logger.info("Loading environment variables...")
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
# Allow all origins and methods with more permissive CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
        "supports_credentials": True
    }
})

# Create a temp directory that persists between requests
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def extract_audio(input_path, output_path):
    """Extract audio using FFmpeg"""
    try:
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vn',
            '-acodec', 'libmp3lame',
            '-q:a', '2',
            '-y',
            output_path
        ]
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print(f"FFmpeg output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        raise Exception(f"Error extracting audio: {e.stderr}")

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper"""
    try:
        with open(audio_path, "rb") as audio_file:
            print(f"Transcribing file: {audio_path}")
            # Using the older OpenAI API format
            transcript_obj = openai.Audio.transcribe("whisper-1", audio_file)
            print(f"Transcription result: {transcript_obj}")
            return transcript_obj.text
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise Exception(f"Error transcribing audio: {str(e)}")

def generate_summary(transcript):
    """Generate summary using GPT-3.5"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates meeting summaries."},
                {"role": "user", "content": f"Please create a summary of this meeting transcript with bullet points for key decisions, action items, timeline, and budget:\n\n{transcript}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Summary generation error: {str(e)}")
        raise Exception(f"Error generating summary: {str(e)}")

def translate_text(text, target_language):
    """Translate text using GPT-3.5"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful translator. Translate the following text to {target_language}. Maintain the same formatting including markdown and bullet points."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Translation error: {str(e)}")
        raise Exception(f"Error translating text: {str(e)}")

def handle_options_request():
    """Handle CORS preflight requests"""
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

@app.route('/test', methods=['GET'])
def test():
    start_time = time.time()
    response = jsonify({
        "status": "ok", 
        "message": "Server is running",
        "local_ip": get_local_ip(),
        "response_time_ms": int((time.time() - start_time) * 1000)
    })
    return response

@app.route('/transcribe', methods=['POST', 'OPTIONS'])
def transcribe():
    start_time = time.time()
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
        
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        logger.info(f"Received file: {file.filename}")
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_path = os.path.join(UPLOAD_FOLDER, f"{filename}_audio.mp3")
        
        # Save uploaded file
        file.save(input_path)
        logger.info(f"Saved file to: {input_path}")
        
        try:
            # Step 1: Extract audio
            logger.info("Extracting audio...")
            extract_start = time.time()
            extract_audio(input_path, audio_path)
            logger.info(f"Audio extracted in {(time.time() - extract_start):.2f}s")
            
            # Step 2: Transcribe
            logger.info("Transcribing audio...")
            transcribe_start = time.time()
            transcript = transcribe_audio(audio_path)
            logger.info(f"Transcription completed in {(time.time() - transcribe_start):.2f}s")
            
            # Step 3: Generate summary
            logger.info("Generating summary...")
            summary_start = time.time()
            summary = generate_summary(transcript)
            logger.info(f"Summary generated in {(time.time() - summary_start):.2f}s")
            
            # Step 4: Translate summary
            logger.info("Translating summary...")
            translate_start = time.time()
            translated_summary = translate_text(summary, "Spanish")
            logger.info(f"Translation completed in {(time.time() - translate_start):.2f}s")
            
            # Clean up files
            os.remove(input_path)
            os.remove(audio_path)
            logger.info("Files cleaned up")
            
            total_time = time.time() - start_time
            response = jsonify({
                "transcript": transcript,
                "summary": summary,
                "translated_summary": translated_summary,
                "processing_time_ms": int(total_time * 1000)
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as e:
            # Clean up files on error
            logger.error(f"Error during processing: {str(e)}")
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise e
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback: {error_traceback}")
        response = jsonify({
            "error": str(e),
            "step": "processing",
            "traceback": error_traceback
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/translate', methods=['POST', 'OPTIONS'])
def translate():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        data = request.json
        if not data or 'text' not in data or 'targetLanguage' not in data:
            return jsonify({"error": "Missing text or target language"}), 400
        
        text = data['text']
        target_language = data['targetLanguage']
        
        logger.info(f"Translating text to {target_language}...")
        translate_start = time.time()
        translated_text = translate_text(text, target_language)
        logger.info(f"Translation completed in {(time.time() - translate_start):.2f}s")
        
        return jsonify({
            "translatedText": translated_text
        })
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback: {error_traceback}")
        response = jsonify({
            "error": str(e),
            "step": "translation",
            "traceback": error_traceback
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/generate-pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        data = request.json
        if not data or 'summary' not in data:
            return jsonify({"error": "Missing summary"}), 400
        
        summary = data['summary']
        translated_summary = data.get('translatedSummary')  # Optional
        
        # Generate PDF
        pdf_content = create_summary_pdf(summary, translated_summary)
        
        # Create response with PDF file
        response = send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='meeting_summary.pdf'
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        response = jsonify({
            "error": str(e),
            "step": "pdf_generation"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/send-email', methods=['POST', 'OPTIONS'])
def send_email():
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    try:
        data = request.get_json()
        recipients = data.get('recipients', [])
        summary = data.get('summary')
        translated_summary = data.get('translatedSummary')
        
        if not recipients or not summary:
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Generate PDF
        pdf_data = create_summary_pdf(summary, translated_summary)
        
        # Send email
        send_summary_email(recipients, summary, pdf_data, translated_summary)
        
        response = jsonify({'message': 'Email sent successfully'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

if __name__ == '__main__':
    # This block only runs when starting the development server
    local_ip = get_local_ip()
    port = 8080
    logger.info(f"Starting development server on {local_ip}:{port}...")
    logger.info(f"You can access the server at:")
    logger.info(f"  http://localhost:{port}")
    logger.info(f"  http://{local_ip}:{port}")
    
    app.run(
        host='0.0.0.0',  # Bind to all interfaces
        port=port,
        debug=True,  # Enable debug mode for development
        threaded=True
    ) 