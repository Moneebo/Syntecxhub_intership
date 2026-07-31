import json
import os
from pathlib import Path

DATA_FILE = "students.json"


class Student:
    def __init__(self, student_id: str, name: str, grade: float):
        self.student_id = student_id.strip().upper()
        self.name = name.strip().title()
        self.grade = float(grade)

    def to_dict(self) -> dict:
        return {
            "id": self.student_id,
            "name": self.name,
            "grade": self.grade,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        return cls(data["id"], data["name"], data["grade"])

    def grade_letter(self) -> str:
        g = self.grade
        if g >= 90: return "A"
        if g >= 80: return "B"
        if g >= 70: return "C"
        if g >= 60: return "D"
        return "F"

    def __str__(self) -> str:
        return (
            f"  ID    : {self.student_id}\n"
            f"  Name  : {self.name}\n"
            f"  Grade : {self.grade:.1f} ({self.grade_letter()})"
        )


class StudentManager:
    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self.students: dict[str, Student] = {}
        self._load()


    def _load(self):
        if Path(self.filepath).exists():
            with open(self.filepath, "r") as f:
                raw = json.load(f)
            self.students = {r["id"]: Student.from_dict(r) for r in raw}

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump([s.to_dict() for s in self.students.values()], f, indent=2)


    def add(self, student_id: str, name: str, grade: float) -> tuple[bool, str]:
        sid = student_id.strip().upper()
        if sid in self.students:
            return False, f"ID '{sid}' already exists."
        if not (0 <= float(grade) <= 100):
            return False, "Grade must be between 0 and 100."
        self.students[sid] = Student(sid, name, grade)
        self._save()
        return True, f"Student '{name}' added successfully."

    def update(self, student_id: str, name: str = None, grade: float = None) -> tuple[bool, str]:
        sid = student_id.strip().upper()
        if sid not in self.students:
            return False, f"No student with ID '{sid}'."
        s = self.students[sid]
        if name:
            s.name = name.strip().title()
        if grade is not None:
            if not (0 <= float(grade) <= 100):
                return False, "Grade must be between 0 and 100."
            s.grade = float(grade)
        self._save()
        return True, f"Student '{sid}' updated."

    def delete(self, student_id: str) -> tuple[bool, str]:
        sid = student_id.strip().upper()
        if sid not in self.students:
            return False, f"No student with ID '{sid}'."
        name = self.students.pop(sid).name
        self._save()
        return True, f"Student '{name}' deleted."

    def get(self, student_id: str):
        return self.students.get(student_id.strip().upper())

    def list_all(self) -> list[Student]:
        return sorted(self.students.values(), key=lambda s: s.student_id)

    def search(self, query: str) -> list[Student]:
        q = query.lower()
        return [s for s in self.students.values()
                if q in s.name.lower() or q in s.student_id.lower()]



DIVIDER = "─" * 48

def header(title: str):
    print(f"\n{'═' * 48}")
    print(f"  {title}")
    print('═' * 48)

def success(msg: str): print(f"\n  ✓  {msg}")
def error(msg: str):   print(f"\n  ✗  {msg}")

def print_student(s: Student):
    print(DIVIDER)
    print(s)

def print_list(students: list[Student], title: str = "Students"):
    header(title)
    if not students:
        print("  (no records found)")
        return
    print(f"  {'ID':<12} {'Name':<22} {'Grade':>6}  {'Letter':>6}")
    print(DIVIDER)
    for s in students:
        print(f"  {s.student_id:<12} {s.name:<22} {s.grade:>6.1f}  {s.grade_letter():>6}")
    print(DIVIDER)
    print(f"  Total: {len(students)} student(s)")



def prompt(label: str, required: bool = True) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val or not required:
            return val
        print("  (field required)")

def prompt_float(label: str) -> float | None:
    while True:
        raw = input(f"  {label}: ").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a valid number.")

def action_add(mgr: StudentManager):
    header("Add Student")
    sid   = prompt("Student ID")
    name  = prompt("Full Name")
    grade = prompt_float("Grade (0–100)")
    if grade is None:
        error("Grade is required.")
        return
    ok, msg = mgr.add(sid, name, grade)
    (success if ok else error)(msg)

def action_update(mgr: StudentManager):
    header("Update Student")
    sid = prompt("Student ID to update")
    s = mgr.get(sid)
    if not s:
        error(f"No student with ID '{sid.upper()}'.")
        return
    print(f"\n  Current record:\n{s}\n")
    print("  (leave blank to keep current value)")
    name  = prompt("New Name", required=False)
    grade = prompt_float("New Grade (0–100) [blank = keep]")
    ok, msg = mgr.update(sid, name or None, grade)
    (success if ok else error)(msg)

def action_delete(mgr: StudentManager):
    header("Delete Student")
    sid = prompt("Student ID to delete")
    s = mgr.get(sid)
    if not s:
        error(f"No student with ID '{sid.upper()}'.")
        return
    print(f"\n{s}\n")
    confirm = input("  Confirm delete? (yes/no): ").strip().lower()
    if confirm in ("yes", "y"):
        ok, msg = mgr.delete(sid)
        (success if ok else error)(msg)
    else:
        print("  Delete cancelled.")

def action_view(mgr: StudentManager):
    header("View Student")
    sid = prompt("Student ID")
    s = mgr.get(sid)
    if s:
        print_student(s)
    else:
        error(f"No student with ID '{sid.upper()}'.")

def action_list(mgr: StudentManager):
    print_list(mgr.list_all(), "All Students")

def action_search(mgr: StudentManager):
    header("Search Students")
    q = prompt("Search (name or ID)")
    results = mgr.search(q)
    print_list(results, f"Results for '{q}'")



MENU = [
    ("Add student",    action_add),
    ("Update student", action_update),
    ("Delete student", action_delete),
    ("View student",   action_view),
    ("List all",       action_list),
    ("Search",         action_search),
]

def main():
    mgr = StudentManager()
    print("\n" + "═" * 48)
    print("   Student Management System  •  Syntecxhub")
    print("═" * 48)

    while True:
        print(f"\n  {'─ MENU ':─<42}")
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}.  {label}")
        print(f"  0.  Exit")
        print()

        choice = input("  Choose an option: ").strip()
        if choice == "0":
            print("\n  Goodbye!\n")
            break
        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            MENU[int(choice) - 1][1](mgr)
        else:
            error("Invalid option. Please choose 0–6.")


if __name__ == "__main__":
    main()
