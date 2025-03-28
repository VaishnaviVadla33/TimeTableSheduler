import pandas as pd
import random

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TIMINGS = ["10-11", "11-12", "12-1", "LUNCH", "2-3", "3-4"]
MAX_HOURS_PER_WEEK = 20
MAX_HOURS_PER_DAY = 6

# Read subject data from an Excel file
file_path = input("Enter the path of the subjects Excel file: ").strip()
df_subjects = pd.read_excel(file_path)

# Convert columns to meaningful names
df_subjects.columns = ["Department", "Semester", "Section", "Subject", "Theory Classes", "Practical Classes", "Tutorial Classes", "Faculty", "Total Classes"]

# Convert to appropriate data types
df_subjects["Semester"] = df_subjects["Semester"].astype(int)
df_subjects["Theory Classes"] = df_subjects["Theory Classes"].astype(int)
df_subjects["Practical Classes"] = df_subjects["Practical Classes"].astype(int)
df_subjects["Tutorial Classes"] = df_subjects["Tutorial Classes"].astype(int)

# Extract unique department, semester, and section combinations
timetable_data = {}
for _, row in df_subjects.iterrows():
    dept, sem, sec = row["Department"], row["Semester"], row["Section"]

    if dept not in timetable_data:
        timetable_data[dept] = {}
    if sem not in timetable_data[dept]:
        timetable_data[dept][sem] = {}
    if sec not in timetable_data[dept][sem]:
        timetable_data[dept][sem][sec] = {
            "subjects": [],
            "timetable": {time: {day: None for day in DAYS} for time in TIMINGS}
        }

    timetable_data[dept][sem][sec]["subjects"].append({
        "subject": row["Subject"],
        "theory": row["Theory Classes"],
        "lab": row["Practical Classes"],
        "tutorial": row["Tutorial Classes"],
        "faculty": row["Faculty"]
    })

# Faculty unavailability input
faculty_data = {}
faculty_names = df_subjects["Faculty"].unique()

for faculty in faculty_names:
    if pd.isna(faculty):
        continue
    print(f"\nEnter unavailable slots for {faculty} (Format: Day Time e.g., Monday 10-11). Type 'done' to finish:")
    unavailable_slots = []
    while True:
        slot = input("Enter unavailable slot: ").strip()
        if slot.lower() == "done":
            break
        unavailable_slots.append(slot)

    faculty_data[faculty] = {"unavailable": unavailable_slots, "assigned_slots": 0}

# Assigning slots for each section
def assign_slot(dept, sem, sec, day, time, subject, faculty):
    """ Assigns a subject to a time slot while ensuring no conflicts """
    timetable = timetable_data[dept][sem][sec]["timetable"]

    if timetable[time][day] is None and faculty_data[faculty]["assigned_slots"] < MAX_HOURS_PER_WEEK:
        timetable[time][day] = f"{subject} ({faculty})"
        faculty_data[faculty]["assigned_slots"] += 1
        return True
    return False

# Assign Theory, Lab, and Tutorial Classes separately for each section
for dept in timetable_data:
    for sem in timetable_data[dept]:
        for sec in timetable_data[dept][sem]:
            timetable = timetable_data[dept][sem][sec]["timetable"]

            for subject_data in timetable_data[dept][sem][sec]["subjects"]:
                subject, theory_count, lab_count, tutorial_count, faculty = (
                    subject_data["subject"], subject_data["theory"], subject_data["lab"], subject_data["tutorial"], subject_data["faculty"]
                )

                if pd.isna(faculty):
                    print(f"Warning: No faculty assigned for {subject} in {dept}, Semester {sem}, Section {sec}")
                    continue

                # Assign Theory Classes
                for _ in range(theory_count):
                    assigned = False
                    retry_count = 0  
                    while not assigned and retry_count < 50:
                        day = random.choice(DAYS)
                        time = random.choice([t for t in TIMINGS if t != "LUNCH"])  
                        if f"{day} {time}" not in faculty_data[faculty]["unavailable"]:
                            assigned = assign_slot(dept, sem, sec, day, time, subject, faculty)
                        retry_count += 1

                    if not assigned:
                        print(f"Warning: Could not assign {subject} theory class due to time constraints.")

                # Assign Lab Classes (2 continuous slots)
                for _ in range(lab_count):
                    assigned = False
                    retry_count = 0  
                    while not assigned and retry_count < 50:  
                        day = random.choice(DAYS)
                        start_index = random.randint(0, len(TIMINGS) - 3)  
                        time1 = TIMINGS[start_index]
                        time2 = TIMINGS[start_index + 1]

                        if time1 != "LUNCH" and time2 != "LUNCH":
                            if (f"{day} {time1}" not in faculty_data[faculty]["unavailable"] and
                                f"{day} {time2}" not in faculty_data[faculty]["unavailable"]):
                                
                                if assign_slot(dept, sem, sec, day, time1, subject + " Lab", faculty) and \
                                assign_slot(dept, sem, sec, day, time2, subject + " Lab", faculty):
                                    assigned = True

                        retry_count += 1

                    if not assigned:
                        print(f"Warning: Could not assign {subject} lab class due to time constraints.")

                # Assign Tutorial Classes
                for _ in range(tutorial_count):
                    assigned = False
                    retry_count = 0  
                    while not assigned and retry_count < 50:
                        day = random.choice(DAYS)
                        time = random.choice([t for t in TIMINGS if t != "LUNCH"])
                        if f"{day} {time}" not in faculty_data[faculty]["unavailable"]:
                            assigned = assign_slot(dept, sem, sec, day, time, subject + " Tutorial", faculty)
                        retry_count += 1

                    if not assigned:
                        print(f"Warning: Could not assign {subject} tutorial class due to time constraints.")

# Convert Timetables to DataFrames and save
for dept in timetable_data:
    for sem in timetable_data[dept]:
        for sec in timetable_data[dept][sem]:
            df = pd.DataFrame(timetable_data[dept][sem][sec]["timetable"]).T  # Transpose to make DAYS as top row

            print(f"\nGenerated Timetable for {dept}, Semester {sem}, Section {sec}:\n")
            print(df)

            filename = f"Generated_Timetable_{dept}_Sem_{sem}_Section_{sec}.xlsx"
            df.to_excel(filename, index=True)
            print(f"\nTimetable saved as '{filename}'.")
