from flask import Blueprint, render_template, request, jsonify, current_app
from app import db
from app.models import Voter, ValidN1, N2Fingerprint, Ballot, ElectionState
from app.crypto.blind_signature import blind, unblind, verify as blind_verify
from app.crypto.rsa_utils import mod_inverse, find_coprime
from app.crypto.tth import tth
from math import gcd

voter_bp = Blueprint('voter', __name__)


@voter_bp.route('/')
def index():
    state = ElectionState.get()
    return render_template('voter/vote.html', state=state)


@voter_bp.route('/cast', methods=['POST'])
def cast_vote():
    """
    Full voting flow orchestrated server-side (educational demo).
    In a real deployment the blinding step runs in the voter's browser.
    Returns a JSON object with every intermediate crypto value and step
    descriptions so the UI can animate the protocol.
    """
    data    = request.get_json(force=True)
    n1_code = data.get('n1_code', '').strip().upper()
    grade   = data.get('grade')

    # ── Basic validation ─────────────────────────────────────────────────
    state = ElectionState.get()
    if state.status != 'open':
        return jsonify({'success': False, 'error': 'The election is not currently open.'})

    if not n1_code:
        return jsonify({'success': False, 'error': 'N1 code is required.'})

    try:
        grade = int(grade)
        if not 1 <= grade <= 10:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Grade must be an integer between 1 and 10.'})

    steps = []

    # ── STEP 1: Voter → Administrator → Commissioner: verify N1 ──────────
    n1_entry = ValidN1.query.filter_by(code=n1_code).first()
    if not n1_entry:
        return jsonify({'success': False, 'error': f'N1 code "{n1_code}" not found in the registry.'})
    if n1_entry.is_used:
        return jsonify({'success': False, 'error': f'N1 code "{n1_code}" has already been used — double-vote prevented.'})

    # Look up the voter's N2 from their registered record
    voter_record = Voter.query.filter_by(n1_code=n1_code).first()
    if not voter_record:
        return jsonify({'success': False, 'error': f'No voter record found for N1 code "{n1_code}".'})
    n2_code = voter_record.n2_code

    steps.append({
        'step':   1,
        'title':  'Eligibility Check',
        'desc':   (f'Voter presents N₁ = <code>{n1_code}</code>. '
                   'The system verifies it is valid and unused.'),
        'result': 'N₁ is <strong>valid and unused</strong>. Right to vote granted ✓',
        'ok': True,
    })

    # ── STEP 2: Create ballot and blind it ───────────────────────────────
    N_a = current_app.config['ADMIN_N']
    E_a = current_app.config['ADMIN_E']
    D_a = current_app.config['ADMIN_D']

    m = grade  # ballot message m = grade (1-10) — fits inside N_admin=55

    # Choose random k coprime to N_admin
    k = find_coprime(N_a)

    # Blind: m' = m · k^e mod N
    k_e_mod_N = pow(k, E_a, N_a)
    m_prime   = (m * k_e_mod_N) % N_a

    steps.append({
        'step':    2,
        'title':   'Ballot Creation & Blinding',
        'desc':    (f'Voter creates ballot <strong>m = {m}</strong> (the grade) and picks '
                    f'random blinding factor <strong>k = {k}</strong> '
                    f'(coprime to N={N_a}, gcd({k},{N_a})={gcd(k,N_a)}).'),
        'formula': f"m' = m · k<sup>e</sup> (mod N) = {m} · {k}<sup>{E_a}</sup> (mod {N_a}) "
                   f"= {m} · {k_e_mod_N} (mod {N_a}) = <strong>{m_prime}</strong>",
        'result':  f'Blinded ballot m\'= {m_prime}  sent to Administrator (content hidden by blinding)',
        'ok': True,
        'data': {'m': m, 'k': k, 'e': E_a, 'N': N_a, 'k_e': k_e_mod_N, 'm_prime': m_prime},
    })

    # ── STEP 3: Administrator blind-signs ────────────────────────────────
    m_double_prime = pow(m_prime, D_a, N_a)

    steps.append({
        'step':    3,
        'title':   'Administrator Blind-Signs',
        'desc':    (f'Administrator applies private key d={D_a} to the blinded ballot '
                    f'm\'={m_prime}. The administrator does <em>not</em> know the original grade.'),
        'formula': f"m'' = (m')<sup>d</sup> (mod N) = {m_prime}<sup>{D_a}</sup> (mod {N_a}) = <strong>{m_double_prime}</strong>",
        'result':  f"Masked signature m'' = {m_double_prime}  returned to Voter",
        'ok': True,
        'data': {'m_prime': m_prime, 'd': D_a, 'N': N_a, 'm_double_prime': m_double_prime},
    })

    # ── STEP 4: Voter unblinds signature ─────────────────────────────────
    k_inv = mod_inverse(k, N_a)
    s     = (m_double_prime * k_inv) % N_a

    steps.append({
        'step':    4,
        'title':   'Voter Unblinds Signature',
        'desc':    (f'Voter computes k<sup>-1</sup> = {k}<sup>-1</sup> (mod {N_a}) = {k_inv} '
                    f'and removes the blinding factor.'),
        'formula': f"s = m'' · k<sup>-1</sup> (mod N) = {m_double_prime} · {k_inv} (mod {N_a}) = <strong>{s}</strong>",
        'result':  f'Real signature s = {s}',
        'ok': True,
        'data': {'m_double_prime': m_double_prime, 'k_inv': k_inv, 'N': N_a, 's': s},
    })

    # ── STEP 5: Signature verification ───────────────────────────────────
    sig_check = pow(s, E_a, N_a)
    sig_ok    = (sig_check == m)

    steps.append({
        'step':    5,
        'title':   'Signature Verification',
        'desc':    f'Anyone can verify: s<sup>e</sup> (mod N) must equal m.',
        'formula': f"s<sup>e</sup> mod N = {s}<sup>{E_a}</sup> mod {N_a} = {sig_check}",
        'result':  (f'<strong>{sig_check} {"==" if sig_ok else "≠"} {m}</strong> → '
                    f'Signature {"valid ✓" if sig_ok else "INVALID ✗"}'),
        'ok': sig_ok,
        'data': {'s': s, 'e': E_a, 'N': N_a, 'result': sig_check, 'expected': m},
    })

    if not sig_ok:
        return jsonify({'success': False, 'error': 'Signature verification failed', 'steps': steps})

    # ── STEP 6: Compute TTH(N2) fingerprint ──────────────────────────────
    n2_fp    = tth(n2_code)
    fp_entry = N2Fingerprint.query.filter_by(fingerprint=n2_fp, is_used=False).first()

    steps.append({
        'step':    6,
        'title':   'TTH Hash of N₂',
        'desc':    f'Voter computes the TTH fingerprint of N₂ = {n2_code}.',
        'formula': f'TTH({n2_code}) = <strong>{n2_fp}</strong>',
        'result':  (f'Fingerprint {n2_fp} is '
                    + ('<strong>in the Commissioner\'s list ✓</strong>'
                       if fp_entry else '<strong>NOT in the Commissioner\'s list ✗</strong>')),
        'ok': fp_entry is not None,
        'data': {'n2': n2_code, 'fingerprint': n2_fp},
    })

    if not fp_entry:
        return jsonify({'success': False,
                        'error': f'N2 fingerprint {n2_fp} is not in the Commissioner\'s registry.',
                        'steps': steps})

    # ── STEP 7: Encrypt vote with Counter's public key ───────────────────
    N_c = current_app.config['COUNTER_N']
    E_c = current_app.config['COUNTER_E']

    encrypted_vote = pow(m, E_c, N_c)

    steps.append({
        'step':    7,
        'title':   'Vote Encryption for Counter',
        'desc':    (f'Voter encrypts grade using Counter\'s public key '
                    f'(e={E_c}, N={N_c}).  This is the "envelope".'),
        'formula': f'C = m<sup>e</sup> (mod N) = {m}<sup>{E_c}</sup> (mod {N_c}) = <strong>{encrypted_vote}</strong>',
        'result':  f'Encrypted vote C = {encrypted_vote}',
        'ok': True,
        'data': {'m': m, 'e': E_c, 'N': N_c, 'C': encrypted_vote},
    })

    # ── STEP 8: Voter → Anonymizer ───────────────────────────────────────
    steps.append({
        'step':   8,
        'title':  'Submit to Anonymizer',
        'desc':   (f'Voter sends (N1={n1_code}, encrypted_vote={encrypted_vote}, '
                   f'signature={s}, N₂={n2_code}) to the Anonymizer.'),
        'result': 'Anonymizer verifies N1 with Commissioner…',
        'ok': True,
    })

    # Anonymizer verifies N1 with commissioner → marks N1 used
    n1_entry.is_used = True

    # N2 fingerprint marked used (prevents same N2 being reused)
    fp_entry.is_used = True

    steps.append({
        'step':   9,
        'title':  'Commissioner Marks N1 as Used',
        'desc':   'Commissioner removes N1 from the valid list — prevents double voting.',
        'result': f'N1 = {n1_code} consumed ✓',
        'ok': True,
    })

    # Store ballot in anonymizer's box
    ballot = Ballot(
        vote_value      = grade,
        n2_code         = n2_code,
        blinding_k      = k,
        ballot_message  = m,
        blinded_ballot  = m_prime,
        blind_sig       = m_double_prime,
        admin_signature = s,
        encrypted_vote  = encrypted_vote,
    )
    db.session.add(ballot)

    # Mark voter as having voted (UI only)
    voter = Voter.query.filter_by(n1_code=n1_code).first()
    if voter:
        voter.has_voted = True

    db.session.commit()

    steps.append({
        'step':   10,
        'title':  'Ballot Recorded',
        'desc':   'Anonymizer stores the encrypted ballot in the ballot box.',
        'result': f'<strong>Vote recorded! Ballot #{ballot.id}</strong>',
        'ok': True,
    })

    return jsonify({'success': True, 'steps': steps, 'ballot_id': ballot.id})
