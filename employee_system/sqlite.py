import sqlite3
# conn = sqlite3.connect("employees.db")
# print("Database created")
# conn.close()

# conn = sqlite3.connect("employees.db")
# cursor = conn.cursor()
# cursor.execute("""CREATE TABLE employees (
#                name TEXT,
#                salary INTEGER,
#                leaves INTEGER
#                )""")
# conn.commit()
# conn.close()

# conn = sqlite3.connect("employees.db")
# cursor = conn.cursor()
# cursor.execute("INSERT INTO employees VALUES ('Alice', 5000, 2)")
# cursor.execute("INSERT INTO employees VALUES ('Bob', 6000, 0)")
# cursor.execute("INSERT INTO employees VALUES ('Charlie', 5500, 5)")
# cursor.execute("INSERT INTO employees VALUES ('David', 4500, 1)")
# conn.commit()
# conn.close()

# conn = sqlite3.connect("employees.db")
# cursor = conn.cursor()
# cursor.execute("SELECT * FROM employees")
# rows = cursor.fetchall()
# for row in rows:
#     print(row)
# conn.close()

conn = sqlite3.connect("employees.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM employees")
rows = cursor.fetchall()
for row in rows:
    name = row[0]
    salary = row[1]
    leaves = row[2]
    if salary > 5000:
        salary_status = "High"
    else:
        salary_status = "Normal"
    if leaves > 3:
        leave_status = "Rejected"
    else:
        leave_status = "Approved"
    print(f"{name}: Salary Status: {salary_status}, Leave Status: {leave_status}")