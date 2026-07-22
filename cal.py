
def add(a, b):

    return a + b

def subtract(a, b):

    return a - b

def multiply(a, b):

    return a * b

def divide(a, b):

    if b == 0:
        return "Error: Cannot divide by zero!"
    return a / b


def get_number(prompt):

    while True:
        try:
            return float(input(prompt)) 
        except ValueError:
            print("    That's not a valid number. Please try again.")

def get_operator():

    valid = ["+", "-", "*", "/"]
    while True:
        op = input("Enter operator (+, -, *, /): ").strip()
        if op in valid:
            return op
        print("    Invalid operator. Please enter +, -, *, or /")


def show_menu():
    print("\n" + "="*40)
    print("       SIMPLE CALCULATOR")
    print("="*40)
    print("  1. Perform a calculation")
    print("  2. Clear screen / start fresh")
    print("  3. Exit")
    print("="*40)


def main():
    print("\nWelcome to the Simple Calculator!")

    while True: 
        show_menu()
        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            print("\n--- New Calculation ---")
            num1 = get_number("Enter first number: ")
            operator = get_operator()
            num2 = get_number("Enter second number: ")

            if operator == "+":
                result = add(num1, num2)
            elif operator == "-":
                result = subtract(num1, num2)
            elif operator == "*":
                result = multiply(num1, num2)
            elif operator == "/":
                result = divide(num1, num2)

            print(f"\n   Result: {num1} {operator} {num2} = {result}")

        elif choice == "2":
            print("\n" * 50)
            print("Screen cleared!")

        elif choice == "3":
            print("\nThank you for using the calculator. Goodbye! 👋")
            break

        else:
            print("    Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()