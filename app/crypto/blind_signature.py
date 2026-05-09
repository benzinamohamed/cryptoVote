"""
RSA Blind Signature Protocol
-----------------------------
Three roles: Voter (Alice), Administrator (Bob), Keys = (e, d, N)

1. blind(m, k, e, N)  →  m' = m · k^e (mod N)   [Voter hides ballot]
2. blind_sign(m', d, N)  →  m'' = (m')^d (mod N)  [Admin signs blindly]
3. unblind(m'', k, N)  →  s = m'' · k⁻¹ (mod N)  [Voter removes mask]
4. verify(m, s, e, N)  →  s^e ≡ m (mod N)         [Anyone can verify]

Because (m · k^e)^d · k⁻¹ = m^d · k^(e·d) · k⁻¹ = m^d · k · k⁻¹ = m^d (mod N)
"""
from math import gcd
from .rsa_utils import mod_inverse


def blind(m: int, k: int, e: int, n: int) -> int:
    """Voter blinds message m with blinding factor k.  m' = m · k^e (mod n)"""
    if gcd(k, n) != 1:
        raise ValueError(f"Blinding factor k={k} must be coprime to n={n}")
    return (m * pow(k, e, n)) % n


def blind_sign(m_prime: int, d: int, n: int) -> int:
    """Administrator blind-signs the masked ballot.  m'' = (m')^d (mod n)"""
    return pow(m_prime, d, n)


def unblind(m_double_prime: int, k: int, n: int) -> int:
    """Voter removes blinding factor.  s = m'' · k⁻¹ (mod n)"""
    return (m_double_prime * mod_inverse(k, n)) % n


def verify(m: int, s: int, e: int, n: int) -> bool:
    """Verify blind signature: s^e ≡ m (mod n)"""
    return pow(s, e, n) == m % n
