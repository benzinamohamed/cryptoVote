import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ensta-crypto-voting-2026')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///evoting.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Administrator RSA keys — Exercise 2: N=55, e=27
    # φ(55) = φ(5×11) = 40  →  d = 27⁻¹ mod 40 = 3  (27×3=81=2×40+1)
    ADMIN_N = 55
    ADMIN_E = 27
    ADMIN_D = 3

    # Counter RSA keys — Exercise 4: e=3, N=583
    # 583=11×53, φ(583)=520  →  d = 3⁻¹ mod 520 = 347  (3×347=1041=2×520+1)
    COUNTER_N = 583
    COUNTER_E = 3
    COUNTER_D = 347
