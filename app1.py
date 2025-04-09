
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
# Use raw string (r prefix) for Windows paths or forward slashes
FIREBASE_CREDENTIALS_PATH = r"D:\web\webathon_timetable\firebase_credentials.json"

# App configuration
app.secret_key = "your_unique_and_secret_key_here_123456"

# Firebase Initialization
def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase app is already initialized
        if not firebase_admin._apps:
            # Verify the credentials file exists
            if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
                raise FileNotFoundError(f"Firebase credentials file not found at {FIREBASE_CREDENTIALS_PATH}")
            
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        logging.info("Successfully connected to Firebase")
        return db
    
    except Exception as e:
        logging.error(f"Firebase Connection Error: {e}")
        logging.error(traceback.format_exc())
        raise

# Initialize database connection
try:
    db = initialize_firebase()
except Exception as e:
    logging.critical("Could not establish Firebase connection. Application cannot start.")
    raise

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
    """Handle file upload and timetable generation"""
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
            except Exception as e:
                return render_template("upload.html", 
                    message=f"Error reading Excel file: {str(e)}", 
                    error=True)

            # Store original subjects data
            try:
                subjects_data = df.to_dict('records')
                subjects_collection = db.collection('subjects')
                for subject in subjects_data:
                    subjects_collection.add(subject)
            except Exception as e:
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
            except Exception as e:
                return render_template("upload.html", 
                    message=f"Error generating timetables: {str(e)}", 
                    error=True)

            # Store timetables
            if not store_timetables(timetables):
                return render_template("upload.html", 
                    message="Error storing timetables in database", 
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
        data = request.json
        
        # Construct collection name
        collection_name = f"{data['department']}_{data['semester']}_sections"
        
        # Find the specific section document
        section_ref = db.collection(collection_name).document(data['section'])
        section_doc = section_ref.get()
        
        if not section_doc.exists:
            return jsonify({"success": False, "error": "Timetable not found"})
        
        # Get the current timetable
        timetable = section_doc.to_dict()['timetable']
        
        # Handle different update actions
        if 'new_class' in data:
            # Reschedule action
            timetable[data['day']][data['time']] = data['new_class']
        elif 'day1' in data:
            # Swap action
            temp = timetable[data['day1']][data['time1']]
            timetable[data['day1']][data['time1']] = timetable[data['day2']][data['time2']]
            timetable[data['day2']][data['time2']] = temp
        else:
            # Cancellation action
            timetable[data['day']][data['time']] = None
        
        # Update the document
        section_ref.update({
            'timetable': timetable
        })
        
        return jsonify({"success": True})
    
    except Exception as e:
        logging.error(f"Error updating timetable: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)})
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
