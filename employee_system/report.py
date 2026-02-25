from openpyxl import Workbook
def create_report(data):
    wb = Workbook()
    sheet = wb.active
    sheet.append(["Name", "Salary Status", "Leave Status"])
    for emp in data:
        sheet.append([emp["name"], emp["salary_status"], emp["leave_status"]])
    wb.save("employee_report.xlsx")