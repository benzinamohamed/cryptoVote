from . import db
from datetime import datetime
import random
import string


def generate_code(length: int = 12) -> str:
    """Generate a random 12-character alphanumeric voter code (uppercase)."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


# ---------------------------------------------------------------------------
# Election meta-state (single row)
# ---------------------------------------------------------------------------
class ElectionState(db.Model):
    __tablename__ = 'election_state'
    id         = db.Column(db.Integer, primary_key=True)
    status     = db.Column(db.String(20), default='not_setup')
    name       = db.Column(db.String(200), default='Cryptography Course Evaluation 2026')
    opened_at          = db.Column(db.DateTime, nullable=True)
    closed_at          = db.Column(db.DateTime, nullable=True)
    counted_at         = db.Column(db.DateTime, nullable=True)
    results_published  = db.Column(db.Boolean, default=False)
    published_at       = db.Column(db.DateTime, nullable=True)

    @classmethod
    def get(cls):
        state = cls.query.first()
        if state is None:
            state = cls(status='not_setup')
            db.session.add(state)
            db.session.commit()
        return state


# ---------------------------------------------------------------------------
# Voter registry (only used for the demo UI — in a real system voters keep
# their codes locally and the server never stores N2 in plain text)
# ---------------------------------------------------------------------------
class Voter(db.Model):
    __tablename__ = 'voters'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    n1_code    = db.Column(db.String(12), unique=True, nullable=False)
    n2_code    = db.Column(db.String(12), nullable=False)
    has_voted  = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Commissioner's data stores
# ---------------------------------------------------------------------------
class ValidN1(db.Model):
    """Commissioner holds the list of all valid N1 codes."""
    __tablename__ = 'valid_n1'
    id      = db.Column(db.Integer, primary_key=True)
    code    = db.Column(db.String(12), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)


class N2Fingerprint(db.Model):
    """Commissioner holds TTH(N2) fingerprints — never the raw N2 codes."""
    __tablename__ = 'n2_fingerprints'
    id          = db.Column(db.Integer, primary_key=True)
    fingerprint = db.Column(db.String(4), unique=True, nullable=False)
    is_used     = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Anonymizer's ballot box
# ---------------------------------------------------------------------------
class Ballot(db.Model):
    """
    Each row stores every intermediate crypto value for educational display.
    In a real system only encrypted_vote + admin_signature + n2_code would
    be stored; the rest is shown to let students trace the protocol.
    """
    __tablename__ = 'ballots'
    id              = db.Column(db.Integer, primary_key=True)
    # Clear-text (stored for educational transparency; in prod never stored)
    vote_value      = db.Column(db.Integer, nullable=False)   # grade 1-10
    n2_code         = db.Column(db.String(12), nullable=False)
    # Blind-signature intermediates
    blinding_k      = db.Column(db.Integer, nullable=False)   # k
    ballot_message  = db.Column(db.Integer, nullable=False)   # m = vote_value
    blinded_ballot  = db.Column(db.Integer, nullable=False)   # m' = m·k^e mod N_a
    blind_sig       = db.Column(db.Integer, nullable=False)   # m'' = (m')^d mod N_a
    admin_signature = db.Column(db.Integer, nullable=False)   # s  = m''·k⁻¹ mod N_a
    # Encryption for counter
    encrypted_vote  = db.Column(db.Integer, nullable=False)   # C  = vote^e_c mod N_c
    # Verification flags (set by counter)
    timestamp    = db.Column(db.DateTime, default=datetime.utcnow)
    sig_verified = db.Column(db.Boolean, default=False)
    n2_verified  = db.Column(db.Boolean, default=False)
    is_valid     = db.Column(db.Boolean, default=False)
    is_counted   = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Counter's tallied results
# ---------------------------------------------------------------------------
class CountedBallot(db.Model):
    __tablename__ = 'counted_ballots'
    id              = db.Column(db.Integer, primary_key=True)
    ballot_id       = db.Column(db.Integer, db.ForeignKey('ballots.id'))
    n2_code         = db.Column(db.String(12), nullable=False)
    vote_value      = db.Column(db.Integer, nullable=False)
    sig_valid       = db.Column(db.Boolean, default=False)
    n2_valid        = db.Column(db.Boolean, default=False)
    is_valid        = db.Column(db.Boolean, default=False)
    counted_at      = db.Column(db.DateTime, default=datetime.utcnow)
