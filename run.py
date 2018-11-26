#!/usr/bin/python
from app import app, socketio

#app.run(debug=True, host='0.0.0.0', port=4000)
socketio.run(app, host='0.0.0.0', port=4000, debug=True, use_reloader=True, use_debugger=True)