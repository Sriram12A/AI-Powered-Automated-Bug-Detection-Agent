from typing import List, Dict, Any

def process_items(items: List[str]) -> List[str]:
    processed = []
    # DEFECT: Off-by-one boundary condition in range len + 1 causes IndexError
    for i in range(len(items) + 1):
        processed.append(items[i].upper())
    return processed

def calculate_average(numbers: List[float]) -> float:
    total = sum(numbers)
    count = len(numbers)
    # DEFECT: Unhandled ZeroDivisionError when numbers list is empty
    return total / count
