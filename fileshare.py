from flask import Flask, render_template, request, send_file, url_for, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import qrcode
import os
import json
import time
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for sessions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SocketIO with WebSocket support
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet',
                   ping_timeout=60,
                   ping_interval=25)

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Store file_id to filename mapping
file_mapping = {}

# Store room information
rooms = {}

# Store connection requests
connection_requests = {}

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

@app.route('/qr/<file_id>.png')
def serve_qr(file_id):
    qr_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}.png')
    if not os.path.exists(qr_path):
        return 'QR code not found', 404
    return send_file(qr_path, mimetype='image/png')

@app.route('/create-room')
def create_room():
    room_id = str(uuid.uuid4())
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    room_url = url_for('join_p2p_room', room_id=room_id, _external=True)
    qr.add_data(room_url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    qr_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{room_id}_room.png')
    qr_image.save(qr_path)
    
    return render_template('create_room.html', room_id=room_id)

@app.route('/join-room/<room_id>')
def join_p2p_room(room_id):
    return render_template('join_room.html', room_id=room_id)

@socketio.on('join')
def on_join(data):
    room_id = data['room']
    join_room(room_id)
    if room_id not in rooms:
        # First person to join becomes the host
        rooms[room_id] = {'peers': set(), 'host': request.sid, 'pending_requests': set()}
        emit('room_created', {'sid': request.sid}, room=room_id)
        print(f"Room {room_id} created with host {request.sid}")
    else:
        # Someone trying to join an existing room
        host_sid = rooms[room_id]['host']
        if request.sid != host_sid:  # Only send request if not the host
            connection_requests[request.sid] = {
                'room': room_id,
                'status': 'pending',
                'timestamp': time.time()
            }
            rooms[room_id]['pending_requests'].add(request.sid)
            # Send request to host
            emit('connection_request', {
                'sid': request.sid,
                'room': room_id
            }, room=host_sid)
            print(f"Connection request sent from {request.sid} to host {host_sid} for room {room_id}")
        emit('waiting_for_host', {'host_sid': host_sid}, room=request.sid)

@socketio.on('connection_response')
def on_connection_response(data):
    requester_sid = data['requester_sid']
    accepted = data['accepted']
    
    if requester_sid not in connection_requests:
        print(f"No pending request found for {requester_sid}")
        return
        
    room_id = connection_requests[requester_sid]['room']
    
    if accepted:
        if room_id in rooms:
            rooms[room_id]['peers'].add(requester_sid)
            rooms[room_id]['pending_requests'].discard(requester_sid)
            emit('connection_accepted', {
                'sid': request.sid,
                'room': room_id
            }, room=requester_sid)
            print(f"Connection accepted for {requester_sid} in room {room_id}")
    else:
        emit('connection_rejected', {
            'sid': request.sid,
            'room': room_id
        }, room=requester_sid)
        print(f"Connection rejected for {requester_sid} in room {room_id}")
        
        if room_id in rooms:
            rooms[room_id]['pending_requests'].discard(requester_sid)
    
    del connection_requests[requester_sid]

@socketio.on('leave')
def on_leave(data):
    room_id = data['room']
    if room_id in rooms:
        rooms[room_id]['peers'].discard(request.sid)
        if not rooms[room_id]['peers']:
            del rooms[room_id]
    leave_room(room_id)
    emit('user_left', {'sid': request.sid}, room=room_id)

@socketio.on('offer')
def on_offer(data):
    emit('offer', {
        'sdp': data['sdp'],
        'offerer': request.sid
    }, room=data['room'])

@socketio.on('answer')
def on_answer(data):
    emit('answer', {
        'sdp': data['sdp'],
        'answerer': request.sid
    }, room=data['room'])

@socketio.on('ice_candidate')
def on_ice_candidate(data):
    emit('ice_candidate', {
        'candidate': data['candidate'],
        'sender': request.sid
    }, room=data['room'])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)