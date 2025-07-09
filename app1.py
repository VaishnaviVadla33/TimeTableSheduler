
from flask import Flask, request, render_template, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
import os
import pandas as pd
import random
import traceback
import logging
from flask import Flask, request, render_template, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import pandas as pd
import random
import traceback
import logging
from flask import send_file
import io
import zipfile
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('app.log'),
                        logging.StreamHandler()
                    ])

app = Flask(__name__, 
    template_folder='templates', 
    static_folder='static'
)

# Firebase Configuration
# Improved Firebase Initialization Code
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import logging

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = r"D:\web\webathon_timetable\firebase_credentials.json"

def initialize_firebase():
    """Initialize Firebase Admin SDK with better error handling"""
    try:
        # Check if Firebase app is already initialized
        if firebase_admin._apps:
            logging.info("Firebase already initialized")
            return firestore.client()
        
        # Verify the credentials file exists
        if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
            raise FileNotFoundError(f"Firebase credentials file not found at {FIREBASE_CREDENTIALS_PATH}")
        
        # Verify credentials file is valid JSON
        try:
            with open(FIREBASE_CREDENTIALS_PATH, 'r') as f:
                creds_data = json.load(f)
                required_keys = ['private_key', 'client_email', 'project_id']
                missing_keys = [key for key in required_keys if key not in creds_data]
                if missing_keys:
                    raise ValueError(f"Missing required keys in credentials: {missing_keys}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in credentials file: {e}")
        
        # Initialize Firebase
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Test connection
        try:
            # Try to read from a test collection
            test_ref = db.collection('test').limit(1)
            list(test_ref.stream())
            logging.info("Successfully connected to Firebase")
        except Exception as e:
            logging.warning(f"Firebase connection test failed: {e}")
        
        return db
    
    except Exception as e:
        logging.error(f"Firebase Connection Error: {e}")
        raise

# Alternative initialization using environment variables (recommended)
def initialize_firebase_env():
    """Initialize Firebase using environment variables (more secure)"""
    try:
        if firebase_admin._apps:
            return firestore.client()
        
        # Check for environment variable
        if 'FIREBASE_CREDENTIALS' in os.environ:
            # If credentials are stored as environment variable
            creds_dict = json.loads(os.environ['FIREBASE_CREDENTIALS'])
            cred = credentials.Certificate(creds_dict)
        else:
            # Fall back to file
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("Successfully connected to Firebase")
        return db
    
    except Exception as e:
        logging.error(f"Firebase Connection Error: {e}")
        raise

# Initialize Firebase globally
db = initialize_firebase()

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TIMINGS = ["10-11", "11-12", "12-1", "LUNCH", "2-3", "3-4"]
MAX_HOURS_PER_WEEK = 20
REQUIRED_COLUMNS = ['Department', 'Semester', 'Section', 'Subject', 
                   'Theory Classes', 'Practical Classes', 'Tutorial Classes', 'Faculty']

def validate_excel_data(df):
    """Validate the structure of the Excel file"""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
    
    if df.empty:
        raise ValueError("The Excel file is empty")
    
    # Check for required values
    if df[['Department', 'Semester', 'Section', 'Subject']].isnull().values.any():
        raise ValueError("Department, Semester, Section, and Subject cannot be empty")

def generate_timetables(df):
    """Generate timetables for all department/semester/section combinations"""
    try:
        # Convert to appropriate data types
        df["Semester"] = df["Semester"].astype(str)
        df["Theory Classes"] = pd.to_numeric(df["Theory Classes"], errors='coerce').fillna(0).astype(int)
        df["Practical Classes"] = pd.to_numeric(df["Practical Classes"], errors='coerce').fillna(0).astype(int)
        df["Tutorial Classes"] = pd.to_numeric(df["Tutorial Classes"], errors='coerce').fillna(0).astype(int)
        
        # Initialize faculty tracking
        faculty_data = {
            str(faculty): {"assigned_slots": 0} 
            for faculty in df["Faculty"].unique() 
            if pd.notna(faculty)
        }
        
        # Group data by department, semester, section
        grouped = df.groupby(['Department', 'Semester', 'Section'])
        
        timetables = []
        
        for (dept, sem, sec), group in grouped:
            # Initialize timetable structure
            timetable = {
                "department": str(dept),
                "semester": str(sem),
                "section": str(sec),
                "days": {}
            }
            
            # Initialize days structure
            for day in DAYS:
                timetable["days"][day] = {
                    time: None for time in TIMINGS
                }
            
            # Process each subject in this group
            for _, row in group.iterrows():
                subject = str(row["Subject"])
                theory_count = row["Theory Classes"]
                lab_count = row["Practical Classes"]
                tutorial_count = row["Tutorial Classes"]
                faculty = str(row["Faculty"]) if pd.notna(row["Faculty"]) else None
                
                if not faculty:
                    logging.warning(f"No faculty assigned for {subject} in {dept}, Semester {sem}, Section {sec}")
                    continue
                
                # Assign theory classes
                for _ in range(theory_count):
                    assigned = False
                    for _ in range(50):  # Limit attempts
                        day = random.choice(DAYS)
                        time = random.choice([t for t in TIMINGS if t != "LUNCH"])
                        if timetable["days"][day][time] is None and faculty_data[faculty]["assigned_slots"] < MAX_HOURS_PER_WEEK:
                            timetable["days"][day][time] = f"{subject} ({faculty})"
                            faculty_data[faculty]["assigned_slots"] += 1
                            assigned = True
                            break
                
                # Assign lab classes (2 consecutive slots)
                for _ in range(lab_count):
                    assigned = False
                    for _ in range(50):
                        day = random.choice(DAYS)
                        time_idx = random.randint(0, len(TIMINGS) - 3)
                        time1, time2 = TIMINGS[time_idx], TIMINGS[time_idx + 1]
                        if (time1 != "LUNCH" and time2 != "LUNCH" and
                            timetable["days"][day][time1] is None and 
                            timetable["days"][day][time2] is None and
                            faculty_data[faculty]["assigned_slots"] < MAX_HOURS_PER_WEEK - 1):
                            
                            timetable["days"][day][time1] = f"{subject} Lab ({faculty})"
                            timetable["days"][day][time2] = f"{subject} Lab ({faculty})"
                            faculty_data[faculty]["assigned_slots"] += 2
                            assigned = True
                            break
                
                # Assign tutorial classes
                for _ in range(tutorial_count):
                    assigned = False
                    for _ in range(50):
                        day = random.choice(DAYS)
                        time = random.choice([t for t in TIMINGS if t != "LUNCH"])
                        if timetable["days"][day][time] is None and faculty_data[faculty]["assigned_slots"] < MAX_HOURS_PER_WEEK:
                            timetable["days"][day][time] = f"{subject} Tutorial ({faculty})"
                            faculty_data[faculty]["assigned_slots"] += 1
                            assigned = True
                            break
            
            timetables.append(timetable)
        
        return timetables
    
    except Exception as e:
        logging.error(f"Error in timetable generation: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def store_timetables(timetables):
    """Store timetables in Firebase using hierarchical collections"""
    try:
        for timetable in timetables:
            dept = timetable["department"]
            sem = timetable["semester"]
            sec = timetable["section"]
            
            logging.info(f"Storing timetable - Department: {dept}, Semester: {sem}, Section: {sec}")
            
            # Create a reference to the specific section's document
            # Collection name format: "DEPT_SEM_sections"
            section_ref = db.collection(f"{dept}_{sem}_sections").document(sec)
            
            # Set the timetable data
            section_ref.set({
                "department": dept,
                "semester": sem,
                "section": sec,
                "timetable": timetable["days"]
            })
        
        return True
    except Exception as e:
        logging.error(f"Error storing timetables: {e}")
        logging.error(traceback.format_exc())
        return False

@app.route("/", methods=["GET"])
def index():
    """Landing page - redirects to dashboard"""
    return redirect(url_for('dashboard'))

@app.route("/upload", methods=["GET", "POST"])
def upload_subjects():
    """Handle file upload and timetable generation with better error handling"""
    if request.method == "POST":
        try:
            # Check if file is present
            if "file" not in request.files:
                return render_template("upload.html", 
                    message="No file uploaded", 
                    error=True)

            file = request.files["file"]
            if file.filename == "":
                return render_template("upload.html", 
                    message="No file selected", 
                    error=True)

            # Validate file type
            if not file.filename.lower().endswith(('.xlsx', '.xls')):
                return render_template("upload.html", 
                    message="Invalid file type. Please upload an Excel file.", 
                    error=True)

            # Ensure uploads directory exists
            os.makedirs("uploads", exist_ok=True)
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)

            # Read and validate Excel file
            try:
                df = pd.read_excel(file_path)
                validate_excel_data(df)
                logging.info(f"Successfully read Excel file with {len(df)} rows")
            except Exception as e:
                logging.error(f"Excel validation error: {str(e)}")
                return render_template("upload.html", 
                    message=f"Error reading Excel file: {str(e)}", 
                    error=True)

            # Test Firebase connection before proceeding
            try:
                db = initialize_firebase()  # Use your improved initialization
                # Test write operation
                test_ref = db.collection('test').document('connection_test')
                test_ref.set({'timestamp': firestore.SERVER_TIMESTAMP})
                logging.info("Firebase connection test successful")
            except Exception as e:
                logging.error(f"Firebase connection test failed: {str(e)}")
                return render_template("upload.html", 
                    message=f"Database connection error: {str(e)}", 
                    error=True)

            # Store original subjects data
            try:
                subjects_data = df.to_dict('records')
                subjects_collection = db.collection('subjects')
                
                # Clear existing subjects (optional)
                # docs = subjects_collection.stream()
                # for doc in docs:
                #     doc.reference.delete()
                
                # Add new subjects
                for i, subject in enumerate(subjects_data):
                    doc_ref = subjects_collection.document(f"subject_{i}")
                    doc_ref.set(subject)
                
                logging.info(f"Successfully stored {len(subjects_data)} subjects")
            except Exception as e:
                logging.error(f"Error storing subjects: {str(e)}")
                return render_template("upload.html", 
                    message=f"Error storing subjects: {str(e)}", 
                    error=True)

            # Generate timetables
            try:
                timetables = generate_timetables(df)
                if not timetables:
                    return render_template("upload.html", 
                        message="No timetables were generated", 
                        error=True)
                logging.info(f"Successfully generated {len(timetables)} timetables")
            except Exception as e:
                logging.error(f"Error generating timetables: {str(e)}")
                return render_template("upload.html", 
                    message=f"Error generating timetables: {str(e)}", 
                    error=True)

            # Store timetables
            try:
                if not store_timetables(timetables):
                    return render_template("upload.html", 
                        message="Error storing timetables in database", 
                        error=True)
                logging.info("Successfully stored all timetables")
            except Exception as e:
                logging.error(f"Error storing timetables: {str(e)}")
                return render_template("upload.html", 
                    message=f"Error storing timetables: {str(e)}", 
                    error=True)

            return render_template("upload.html", 
                message=f"Successfully generated {len(timetables)} timetables!", 
                success=True)

        except Exception as e:
            logging.error(f"Unexpected error in upload: {e}")
            logging.error(traceback.format_exc())
            return render_template("upload.html", 
                message=f"An unexpected error occurred: {str(e)}", 
                error=True)

    return render_template("upload.html", message=None)


@app.route("/download_timetables")
def download_timetables():
    """Download all timetables as separate Excel files in a ZIP archive with proper formatting"""
    try:
        # Constants for correct row & column order
        DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        TIMINGS = ["10-11", "11-12", "12-1", "LUNCH", "2-3", "3-4"]

        memory_zip = BytesIO()
        with zipfile.ZipFile(memory_zip, 'w') as zf:
            collections = [col for col in db.collections() if '_sections' in col.id]

            for collection in collections:
                for doc in collection.stream():
                    data = doc.to_dict()
                    timetable = data.get("timetable", {})

                    # Build ordered data matrix
                    ordered_data = {day: [] for day in DAYS}
                    for time in TIMINGS:
                        for day in DAYS:
                            ordered_data[day].append(timetable.get(day, {}).get(time, ""))

                    df = pd.DataFrame(ordered_data, index=TIMINGS)

                    dept = data.get("department", "UnknownDept")
                    sem = data.get("semester", "X")
                    sec = data.get("section", "X")

                    filename = f"Timetable_{dept}_Sem{sem}_Sec{sec}.xlsx"

                    file_stream = BytesIO()
                    with pd.ExcelWriter(file_stream, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=True, sheet_name='Timetable')

                    file_stream.seek(0)
                    zf.writestr(filename, file_stream.read())

        memory_zip.seek(0)
        return send_file(
            memory_zip,
            download_name="All_Timetables.zip",
            as_attachment=True,
            mimetype="application/zip"
        )

    except Exception as e:
        logging.error(f"Error generating timetables ZIP: {e}")
        return "Failed to generate timetable download", 500
    

@app.route("/view_timetables")
def view_timetables():
    """View all generated timetables"""
    try:
        timetables = []
        departments = set()
        semesters = set()
        sections = set()
        
        # Get all department-semester section collections
        collections = [col for col in db.collections() if '_sections' in col.id]
        
        for collection in collections:
            # Fetch all timetables in this collection
            collection_timetables = collection.stream()
            for doc in collection_timetables:
                timetable_data = doc.to_dict()
                timetables.append(timetable_data)
                departments.add(timetable_data['department'])
                semesters.add(timetable_data['semester'])
                sections.add(timetable_data['section'])
        
        # Get filter parameters from request
        selected_department = request.args.get("department", "")
        selected_semester = request.args.get("semester", "")
        selected_section = request.args.get("section", "")
        
        # Apply filters if specified
        filtered_timetables = []
        for timetable in timetables:
            if (not selected_department or timetable['department'] == selected_department) and \
               (not selected_semester or timetable['semester'] == selected_semester) and \
               (not selected_section or timetable['section'] == selected_section):
                filtered_timetables.append(timetable)
        
        return render_template("view_timetables.html", 
                             timetables=filtered_timetables,
                             departments=sorted(departments),
                             semesters=sorted(semesters),
                             sections=sorted(sections),
                             selected_department=selected_department,
                             selected_semester=selected_semester,
                             selected_section=selected_section)
    
    except Exception as e:
        logging.error(f"Error loading timetables: {e}")
        logging.error(traceback.format_exc())
        return render_template("view_timetables.html", 
                             timetables=[], 
                             error_message=f"Error loading timetables: {str(e)}")
    
@app.route("/dashboard")
def dashboard():
    """Main dashboard that combines timetable viewing and creation"""
    try:
        # Get all available departments, semesters, sections for dropdowns
        departments = ["CSE", "CS_DS"]  # From your data
        semesters = ["1","2","3", "4","5","6","7","8"]          # From your data
        sections = ["a", "b"]           # From your data
        
        # Get all timetables
        timetables = []
        collections = [col for col in db.collections() if '_sections' in col.id]
        for collection in collections:
            docs = collection.stream()
            for doc in docs:
                timetables.append(doc.to_dict())
        
        # Get filter parameters from URL (for initial page load)
        selected_department = request.args.get("department", "")
        selected_semester = request.args.get("semester", "")
        selected_section = request.args.get("section", "")
        
        return render_template("dashboard.html",
                            timetables=timetables,
                            departments=departments,
                            semesters=semesters,
                            sections=sections,
                            selected_department=selected_department,
                            selected_semester=selected_semester,
                            selected_section=selected_section)
    
    except Exception as e:
        logging.error(f"Error loading dashboard: {e}")
        return render_template("dashboard.html",
                            error_message=f"Error loading dashboard: {str(e)}")

@app.route("/update_timetable", methods=["POST"])
def update_timetable():
    """Handle timetable updates (reschedule, swap, cancel)"""
    try:
        data = {k: v.strip() if isinstance(v, str) else v for k, v in request.json.items()}
        logging.info(f"Received update data: {data}")

        # Validate required fields
        required_fields = ['department', 'semester', 'section']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "error": f"Missing required fields: {missing_fields}"})
        
        # Construct collection name
        collection_name = f"{data['department']}_{data['semester']}_sections"
        
        # Find the specific section document
        section_ref = db.collection(collection_name).document(data['section'])
        section_doc = section_ref.get()
        
        if not section_doc.exists:
            return jsonify({"success": False, "error": "Timetable not found"})
        
        # Get the current timetable
        timetable_data = section_doc.to_dict()
        if 'timetable' not in timetable_data:
            return jsonify({"success": False, "error": "Timetable data not found"})
        
        timetable = timetable_data['timetable']
        
        # Debug: Log timetable structure
        logging.info(f"Timetable keys: {list(timetable.keys())}")
        for day in timetable:
            logging.info(f"Day '{day}' has timeslots: {list(timetable[day].keys())}")
        
        # Handle different update actions
        if 'action' in data:
            if data['action'] == 'reschedule':
                # Reschedule action - need day, time_slot and new_class
                if 'day' not in data or 'time_slot' not in data or 'new_class' not in data:
                    return jsonify({"success": False, "error": "Missing day, time_slot or new_class for reschedule"})
                
                day = data['day']
                time_slot = data['time_slot']
                
                if day not in timetable:
                    return jsonify({"success": False, "error": f"Day '{day}' not found in timetable"})
                
                if time_slot not in timetable[day]:
                    return jsonify({"success": False, "error": f"Time slot '{time_slot}' not found for day '{day}'"})
                
                timetable[day][time_slot] = data['new_class']
                logging.info(f"Rescheduled {day} {time_slot} to {data['new_class']}")
                
            elif data['action'] == 'swap':
                # Swap action - need two complete day-time pairs
                required_swap_fields = ['day1', 'time_slot1', 'day2', 'time_slot2']
                missing_swap_fields = [field for field in required_swap_fields if field not in data]
                if missing_swap_fields:
                    return jsonify({"success": False, "error": f"Missing swap fields: {missing_swap_fields}"})
                
                day1, time_slot1 = data['day1'], data['time_slot1']
                day2, time_slot2 = data['day2'], data['time_slot2']
                
                # Debug logging
                logging.info(f"Swap request: {day1} {time_slot1} <-> {day2} {time_slot2}")
                
                # Validate both slots exist
                if day1 not in timetable:
                    return jsonify({"success": False, "error": f"Day '{day1}' not found in timetable"})
                if day2 not in timetable:
                    return jsonify({"success": False, "error": f"Day '{day2}' not found in timetable"})
                
                if time_slot1 not in timetable[day1]:
                    return jsonify({"success": False, "error": f"Time slot '{time_slot1}' not found for day '{day1}'"})
                if time_slot2 not in timetable[day2]:
                    return jsonify({"success": False, "error": f"Time slot '{time_slot2}' not found for day '{day2}'"})
                
                # Get current values
                value1 = timetable[day1][time_slot1]
                value2 = timetable[day2][time_slot2]
                
                logging.info(f"Swapping: '{value1}' at {day1} {time_slot1} with '{value2}' at {day2} {time_slot2}")
                
                # Perform the swap
                timetable[day1][time_slot1] = value2
                timetable[day2][time_slot2] = value1
                
                logging.info(f"Successfully swapped {day1} {time_slot1} with {day2} {time_slot2}")
                
            elif data['action'] == 'cancel':
                # Cancel action - need day and time_slot
                if 'day' not in data or 'time_slot' not in data:
                    return jsonify({"success": False, "error": "Missing day or time_slot for cancel"})
                
                day = data['day']
                time_slot = data['time_slot']
                
                if day not in timetable:
                    return jsonify({"success": False, "error": f"Day '{day}' not found in timetable"})
                
                if time_slot not in timetable[day]:
                    return jsonify({"success": False, "error": f"Time slot '{time_slot}' not found for day '{day}'"})
                
                timetable[day][time_slot] = None
                logging.info(f"Cancelled {day} {time_slot}")
                
            else:
                return jsonify({"success": False, "error": f"Unknown action: {data['action']}"})
        
        else:
            return jsonify({"success": False, "error": "No action specified"})
        
        # Update the document
        section_ref.update({
            'timetable': timetable
        })
        
        logging.info("Timetable updated successfully in database")
        return jsonify({"success": True, "message": "Timetable updated successfully"})
    
    except Exception as e:
        logging.error(f"Error updating timetable: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)})
    
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
