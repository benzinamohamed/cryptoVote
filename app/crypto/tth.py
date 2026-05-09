"""
Toy Tetragraph Hash (TTH)
Educational hash function used in the electronic voting protocol.

Algorithm:
1. Convert alphanumeric chars to integers (A=0..Z=25, digits as face value)
2. Pad to a multiple of 16 with zeros
3. Process each 16-element block as a 4×4 matrix
4. Column sums mod 26 are accumulated into a 4-element state
5. Return the 4-element state as uppercase letters
"""


def tth(text: str) -> str:
    """Compute the TTH fingerprint of an alphanumeric string. Returns 4 uppercase letters."""
    text = str(text).upper()

    nums = []
    for c in text:
        if c.isalpha():
            nums.append(ord(c) - ord('A'))   # A=0 … Z=25
        elif c.isdigit():
            nums.append(int(c))              # keep numeric face value

    if not nums:
        return 'AAAA'

    # Pad to multiple of 16
    while len(nums) % 16 != 0:
        nums.append(0)

    state = [0, 0, 0, 0]
    for block_start in range(0, len(nums), 16):
        block = nums[block_start:block_start + 16]
        for col in range(4):
            col_sum = sum(block[row * 4 + col] for row in range(4))
            state[col] = (state[col] + col_sum) % 26

    return ''.join(chr(ord('A') + s) for s in state)


def tth_steps(text: str) -> dict:
    """Return a detailed, step-by-step breakdown of the TTH computation (for the UI)."""
    text = str(text).upper()

    char_map = []
    nums = []
    for c in text:
        if c.isalpha():
            v = ord(c) - ord('A')
            nums.append(v)
            char_map.append(f"{c}={v}")
        elif c.isdigit():
            v = int(c)
            nums.append(v)
            char_map.append(f"{c}={v}")

    padded = nums[:]
    while len(padded) % 16 != 0:
        padded.append(0)

    state = [0, 0, 0, 0]
    blocks = []
    for block_start in range(0, len(padded), 16):
        block = padded[block_start:block_start + 16]
        col_details = []
        for col in range(4):
            col_vals = [block[row * 4 + col] for row in range(4)]
            col_sum = sum(col_vals) % 26
            state[col] = (state[col] + col_sum) % 26
            col_details.append({'values': col_vals, 'sum': col_sum})
        blocks.append({'block': block, 'cols': col_details})

    return {
        'input': text,
        'char_map': char_map,
        'padded': padded,
        'blocks': blocks,
        'state': state,
        'hash': ''.join(chr(ord('A') + s) for s in state),
    }
