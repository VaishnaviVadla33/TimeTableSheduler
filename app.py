from flask import Flask, request, render_template, jsonify, redirect, url_for
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
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

# Hardcoded configuration (replace with your actual values)
MONGODB_URI = "mongodb+srv://vaishnavivadla045:iHC4PDJX1fRoNFg1@cluster0.fe3gpaq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
SECRET_KEY = "your_unique_and_secret_key_here_123456"

# App configuration
app.secret_key = SECRET_KEY

# MongoDB Connection
def get_mongodb_connection():
    """Establish and return a MongoDB connection"""
    try:
        client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
        
        # Test the connection
        client.admin.command('ping')
        
        db = client['timetable_management']
        logging.info("Successfully connected to MongoDB")
        return db
    
    except Exception as e:
        logging.error(f"MongoDB Connection Error: {e}")
        logging.error(traceback.format_exc())
        raise

# Initialize database connection
try:
    db = get_mongodb_connection()
except Exception as e:
    logging.critical("Could not establish MongoDB connection. Application cannot start.")
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
    """Store timetables in a hierarchical MongoDB structure"""
    try:
        for timetable in timetables:
            dept = timetable["department"]
            sem = timetable["semester"]
            sec = timetable["section"]
            
            logging.info(f"Storing timetable - Department: {dept}, Semester: {sem}, Section: {sec}")
            
            # Store the section timetable in a dedicated collection
            section_collection = db[f"{dept}_{sem}_sections"]
            
            result = section_collection.update_one(
                {"department": dept, "semester": sem, "section": sec},
                {"$set": {
                    "department": dept,
                    "semester": sem,
                    "section": sec,
                    "timetable": timetable["days"]
                }},
                upsert=True
            )
            
            logging.info(f"Upsert result: Modified {result.modified_count}, Upserted {result.upserted_id}")
        
        return True
    except Exception as e:
        logging.error(f"Error storing timetables: {e}")
        logging.error(traceback.format_exc())
        return False

@app.route("/", methods=["GET"])
def index():
    """Landing page"""
    return render_template("index.html")

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
                db.subjects.insert_many(subjects_data)
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
        # Get all department-semester section collections
        collections = db.list_collection_names()
        timetables = []
        
        # Find collections matching the pattern of department_semester_sections
        section_collections = [col for col in collections if '_sections' in col]
        
        for collection_name in section_collections:
            # Fetch all timetables in this collection
            collection = db[collection_name]
            collection_timetables = list(collection.find())
            timetables.extend(collection_timetables)
        
        return render_template("view_timetables.html", timetables=timetables)
    
    except Exception as e:
        logging.error(f"Error loading timetables: {e}")
        logging.error(traceback.format_exc())
        return render_template("view_timetables.html", 
                             timetables=[], 
                             error_message=f"Error loading timetables: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True)