import os
from dotenv import load_dotenv
import cv2
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from ultralytics import YOLO
import threading
from flask import Flask, render_template, request, redirect, url_for, session, flash,Response
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for sessions
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename
# Load environment variables from .env file
load_dotenv()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        new_user = User(username='admin', password='admin123', role='admin')
        db.session.add(new_user)
        db.session.commit()
        print('User created: admin / admin123')
    else:
        print('User already exists.')

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        user = User.query.filter_by(username=uname).first()
        if user:
            if user.password == pwd:
                session['user'] = uname
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('User does not exist. Please check your username.', 'danger')

    return render_template('login.html')

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        else:
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('User added successfully.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('add_user.html')




# Retrieve the email and password from environment variables
sender_email = os.getenv("SENDER_EMAIL")
receiver_email = os.getenv("RECEIVER_EMAIL")
email_password = os.getenv("EMAIL_PASSWORD")

def draw_text_with_background(frame, text, position, font_scale=0.4, color=(255, 255, 255), thickness=1, bg_color=(0, 0, 0), alpha=0.7, padding=5):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_width, text_height = text_size

    overlay = frame.copy()
    x, y = position
    cv2.rectangle(overlay, (x - padding, y - text_height - padding), (x + text_width + padding, y + padding), bg_color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)

def send_email_alert(image_path):
    # Set up the MIME
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Alert: Hardhat Missing!"
    
    body = "A hardhat was not detected for the past 10 seconds, but a person was detected. Please find the attached frame showing the situation."
    message.attach(MIMEText(body, "plain"))
    
    # Attach the image file
    with open(image_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={image_path}")
        message.attach(part)
    
    # Sending the email via SMTP server
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, email_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email alert sent with attachment.")
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_email_in_background(image_path):
    email_thread = threading.Thread(target=send_email_alert, args=(image_path,))
    email_thread.start()


@app.route('/send_custom_email', methods=['POST'])
def send_custom_email():
    email = request.form.get('email')
    description = request.form.get('description')
    image = request.files.get('image')

    if not (email and description and image):
        flash('All fields are required!')
        return redirect(url_for('cam_dashboard'))

    # Save image temporarily
    filename = secure_filename(image.filename)
    temp_path = os.path.join('temp', filename)  # Make sure this folder exists
    image.save(temp_path)

    # Prepare the email
    msg = EmailMessage()
    msg['Subject'] = 'PPE Violation Alert 🚨'
    msg['From'] =os.getenv("SENDER_EMAIL")    # Replace with your sender email
    msg['To'] =os.getenv("RECEIVER_EMAIL")
    msg.set_content(f"Description:\n\n{description}")

    # Read the image and attach
    with open(temp_path, 'rb') as img:
        img_data = img.read()
        msg.add_attachment(img_data, maintype='image', subtype='png', filename=filename)

    # Send the email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(os.getenv("SENDER_EMAIL"), os.getenv("EMAIL_PASSWORD"))  # Use app password
            smtp.send_message(msg)

        flash("Email sent successfully!")
    except Exception as e:
        flash(f"Failed to send email: {e}")
    finally:
        os.remove(temp_path)  # Clean up temp image

    return redirect(url_for('cam_dashboard'))





# def main():
#     model = YOLO("Model/ppe.pt")  # Replace with your custom model file if needed
#     cap = cv2.VideoCapture(0)  # 0 is usually the default camera
    
#     if not cap.isOpened():
#         print("Error: Unable to access the webcam.")
#         return

#     print("Press 'q' to exit.")

#     colors = [
#         (255, 0, 0),  # Hardhat (Blue)
#         (0, 255, 0),  # Mask (Green)
#         (0, 0, 255),  # NO-Hardhat (Red)
#         (255, 255, 0),  # NO-Mask (Cyan)
#         (255, 0, 255),  # NO-Safety Vest (Magenta)
#         (0, 255, 255),  # Person (Yellow)
#         (128, 0, 128),  # Safety Cone (Purple)
#         (128, 128, 0),  # Safety Vest (Olive)
#         (0, 128, 128),  # Machinery (Teal)
#         (128, 128, 128)  # Vehicle (Gray)
#     ]

#     # Initialize last time a hardhat was detected
#     last_hardhat_time = time.time()
#     hardhat_missing = False
#     last_email_time = time.time()  # Track time of last email sent
#     email_sent_flag = False
#     email_sent_time = 0  # To track when to stop showing the email sent message

#     # Create a resizable window
#     cv2.namedWindow("YOLOv8 Annotated Feed", cv2.WINDOW_NORMAL)

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             print("Error: Unable to read from the webcam.")
#             break

#         # Initialize counters
#         hardhat_count = 0
#         vest_count = 0
#         person_count = 0
#         hardhat_detected = False
#         person_detected = False

#         # Perform YOLO inference
#         results = model(frame)

#         for result in results:
#             if result.boxes is not None:
#                 for box in result.boxes:
#                     x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
#                     confidence = box.conf[0]  # Confidence score
#                     cls = int(box.cls[0])  # Class ID
#                     label = f"{model.names[cls]} ({confidence:.2f})"

#                     color = colors[cls % len(colors)]

#                     # Draw the bounding box
#                     cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#                     draw_text_with_background(frame, label, (x1, y1 - 10), font_scale=0.4, color=(255, 255, 255), bg_color=color, alpha=0.8, padding=4)

#                     if model.names[cls] == "Hardhat":
#                         hardhat_count += 1
#                         hardhat_detected = True
#                     elif model.names[cls] == "Safety Vest":
#                         vest_count += 1
#                     elif model.names[cls] == "Person":
#                         person_count += 1
#                         person_detected = True

#         # If person is detected but no hardhat detected for 10 seconds, send an email alert
#         if person_detected and not hardhat_detected and (time.time() - last_email_time) >= 100:  # Check 10 seconds interval
#             image_path = "no_hardhat_frame.jpg"
#             cv2.imwrite(image_path, frame)  # Save the frame as an image
#             send_email_in_background(image_path)  # Send email in background thread
#             email_sent_flag = True
#             email_sent_time = time.time()  # Track the time of sending the email
#             last_email_time = time.time()  # Update last email time

#         # If hardhat detected, update the last time detected
#         if hardhat_detected:
#             last_hardhat_time = time.time()

#         # Add the counts on the sideboard
#         sideboard_text = [
#             f"Hardhats: {hardhat_count}",
#             f"Safety Vests: {vest_count}",
#             f"People: {person_count}"
#         ]

#         y_position = 30
#         for text in sideboard_text:
#             draw_text_with_background(frame, text, (10, y_position), font_scale=0.5, color=(255, 255, 255), bg_color=(0, 0, 0), alpha=0.7, padding=5)
#             y_position += 30

#         # Show the "Email Sent" message for 3 seconds after an email is sent
#         if email_sent_flag and (time.time() - email_sent_time) < 3:
#             draw_text_with_background(frame, "Email Sent", (frame.shape[1] - 100, 30), font_scale=0.5, color=(0, 255, 0), bg_color=(0, 0, 0), alpha=0.8, padding=5)

#         # Resize the frame to fit the window dynamically
#         resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)  # Resize to a fixed size

#         # Display the annotated frame
#         cv2.imshow("YOLOv8 Annotated Feed", resized_frame)

#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cap.release()
#     cv2.destroyAllWindows()


model = YOLO("Model/ppe.pt")  # Load your model
cap = cv2.VideoCapture(0)

def draw_text_with_background(frame, text, position, font_scale=0.5, color=(255,255,255), bg_color=(0,0,0), alpha=0.7, padding=5):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, 1)
    x, y = position
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y - text_height - padding), (x + text_width + padding*2, y + padding), bg_color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.putText(frame, text, (x + padding, y), font, font_scale, color, 1, cv2.LINE_AA)

def generate_frames():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
              (255, 0, 255), (0, 255, 255), (128, 0, 128), (128, 128, 0),
              (0, 128, 128), (128, 128, 128)]

    while True:
        success, frame = cap.read()
        if not success:
            break

        results = model(frame)

        hardhat_count = vest_count = person_count = 0

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    confidence = box.conf[0]
                    cls = int(box.cls[0])
                    label = f"{model.names[cls]} ({confidence:.2f})"
                    color = colors[cls % len(colors)]

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    draw_text_with_background(frame, label, (x1, y1 - 10), font_scale=0.4, color=(255, 255, 255), bg_color=color)

                    if model.names[cls] == "Hardhat":
                        hardhat_count += 1
                    elif model.names[cls] == "Safety Vest":
                        vest_count += 1
                    elif model.names[cls] == "Person":
                        person_count += 1

        sideboard = [
            f"Hardhats: {hardhat_count}",
            f"Safety Vests: {vest_count}",
            f"People: {person_count}"
        ]

        y_offset = 30
        for text in sideboard:
            draw_text_with_background(frame, text, (10, y_offset))
            y_offset += 30

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cam_dashboard')
def cam_dashboard():
    return render_template('cam_dashboard.html')


if __name__ == "__main__":
    app.run(debug=True)
    #main()
