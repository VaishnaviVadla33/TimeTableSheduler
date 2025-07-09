# Webathon Timetable Generator

A Flask web application for uploading subject data from Excel files, generating automated timetables, and managing them with features like rescheduling, swapping, and canceling classes. The application uses Firebase Firestore for data storage and supports Excel downloads of generated timetables.

## ✨ Features

- Upload subject details via Excel (.xlsx) files
- Auto-generate weekly timetables based on subject data
- Store and manage timetables using Firebase Firestore
- Interactive timetable management (reschedule, swap, cancel classes)
- Download all timetables in Excel format via ZIP file
- Responsive web interface with real-time updates

## 📁 Project Structure

```
WEBATHON_TIMETABLE/
│
├── app1.py                    # Main Flask backend
├── firebase_credentials.json  # Firebase service account key
├── firebase_test.py           # Firebase connection test script
├── requirements.txt           # Python dependencies
├── app.log                    # Application log file
├── .gitignore                 # Git ignore file
├── static/                    # CSS and static files
├── templates/                 # HTML templates (Jinja2)
│   ├── dashboard.html
│   ├── upload.html
│   ├── index.html
│   └── view_timetables.html
└── uploads/                   # Uploaded Excel files
    └── subjects2.xlsx         # Sample upload file
```

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/VaishnaviVadla33/TimeTableSheduler.git
cd TimeTableSheduler
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python -m venv myenv

# Activate the virtual environment:
# On Windows:
myenv\Scripts\activate

# On macOS/Linux:
source myenv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```


## 🔥 Firebase Setup

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Navigate to **Firestore Database** and create a new database (start in test mode)
4. Go to **Project Settings > Service Accounts**
5. Click "Generate New Private Key" and download the JSON file
6. Rename the downloaded file to `firebase_credentials.json` and place it in the project root directory

## 🚀 How to Run

1. **Activate virtual environment** (if you created one):
   ```bash
   # On Windows:
   myenv\Scripts\activate
   
   # On macOS/Linux:
   source myenv/bin/activate
   ```

2. **Start the application**:
   ```bash
   python app1.py
   ```

3. **Open your browser** and navigate to: `http://127.0.0.1:5000`

## 📊 Uploading Subjects

### Excel File Format

Check the sample Excel file `subjects2.xlsx` in the `uploads/` folder to understand the required format and structure your data accordingly.

### Steps to Upload

1. Navigate to the upload page: `http://127.0.0.1:5000/upload`

2. Upload your Excel file following the same format as the sample file

3. Timetables will be generated automatically upon successful upload

### Managing Timetables

1. Navigate to `/dashboard` in your browser
2. Click on any class cell in the timetable to access management options:
   - **Reschedule**: Edit the selected class
   - **Swap**: Exchange with another class
   - **Cancel**: Remove the class from the timetable

### Downloading Timetables

1. Go to the upload page (`/upload`)
2. Click the "Download All Timetables" button
3. A ZIP file containing individual Excel timetables will be downloaded automatically

### File Naming Convention

Each Excel file follows this naming pattern:
```
Timetable_<Department>_Sem<Number>_Sec<Letter>.xlsx
```

Example: `Timetable_CSE_Sem3_SecA.xlsx`

## 🔧 Developer Notes

### Database Structure

Timetables are stored in Firestore collections with the naming pattern: `{Department}_{Semester}_sections`

Each document within a section collection follows this structure:

```json
{
  "department": "CSE",
  "semester": "3",
  "section": "a",
  "timetable": {
    "Monday": {
      "10-11": "Subject Name",
      "11-12": "Another Subject"
    },
    "Tuesday": {
      "10-11": "Subject Name"
    }
  }
}
```

### Key Dependencies

```
Flask==2.3.3
pandas
firebase-admin
openpyxl==3.1.5
XlsxWriter==3.2.0
```

Install all dependencies with:
```bash
pip install -r requirements.txt
```

## 📝 Usage Notes

- The application runs locally on your machine
- Always activate your virtual environment before running the app (if using one)
- Check browser console and server logs for troubleshooting
- Ensure Firebase credentials are properly configured before first use
- The application supports multiple departments, semesters, and sections

## 🤝 Contributing

Developed for the Webathon event. Feel free to fork the repository and submit pull requests for improvements.

## Support

If you encounter any issues:
1. Check the browser console for client-side errors
2. Review server logs for backend issues
3. Verify Firebase configuration and credentials
4. Ensure all dependencies are properly installed
