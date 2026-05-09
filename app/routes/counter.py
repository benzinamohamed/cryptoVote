from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app import db
from app.models import Ballot, CountedBallot, N2Fingerprint, ElectionState
from app.crypto.tth import tth
from datetime import datetime

counter_bp = Blueprint('counter', __name__)


@counter_bp.route('/')
def dashboard():
    state   = ElectionState.get()
    ballots = Ballot.query.all()
    counted = CountedBallot.query.all()

    distribution = {}
    valid_votes  = [b for b in counted if b.is_valid]
    for b in valid_votes:
        distribution[b.vote_value] = distribution.get(b.vote_value, 0) + 1
    sorted_dist = sorted(distribution.items())

    avg = round(sum(b.vote_value for b in valid_votes) / len(valid_votes), 2) if valid_votes else None

    return render_template('counter/dashboard.html',
                           state=state,
                           ballots=ballots,
                           counted=counted,
                           distribution=sorted_dist,
                           avg=avg,
                           counter_n=current_app.config['COUNTER_N'],
                           counter_e=current_app.config['COUNTER_E'],
                           counter_d=current_app.config['COUNTER_D'],
                           admin_e=current_app.config['ADMIN_E'],
                           admin_n=current_app.config['ADMIN_N'])


@counter_bp.route('/count', methods=['POST'])
def count():
    state = ElectionState.get()
    if state.status != 'closed':
        flash('The election must be closed before counting.', 'warning')
        return redirect(url_for('counter.dashboard'))

    N_c = current_app.config['COUNTER_N']
    D_c = current_app.config['COUNTER_D']
    E_a = current_app.config['ADMIN_E']
    N_a = current_app.config['ADMIN_N']

    uncounted = Ballot.query.filter_by(is_counted=False).all()
    if not uncounted:
        flash('All ballots have already been counted.', 'info')
        return redirect(url_for('counter.dashboard'))

    for ballot in uncounted:
        # 1. Decrypt with counter's private key
        decrypted = pow(ballot.encrypted_vote, D_c, N_c)

        # 2. Verify admin blind signature: s^e mod N == m
        sig_check = pow(ballot.admin_signature, E_a, N_a)
        sig_valid = (sig_check == ballot.ballot_message)

        # 3. Verify N2 fingerprint with Commissioner
        fp       = tth(ballot.n2_code)
        fp_entry = N2Fingerprint.query.filter_by(fingerprint=fp).first()
        n2_valid = fp_entry is not None

        is_valid = sig_valid and n2_valid and (decrypted == ballot.vote_value)

        cb = CountedBallot(
            ballot_id  = ballot.id,
            n2_code    = ballot.n2_code,
            vote_value = decrypted,
            sig_valid  = sig_valid,
            n2_valid   = n2_valid,
            is_valid   = is_valid,
        )
        db.session.add(cb)

        ballot.sig_verified = sig_valid
        ballot.n2_verified  = n2_valid
        ballot.is_valid     = is_valid
        ballot.is_counted   = True

    state.status     = 'counted'
    state.counted_at = datetime.utcnow()
    db.session.commit()

    flash(f'Successfully tallied {len(uncounted)} ballot(s).', 'success')
    return redirect(url_for('counter.dashboard'))


@counter_bp.route('/publish', methods=['POST'])
def publish():
    state = ElectionState.get()
    if state.status != 'counted':
        flash('Results must be counted before publishing.', 'warning')
        return redirect(url_for('counter.dashboard'))
    state.results_published = True
    state.published_at = datetime.utcnow()
    db.session.commit()
    flash('Results have been published. Voters can now verify their votes.', 'success')
    return redirect(url_for('counter.dashboard'))
