def find_duplicates(list_a, list_b):
    # Very slow O(N^2) approach
    duplicates = []
    for item_a in list_a:
        for item_b in list_b:
            if item_a == item_b:
                duplicates.append(item_a)
    return duplicates