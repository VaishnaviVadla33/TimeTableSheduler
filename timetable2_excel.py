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

# Ignoring the first row (header already used)
df_subjects = df_subjects.iloc[0:].reset_index(drop=True)

# Convert columns to meaningful names
df_subjects.columns = ["Year", "Section", "Subject", "Theory Classes", "Practical Classes", "Faculty"]

# Convert to appropriate data types
df_subjects["Year"] = df_subjects["Year"].astype(int)
df_subjects["Theory Classes"] = df_subjects["Theory Classes"].astype(int)
df_subjects["Practical Classes"] = df_subjects["Practical Classes"].astype(int)

# Extract unique years and sections
years = {}
for _, row in df_subjects.iterrows():
    year = row["Year"]
    section = row["Section"]

    if year not in years:
        years[year] = {}

    if section not in years[year]:
        years[year][section] = {"subjects": [], "timetable": {time: {day: None for day in DAYS} for time in TIMINGS}}

    years[year][section]["subjects"].append({
        "subject": row["Subject"],
        "theory": row["Theory Classes"],
        "lab": row["Practical Classes"],
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
def assign_slot(year, section, day, time, subject, faculty):
    """ Assigns a subject to a time slot while ensuring no conflicts """
    timetable = years[year][section]["timetable"]

    if timetable[time][day] is None and faculty_data[faculty]["assigned_slots"] < MAX_HOURS_PER_WEEK:
        timetable[time][day] = f"{subject} ({faculty})"
        faculty_data[faculty]["assigned_slots"] += 1
        return True
    return False

# Assign Theory and Lab Classes separately for each section
for year in years:
    for section in years[year]:
        timetable = years[year][section]["timetable"]

        for subject_data in years[year][section]["subjects"]:
            subject, theory_count, lab_count, faculty = (
                subject_data["subject"], subject_data["theory"], subject_data["lab"], subject_data["faculty"]
            )

            if pd.isna(faculty):
                print(f"Warning: No faculty assigned for {subject} in Year {year} Section {section}")
                continue

            # Assign Theory Classes
            for _ in range(theory_count):
                assigned = False
                retry_count = 0  
                while not assigned and retry_count < 50:
                    day = random.choice(DAYS)
                    time = random.choice([t for t in TIMINGS if t != "LUNCH"])  
                    if f"{day} {time}" not in faculty_data[faculty]["unavailable"]:
                        assigned = assign_slot(year, section, day, time, subject, faculty)
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
                            
                            if assign_slot(year, section, day, time1, subject + " Lab", faculty) and \
                               assign_slot(year, section, day, time2, subject + " Lab", faculty):
                                assigned = True

                    retry_count += 1

                if not assigned:
                    print(f"Warning: Could not assign {subject} lab class due to time constraints.")

# Convert Timetables to DataFrames and save
for year in years:
    for section in years[year]:
        df = pd.DataFrame(years[year][section]["timetable"]).T  # Transpose to make DAYS as top row

        print(f"\nGenerated Timetable for Year {year} Section {section}:\n")
        print(df)

        filename = f"Generated_Timetable_Year_{year}_Section_{section}.xlsx"
        df.to_excel(filename, index=True)
        print(f"\nTimetable saved as '{filename}'.")
