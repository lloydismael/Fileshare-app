from flask import Flask, render_template, request, send_file, url_for, jsonify, session, redirect
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
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from aiortc.contrib.media import MediaRelay
import asyncio
import base64

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

# Store WebRTC connections
peer_connections = {}
data_channels = {}

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

@app.route('/connection', methods=['GET', 'POST'])
def connection():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            return redirect(url_for('create_room'))
        elif action == 'join':
            room_id = request.form.get('room_id')
            if room_id:
                return redirect(url_for('join_p2p_room', room_id=room_id))
            else:
                return 'Room ID is required to join a connection', 400
    return render_template('connection.html')

@socketio.on('join')
def on_join(data):
    room_id = data['room']
    join_room(room_id)
    logger.info(f"User {request.sid} attempting to join room {room_id}")
    
    if room_id not in rooms:
        # First person to join becomes the host
        rooms[room_id] = {
            'peers': set(),
            'host': request.sid,
            'pending_requests': set(),
            'connected_users': {request.sid}  # Track all connected users
        }
        emit('room_created', {
            'sid': request.sid,
            'room_id': room_id,
            'is_host': True
        }, room=request.sid)
        logger.info(f"Room {room_id} created with host {request.sid}")
    else:
        # Someone trying to join an existing room
        host_sid = rooms[room_id]['host']
        rooms[room_id]['connected_users'].add(request.sid)
        
        if request.sid != host_sid:
            connection_requests[request.sid] = {
                'room': room_id,
                'status': 'pending',
                'timestamp': time.time(),
                'username': data.get('username', f'User-{request.sid[:6]}')
            }
            rooms[room_id]['pending_requests'].add(request.sid)
            
            # Notify the host about the new connection request
            emit('connection_request', {
                'sid': request.sid,
                'room': room_id,
                'username': connection_requests[request.sid]['username']
            }, room=host_sid)
            
            # Notify the requester they're waiting for approval
            emit('waiting_for_host', {
                'host_sid': host_sid,
                'room_id': room_id
            }, room=request.sid)
            
            logger.info(f"Connection request sent from {request.sid} to host {host_sid} for room {room_id}")
            
            # Broadcast to all room members about the pending request
            emit('user_pending', {
                'sid': request.sid,
                'username': connection_requests[request.sid]['username']
            }, room=room_id)

@socketio.on('connection_response')
def on_connection_response(data):
    requester_sid = data['requester_sid']
    accepted = data['accepted']
    transfer_mode = data.get('transfer_mode', 'webrtc')  # 'webrtc' or 'socket'
    
    if requester_sid not in connection_requests:
        logger.warning(f"No pending request found for {requester_sid}")
        return
        
    room_id = connection_requests[requester_sid]['room']
    requester_username = connection_requests[requester_sid].get('username', f'User-{requester_sid[:6]}')
    
    if accepted:
        if room_id in rooms:
            rooms[room_id]['peers'].add(requester_sid)
            rooms[room_id]['pending_requests'].discard(requester_sid)
            
            # Notify the requester that they've been accepted
            emit('connection_accepted', {
                'sid': request.sid,
                'room': room_id,
                'host_sid': request.sid
            }, room=requester_sid)
            
            # Notify all room members about the new peer
            emit('user_joined', {
                'sid': requester_sid,
                'username': requester_username
            }, room=room_id)
            
            # Send the current peer list to the new user
            emit('peer_list', {
                'peers': list(rooms[room_id]['peers']),
                'host': rooms[room_id]['host']
            }, room=requester_sid)
            
            logger.info(f"Connection accepted for {requester_username} ({requester_sid}) in room {room_id}")
    else:
        # Remove user from room's connected users if rejected
        if room_id in rooms:
            rooms[room_id]['connected_users'].discard(requester_sid)
            rooms[room_id]['pending_requests'].discard(requester_sid)
        
        emit('connection_rejected', {
            'sid': request.sid,
            'room': room_id,
            'reason': data.get('reason', 'Request denied by host')
        }, room=requester_sid)
        
        logger.info(f"Connection rejected for {requester_username} ({requester_sid}) in room {room_id}")
    
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

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    sender_sid = request.sid
    target_sid = data.get('target_sid')
    room_id = data.get('room')
    
    if room_id not in rooms or target_sid not in rooms[room_id]['connected_users']:
        return
    
    # Forward the offer to the target peer
    emit('webrtc_offer', {
        'sdp': data['sdp'],
        'sender_sid': sender_sid
    }, room=target_sid)
    logger.info(f"WebRTC offer forwarded from {sender_sid} to {target_sid}")

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    sender_sid = request.sid
    target_sid = data.get('target_sid')
    room_id = data.get('room')
    
    if room_id not in rooms or target_sid not in rooms[room_id]['connected_users']:
        return
    
    # Forward the answer to the target peer
    emit('webrtc_answer', {
        'sdp': data['sdp'],
        'sender_sid': sender_sid
    }, room=target_sid)
    logger.info(f"WebRTC answer forwarded from {sender_sid} to {target_sid}")

@socketio.on('webrtc_ice_candidate')
def handle_ice_candidate(data):
    sender_sid = request.sid
    target_sid = data.get('target_sid')
    room_id = data.get('room')
    
    if room_id not in rooms or target_sid not in rooms[room_id]['connected_users']:
        return
    
    # Forward the ICE candidate to the target peer
    emit('webrtc_ice_candidate', {
        'candidate': data['candidate'],
        'sender_sid': sender_sid
    }, room=target_sid)
    logger.info(f"ICE candidate forwarded from {sender_sid} to {target_sid}")

@socketio.on('start_file_transfer')
def handle_start_file_transfer(data):
    sender_sid = request.sid
    target_sid = data.get('target_sid')
    room_id = data.get('room')
    filename = data.get('filename')
    file_size = data.get('file_size')
    
    if room_id not in rooms or target_sid not in rooms[room_id]['connected_users']:
        return
    
    # Notify the target peer about the incoming file
    emit('file_transfer_request', {
        'sender_sid': sender_sid,
        'filename': filename,
        'file_size': file_size
    }, room=target_sid)
    logger.info(f"File transfer request sent from {sender_sid} to {target_sid}")

@socketio.on('file_transfer_response')
def handle_file_transfer_response(data):
    sender_sid = request.sid
    target_sid = data.get('target_sid')
    accepted = data.get('accepted')
    
    # Notify the sender about the response
    emit('file_transfer_response', {
        'accepted': accepted,
        'target_sid': sender_sid
    }, room=target_sid)
    logger.info(f"File transfer {'accepted' if accepted else 'rejected'} by {sender_sid}")

@socketio.on('file_chunk')
def handle_file_chunk(data):
    target_sid = data.get('target_sid')
    chunk = data.get('chunk')
    chunk_index = data.get('chunk_index')
    total_chunks = data.get('total_chunks')
    
    # Forward the file chunk to the target peer
    emit('file_chunk', {
        'chunk': chunk,
        'chunk_index': chunk_index,
        'total_chunks': total_chunks,
        'sender_sid': request.sid
    }, room=target_sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)