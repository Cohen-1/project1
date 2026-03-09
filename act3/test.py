from flask import Flask, request, jsonify
import time
import random


app = Flask(__name__)

appointments = []

@app.route('/api/appointments/book', methods=['POST'])
def book_appointment():
    data = request.get_json()

    time.sleep(random.uniform(0.1, 0.5))
    appointments.append(data)
    return jsonify({"message": "Appointment boooked successfully"}), 201


if __name__ == "__main__":
    app.run(debug=True, port=5000)
