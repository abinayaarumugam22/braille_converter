from flask import Flask, render_template, request, send_file
import pdfplumber
import docx2txt
import pytesseract
import cv2
import numpy as np
from PIL import Image
import os
from gtts import gTTS
from docx import Document
import io

app = Flask(__name__)

# Set the path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "static"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# 🟢 Preprocessing function for images
def preprocess_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)  # Reduce noise
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)  # Apply adaptive thresholding

    kernel = np.ones((2, 2), np.uint8)
    processed_image = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)  # Remove small noise

    processed_path = "processed_image.png"
    cv2.imwrite(processed_path, processed_image)
    return processed_path  # Return path of the cleaned image

# 🟢 Function to extract text from images
def extract_text_from_image(image_path):
    processed_path = preprocess_image(image_path)  # Preprocess image
    text = pytesseract.image_to_string(Image.open(processed_path))  # OCR on processed image
    return text

# 🟢 Function to extract text from PDFs (including images)
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""  # Extract text from PDF
            for img in page.images:  # Process images in PDF
                img_data = img["stream"].get_data()
                image = Image.open(io.BytesIO(img_data))
                text += pytesseract.image_to_string(image) + "\n"
    return text

# 🟢 Function to convert text to Braille
def convert_to_braille(text):
    braille_dict = {
    # Lowercase letters
    "a": "⠁", "b": "⠃", "c": "⠉", "d": "⠙", "e": "⠑",
    "f": "⠋", "g": "⠛", "h": "⠓", "i": "⠊", "j": "⠚",
    "k": "⠅", "l": "⠇", "m": "⠍", "n": "⠝", "o": "⠕",
    "p": "⠏", "q": "⠟", "r": "⠗", "s": "⠎", "t": "⠞",
    "u": "⠥", "v": "⠧", "w": "⠺", "x": "⠭", "y": "⠽", "z": "⠵",
    
    # Uppercase letters (preceded by the uppercase indicator ⠨)
    "A": "⠨⠁", "B": "⠨⠃", "C": "⠨⠉", "D": "⠨⠙", "E": "⠨⠑",
    "F": "⠨⠋", "G": "⠨⠛", "H": "⠨⠓", "I": "⠨⠊", "J": "⠨⠚",
    "K": "⠨⠅", "L": "⠨⠇", "M": "⠨⠍", "N": "⠨⠝", "O": "⠨⠕",
    "P": "⠨⠏", "Q": "⠨⠟", "R": "⠨⠗", "S": "⠨⠎", "T": "⠨⠞",
    "U": "⠨⠥", "V": "⠨⠧", "W": "⠨⠺", "X": "⠨⠭", "Y": "⠨⠽", "Z": "⠨⠵",

    # Numbers (preceded by the number indicator ⠼)
    "0": "⠼⠚", "1": "⠼⠁", "2": "⠼⠃", "3": "⠼⠉", "4": "⠼⠙",
    "5": "⠼⠑", "6": "⠼⠋", "7": "⠼⠛", "8": "⠼⠓", "9": "⠼⠊",

    # Punctuation
    " ": " ", ".": "⠲", ",": "⠂", ";": "⠆", ":": "⠒",
    "?": "⠦", "!": "⠖", "-": "⠤", "(": "⠷", ")": "⠾",
    "'": "⠄", "\"": "⠦⠴", "/": "⠌", "\\": "⠡",
    "&": "⠯", "*": "⠔", "+": "⠖", "=": "⠶", "_": "⠤",
    "@": "⠈", "#": "⠼", "%": "⠨⠴", "$": "⠈⠎"
}

    return "".join(braille_dict.get(char.lower(), char) for char in text)

# 🟢 Flask Route: Home (Handles File Upload & Processing)
@app.route("/", methods=["GET", "POST"])
def index():
    text, braille = "", ""
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Extract text based on file type
            if file.filename.endswith(".pdf"):
                text = extract_text_from_pdf(file_path)
            elif file.filename.endswith(".docx"):
                text = docx2txt.process(file_path)
            elif file.filename.endswith((".png", ".jpg", ".jpeg")):
                text = extract_text_from_image(file_path)

            # Convert extracted text to Braille
            braille = convert_to_braille(text)

            # Convert text to speech
            speech = gTTS(text, lang="en")
            speech.save(os.path.join(OUTPUT_FOLDER, "speech.mp3"))

            # Save Braille text
            with open(os.path.join(OUTPUT_FOLDER, "braille.txt"), "w", encoding="utf-8") as f:
                f.write(braille)

    return render_template("index.html", text=text, braille=braille)

# 🟢 Flask Route: Download Braille as .docx
@app.route("/download/<file_type>")
def download_braille(file_type):
    braille_text = open(os.path.join(OUTPUT_FOLDER, "braille.txt"), "r", encoding="utf-8").read()
    if file_type == "docx":
        doc = Document()
        doc.add_paragraph(braille_text)
        doc_path = os.path.join(OUTPUT_FOLDER, "braille_output.docx")
        doc.save(doc_path)
        return send_file(doc_path, as_attachment=True)
    return "Invalid file type", 400

# 🟢 Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
