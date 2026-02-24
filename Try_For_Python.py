import csv
with open("leaves.csv", "r") as file , open("report.csv", "w") as report:
    reader = csv.DictReader(file)
    fieldnames = ["name","status"]
    writer = csv.DictWriter(report, fieldnames=fieldnames)
    for row in reader:
        name = row["name"]
        leave = int(row["leave"])
        status = "Approved" if leave > 0 else "Rejected"
        writer.writerow({"name": name, "status": status})