"""Examples of the common ways to use loops in Python.

Run with: python3 loops.py
"""


def for_over_list():
    print("1. for loop over a list")
    fruits = ["apple", "banana", "cherry"]
    for fruit in fruits:
        print("  ", fruit)


def for_with_range():
    print("2. for loop with range(start, stop, step)")
    for i in range(0, 10, 2):  # 0, 2, 4, 6, 8 -- stop is excluded
        print("  ", i)


def while_loop():
    print("3. while loop (runs until the condition is false)")
    countdown = 3
    while countdown > 0:
        print("  ", countdown)
        countdown -= 1
    print("   liftoff!")


def break_and_continue():
    print("4. break and continue")
    for n in range(10):
        if n % 2 == 0:
            continue  # skip even numbers, go to the next iteration
        if n > 7:
            break  # stop the loop entirely
        print("  ", n)


def enumerate_and_zip():
    print("5. enumerate (index + value) and zip (loop over two lists together)")
    names = ["Asha", "Ravi", "Meena"]
    scores = [91, 78, 85]
    for index, name in enumerate(names, start=1):
        print(f"   #{index}: {name}")
    for name, score in zip(names, scores):
        print(f"   {name} scored {score}")


def loop_over_dict():
    print("6. looping over a dictionary")
    prices = {"tea": 20, "coffee": 35, "juice": 50}
    for item, price in prices.items():
        print(f"   {item}: Rs {price}")


def nested_loops():
    print("7. nested loops (multiplication table)")
    for row in range(1, 4):
        line = ""
        for col in range(1, 4):
            line += f"{row * col:4}"
        print("  ", line)


def loop_else():
    print("8. for ... else (else runs only if the loop did not break)")
    target = 7
    for n in [1, 3, 5]:
        if n == target:
            print("   found it")
            break
    else:
        print(f"   {target} not found")


def comprehensions():
    print("9. comprehensions (a loop that builds a new collection)")
    squares = [n * n for n in range(1, 6)]
    evens = [n for n in range(10) if n % 2 == 0]
    lengths = {word: len(word) for word in ["loop", "python", "code"]}
    print("   squares:", squares)
    print("   evens:  ", evens)
    print("   lengths:", lengths)


def accumulate_total():
    print("10. accumulating a result")
    numbers = [4, 8, 15, 16, 23, 42]
    total = 0
    for n in numbers:
        total += n
    print("   total:", total, "| same with sum():", sum(numbers))


if __name__ == "__main__":
    for example in (
        for_over_list,
        for_with_range,
        while_loop,
        break_and_continue,
        enumerate_and_zip,
        loop_over_dict,
        nested_loops,
        loop_else,
        comprehensions,
        accumulate_total,
    ):
        example()
        print()
