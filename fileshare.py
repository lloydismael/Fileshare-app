from flask import Flask, render_template, request, send_file, url_for
import qrcode
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Store file_id to filename mapping
file_mapping = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file selected', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No file selected', 400

    # Generate unique ID for the file
    file_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    file_mapping[file_id] = filename
    
    # Save the file
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr_data = url_for('download_file', file_id=file_id, _external=True)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    qr_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}.png')
    qr_image.save(qr_path)
    
    return render_template('upload_success.html', file_id=file_id)

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in file_mapping:
        return 'File not found', 404
    
    filename = file_mapping[file_id]
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__ == '__main__':
    app.run(debug=True)