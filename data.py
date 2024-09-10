def calculate_salary(row):
    student_id = row['Student id'].strip().lower()  # To identify the demo class using student ID
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    # Handle demo classes based on the 'Student id'
    if 'demo class i - x' in student_id:
        return hours * 150
    elif 'demo class xi - xii' in student_id:
        return hours * 180

    # Handle paid classes
    elif class_type.startswith("paid"):
        return hours * 4 * 100

    # Handle regular, additional, exam types based on syllabus and class level
    else:
        class_level = row['Class'].strip().lower()  # Don't convert to int yet
        
        # Handle the 'Lkg' case separately
        if class_level == 'lkg':
            return hours * 120
        
        # Convert to integer for other cases
        if class_level.isdigit():
            class_level = int(class_level)
            
            if syllabus in ['igcse', 'ib']:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 7:
                    return hours * 150
                elif 8 <= class_level <= 10:
                    return hours * 170
                elif 11 <= class_level <= 13:
                    return hours * 200
            else:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 10:
                    return hours * 150
                elif 11 <= class_level <= 12:
                    return hours * 180

    return 0  # Default case if no condition matches
