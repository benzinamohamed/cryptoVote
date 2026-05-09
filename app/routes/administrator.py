from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from app import db
from app.models import (Ballot, CountedBallot, ElectionState, Voter,
                        ValidN1, N2Fingerprint, generate_code)
from app.crypto.tth import tth
from datetime import datetime

administrator_bp = Blueprint('administrator', __name__)
ADMIN_PASSWORD = 'admin123'


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('administrator.login'))
        return f(*args, **kwargs)
    return decorated


# ── Auth ──────────────────────────────────────────────────────────────

@administrator_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('administrator.dashboard'))
    if request.method == 'POST':
        if request.form.get('password', '') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('administrator.dashboard'))
        flash('Incorrect password.', 'danger')
    return render_template('administrator/login.html')


@administrator_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('main.index'))


# ── Dashboard ─────────────────────────────────────────────────────────

@administrator_bp.route('/')
@admin_required
def dashboard():
    state          = ElectionState.get()
    voters         = Voter.query.all()
    voters_created = session.pop('voters_created', None)
    ballots        = Ballot.query.all()
    counted        = CountedBallot.query.all()
    valid          = [b for b in counted if b.is_valid]

    distribution = {}
    for b in valid:
        distribution[b.vote_value] = distribution.get(b.vote_value, 0) + 1

    avg = round(sum(b.vote_value for b in valid) / len(valid), 2) if valid else None

    return render_template('administrator/dashboard.html',
                           state=state,
                           voters=voters,
                           voters_created=voters_created,
                           ballots=ballots,
                           counted=counted,
                           valid=valid,
                           distribution=sorted(distribution.items()),
                           avg=avg,
                           admin_e=current_app.config['ADMIN_E'],
                           admin_n=current_app.config['ADMIN_N'],
                           counter_n=current_app.config['COUNTER_N'],
                           counter_d=current_app.config['COUNTER_D'])


# ── Election management ───────────────────────────────────────────────

@administrator_bp.route('/setup', methods=['POST'])
@admin_required
def setup():
    state = ElectionState.get()
    if state.status != 'not_setup':
        flash('Election already initialised. Reset first.', 'warning')
        return redirect(url_for('administrator.dashboard'))

    name       = request.form.get('election_name', 'Cryptography Course Evaluation 2026').strip()
    num_voters = max(1, min(20, int(request.form.get('num_voters', 5))))

    created = []
    for i in range(num_voters):
        while True:
            n1 = generate_code()
            if not ValidN1.query.filter_by(code=n1).first():
                break
        while True:
            n2  = generate_code()
            fp  = tth(n2)
            if not N2Fingerprint.query.filter_by(fingerprint=fp).first():
                break

        db.session.add(Voter(name=f'Voter {i + 1}', n1_code=n1, n2_code=n2))
        db.session.add(ValidN1(code=n1))
        db.session.add(N2Fingerprint(fingerprint=fp))
        created.append({'name': f'Voter {i + 1}', 'n1': n1, 'n2': n2, 'fingerprint': fp})

    state.status    = 'open'
    state.name      = name
    state.opened_at = datetime.utcnow()
    db.session.commit()

    session['voters_created'] = created
    flash(f'Election "{name}" started with {num_voters} voter(s).', 'success')
    return redirect(url_for('administrator.dashboard'))


@administrator_bp.route('/close', methods=['POST'])
@admin_required
def close_election():
    state = ElectionState.get()
    if state.status != 'open':
        flash('Election is not currently open.', 'warning')
        return redirect(url_for('administrator.dashboard'))
    state.status    = 'closed'
    state.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Election closed. You can now count the ballots.', 'info')
    return redirect(url_for('administrator.dashboard'))


@administrator_bp.route('/count', methods=['POST'])
@admin_required
def count():
    state = ElectionState.get()
    if state.status != 'closed':
        flash('Election must be closed before counting.', 'warning')
        return redirect(url_for('administrator.dashboard'))

    N_c = current_app.config['COUNTER_N']
    D_c = current_app.config['COUNTER_D']
    E_a = current_app.config['ADMIN_E']
    N_a = current_app.config['ADMIN_N']

    uncounted = Ballot.query.filter_by(is_counted=False).all()
    for ballot in uncounted:
        decrypted  = pow(ballot.encrypted_vote, D_c, N_c)
        sig_check  = pow(ballot.admin_signature, E_a, N_a)
        sig_valid  = (sig_check == ballot.ballot_message)
        fp_entry   = N2Fingerprint.query.filter_by(fingerprint=tth(ballot.n2_code)).first()
        n2_valid   = fp_entry is not None
        is_valid   = sig_valid and n2_valid and (decrypted == ballot.vote_value)

        db.session.add(CountedBallot(
            ballot_id  = ballot.id,
            n2_code    = ballot.n2_code,
            vote_value = decrypted,
            sig_valid  = sig_valid,
            n2_valid   = n2_valid,
            is_valid   = is_valid,
        ))
        ballot.sig_verified = sig_valid
        ballot.n2_verified  = n2_valid
        ballot.is_valid     = is_valid
        ballot.is_counted   = True

    state.status     = 'counted'
    state.counted_at = datetime.utcnow()
    db.session.commit()
    flash(f'Tallied {len(uncounted)} ballot(s).', 'success')
    return redirect(url_for('administrator.dashboard'))


@administrator_bp.route('/publish', methods=['POST'])
@admin_required
def publish():
    state = ElectionState.get()
    if state.status != 'counted':
        flash('Count the ballots before publishing.', 'warning')
        return redirect(url_for('administrator.dashboard'))
    state.results_published = True
    state.published_at      = datetime.utcnow()
    db.session.commit()
    flash('Results published. Voters can now verify their votes.', 'success')
    return redirect(url_for('administrator.dashboard'))


@administrator_bp.route('/reset', methods=['POST'])
@admin_required
def reset():
    db.session.query(CountedBallot).delete()
    db.session.query(Ballot).delete()
    db.session.query(N2Fingerprint).delete()
    db.session.query(ValidN1).delete()
    db.session.query(Voter).delete()
    db.session.query(ElectionState).delete()
    db.session.commit()
    flash('System reset. You can start a new election.', 'success')
    return redirect(url_for('administrator.dashboard'))
