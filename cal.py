# ── Simple Calculator ──────────────────────────────────────────
# This program runs in the terminal and lets the user do math.

# ── FUNCTIONS (the calculation logic) ──────────────────────────

def add(a, b):
    """Returns the sum of two numbers."""
    return a + b

def subtract(a, b):
    """Returns the difference of two numbers."""
    return a - b

def multiply(a, b):
    """Returns the product of two numbers."""
    return a * b

def divide(a, b):
    """Returns the division result, or an error if b is zero."""
    if b == 0:
        return "Error: Cannot divide by zero!"
    return a / b

# ── INPUT VALIDATION ────────────────────────────────────────────

def get_number(prompt):
    """
    Asks the user to enter a number.
    Keeps asking until they enter a valid number.
    """
    while True:
        try:
            return float(input(prompt))  # float allows decimals like 3.5
        except ValueError:
            print("  ⚠️  That's not a valid number. Please try again.")

def get_operator():
    """
    Asks the user to enter an operator (+, -, *, /).
    Keeps asking until they enter a valid one.
    """
    valid = ["+", "-", "*", "/"]
    while True:
        op = input("Enter operator (+, -, *, /): ").strip()
        if op in valid:
            return op
        print("  ⚠️  Invalid operator. Please enter +, -, *, or /")

# ── DISPLAY MENU ───────────────────────────────────────────────

def show_menu():
    """Prints the main menu options to the screen."""
    print("\n" + "="*40)
    print("       SIMPLE CALCULATOR")
    print("="*40)
    print("  1. Perform a calculation")
    print("  2. Clear screen / start fresh")
    print("  3. Exit")
    print("="*40)

# ── MAIN PROGRAM LOOP ──────────────────────────────────────────

def main():
    """
    This is the main function that runs the calculator.
    It shows a menu and repeats until the user chooses to exit.
    """
    print("\nWelcome to the Simple Calculator!")

    while True:  # This loop keeps the program running
        show_menu()
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            # ── Perform a calculation ──
            print("\n--- New Calculation ---")
            num1 = get_number("Enter first number: ")
            operator = get_operator()
            num2 = get_number("Enter second number: ")

            # Decide which function to call based on the operator
            if operator == "+":
                result = add(num1, num2)
            elif operator == "-":
                result = subtract(num1, num2)
            elif operator == "*":
                result = multiply(num1, num2)
            elif operator == "/":
                result = divide(num1, num2)

            # Show the result
            print(f"\n  ✅ Result: {num1} {operator} {num2} = {result}")

        elif choice == "2":
            # ── Clear ──
            print("\n" * 50)  # Prints many blank lines to "clear" the screen
            print("Screen cleared!")

        elif choice == "3":
            # ── Exit ──
            print("\nThank you for using the calculator. Goodbye! 👋")
            break  # This stops the while loop and ends the program

        else:
            print("  ⚠️  Invalid choice. Please enter 1, 2, or 3.")

# ── START THE PROGRAM ──────────────────────────────────────────
# This line means: "Run main() only when this file is run directly"
if __name__ == "__main__":
    main()