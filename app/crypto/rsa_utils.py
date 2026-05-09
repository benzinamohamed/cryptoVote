"""
Pure-Python RSA utilities used by the voting protocol.
Uses Python's built-in pow(base, exp, mod) for fast modular exponentiation.
"""
from math import gcd
import random


def extended_gcd(a: int, b: int):
    """Return (gcd, x, y) such that a*x + b*y = gcd."""
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x


def mod_inverse(a: int, m: int) -> int:
    """Modular multiplicative inverse of a modulo m (requires gcd(a,m)=1)."""
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        raise ValueError(f"gcd({a}, {m}) = {g} ≠ 1 — inverse does not exist")
    return x % m


def find_coprime(n: int) -> int:
    """Return a random integer k in [2, n-1] with gcd(k, n) = 1."""
    while True:
        k = random.randint(2, n - 1)
        if gcd(k, n) == 1:
            return k


def rsa_encrypt(m: int, e: int, n: int) -> int:
    """c = m^e mod n"""
    if not 0 <= m < n:
        raise ValueError(f"Message {m} must satisfy 0 ≤ m < {n}")
    return pow(m, e, n)


def rsa_decrypt(c: int, d: int, n: int) -> int:
    """m = c^d mod n"""
    return pow(c, d, n)


def rsa_sign(m: int, d: int, n: int) -> int:
    """s = m^d mod n  (sign with private key)"""
    if not 0 <= m < n:
        raise ValueError(f"Message {m} must satisfy 0 ≤ m < {n}")
    return pow(m, d, n)


def rsa_verify(s: int, e: int, n: int) -> int:
    """m = s^e mod n  (verify with public key)"""
    return pow(s, e, n)
