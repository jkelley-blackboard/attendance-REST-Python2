# attendance-REST-Python2

Python 2.7 based script to generate attendance records from list of course_IDs

Usage:

-- batch_attendance.py propertiesfile.ini listofcourses.csv outputfile.txt

Accepts a text file with 1 course ID per line
and returns a pipe delimited file of attendance records (outputfile.txt)

Requires role with system priviliges:

--Administrator Panel (Users) > Users > Edit > View Course Enrollments

--Course/Organization Control Panel (Tools) > Attendance > View Attendance

--Administrator Panel (Users) > Users
