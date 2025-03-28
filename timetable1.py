import pandas as pd
import random

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
TIMINGS = ["10-11", "11-12", "12-1", "LUNCH", "2-3", "3-4"]
MAX_HOURS_PER_WEEK = 20
MAX_HOURS_PER_DAY = 6

years = {2: {}, 3: {}}  # Separate timetables for 2nd & 3rd Year
faculty_data = {}

# Get subject details
year_subject_count = {2: int(input("Enter number of subjects for 2nd Year: ")),
                      3: int(input("Enter number of subjects for 3rd Year: "))}

for year in years:
    print(f"\nEnter details for Year {year}:")
    total_subjects = year_subject_count[year]
    subjects = []

    for _ in range(total_subjects):
        subject_name = input(f"Enter subject name: ")
        theory_classes = int(input(f"How many theory classes for {subject_name} per week? "))
        lab_classes = int(input(f"How many lab sessions (each takes 2 slots) for {subject_name} per week? "))
        subjects.append({"subject": subject_name, "theory": theory_classes, "lab": lab_classes})

    years[year]["subjects"] = subjects

# Get faculty details
num_faculty = int(input("\nEnter number of faculty members: "))

for _ in range(num_faculty):
    faculty_name = input("\nEnter faculty name: ")
    
    num_subjects = int(input(f"Enter number of subjects for {faculty_name}: "))
    subjects_handled = []
    
    for _ in range(num_subjects):
        subject_name = input(f"Enter subject name for {faculty_name}: ")
        subjects_handled.append(subject_name)
    
    unavailable_slots = []
    num_unavailable = int(input(f"Enter number of unavailable slots for {faculty_name}: "))
    
    for _ in range(num_unavailable):
        slot = input("Enter unavailable slot (format: Day Time e.g., Monday 10-11): ")
        unavailable_slots.append(slot)
    
    faculty_data[faculty_name] = {
        "subjects": subjects_handled,
        "unavailable": unavailable_slots,
        "assigned_slots": 0
    }

# Initialize separate timetables for 2nd and 3rd years
for year in years:
    years[year]["timetable"] = {time: {day: None for day in DAYS} for time in TIMINGS}
    years[year]["faculty_hours"] = {name: {"weekly": 0, "daily": {day: 0 for day in DAYS}} for name in faculty_data}

def assign_slot(year, day, time, subject, faculty):
    """ Assigns a subject to a time slot while ensuring no conflicts """
    timetable = years[year]["timetable"]
    faculty_hours = years[year]["faculty_hours"]

    if timetable[time][day] is None and faculty_hours[faculty]["weekly"] < MAX_HOURS_PER_WEEK:
        if faculty_hours[faculty]["daily"][day] < MAX_HOURS_PER_DAY:
            timetable[time][day] = f"{subject} ({faculty})"
            faculty_hours[faculty]["weekly"] += 1
            faculty_hours[faculty]["daily"][day] += 1
            return True
    return False

# Assign Theory and Lab Classes separately for each year
for year in years:
    timetable = years[year]["timetable"]
    faculty_hours = years[year]["faculty_hours"]

    for subject in years[year]["subjects"]:
        faculty_assigned = None
        for faculty, data in faculty_data.items():
            if subject["subject"] in data["subjects"]:
                faculty_assigned = faculty
                break

        if not faculty_assigned:
            print(f"Warning: No faculty assigned for {subject['subject']} in Year {year}")
            continue

        # Assign Theory Classes
        for _ in range(subject["theory"]):
            assigned = False
            retry_count = 0  
            while not assigned and retry_count < 50:  
                day = random.choice(DAYS)
                time = random.choice([t for t in TIMINGS if t != "LUNCH"])  # Avoid lunch slot
                if f"{day} {time}" not in faculty_data[faculty_assigned]["unavailable"]:
                    assigned = assign_slot(year, day, time, subject["subject"], faculty_assigned)
                retry_count += 1

            if not assigned:
                print(f"Warning: Could not assign {subject['subject']} theory class due to time constraints.")

        # Assign Lab Classes (2 continuous slots)
        for _ in range(subject["lab"]):
            assigned = False
            retry_count = 0  
            while not assigned and retry_count < 50:  
                day = random.choice(DAYS)
                start_index = random.randint(0, len(TIMINGS) - 3)  # Prevent out of range issues
                time1 = TIMINGS[start_index]
                time2 = TIMINGS[start_index + 1]

                # Ensure lab is assigned in continuous slots and avoids lunch break
                if time1 != "LUNCH" and time2 != "LUNCH":
                    if (f"{day} {time1}" not in faculty_data[faculty_assigned]["unavailable"] and
                        f"{day} {time2}" not in faculty_data[faculty_assigned]["unavailable"]):
                        
                        if assign_slot(year, day, time1, subject["subject"] + " Lab", faculty_assigned) and \
                           assign_slot(year, day, time2, subject["subject"] + " Lab", faculty_assigned):
                            assigned = True

                retry_count += 1

            if not assigned:
                print(f"Warning: Could not assign {subject['subject']} lab class due to time constraints.")

# Convert Timetables to DataFrames and save
for year in years:
    df = pd.DataFrame(years[year]["timetable"])
    print(f"\nGenerated Timetable for Year {year}:\n")
    print(df)
    df.to_excel(f"Generated_Timetable_Year_{year}.xlsx", index=True)
    print(f"\nTimetable saved as 'Generated_Timetable_Year_{year}.xlsx'.")
