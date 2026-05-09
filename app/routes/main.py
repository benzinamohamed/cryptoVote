from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import (ElectionState, Voter, ValidN1, N2Fingerprint,
                        Ballot, CountedBallot, generate_code)
from app.crypto.tth import tth
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    state      = ElectionState.get()
    voters     = Voter.query.all()
    ballots    = Ballot.query.count()
    counted    = CountedBallot.query.count()
    n1_total   = ValidN1.query.count()
    n1_used    = ValidN1.query.filter_by(is_used=True).count()
    return render_template('index.html',
                           state=state,
                           voters=voters,
                           ballots=ballots,
                           counted=counted,
                           n1_total=n1_total,
                           n1_used=n1_used)


@main_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    state = ElectionState.get()

    # Show voter codes that were just created
    voters_created = session.pop('voters_created', None)

    if request.method == 'POST':
        if state.status != 'not_setup':
            flash('Election is already initialised. Reset first.', 'warning')
            return redirect(url_for('main.index'))

        election_name = request.form.get('election_name', 'Cryptography Course Evaluation 2026').strip()
        num_voters    = max(1, min(20, int(request.form.get('num_voters', 5))))

        created = []
        for i in range(num_voters):
            # Generate unique N1 and N2
            while True:
                n1 = generate_code()
                if not ValidN1.query.filter_by(code=n1).first():
                    break
            while True:
                n2 = generate_code()
                fp = tth(n2)
                if not N2Fingerprint.query.filter_by(fingerprint=fp).first():
                    break

            voter = Voter(name=f'Voter {i + 1}', n1_code=n1, n2_code=n2)
            db.session.add(voter)
            db.session.add(ValidN1(code=n1))
            db.session.add(N2Fingerprint(fingerprint=fp))
            created.append({'name': f'Voter {i + 1}', 'n1': n1, 'n2': n2, 'fingerprint': fp})

        state.status    = 'open'
        state.name      = election_name
        state.opened_at = datetime.utcnow()
        db.session.commit()

        session['voters_created'] = created
        flash(f'Election "{election_name}" opened with {num_voters} registered voters.', 'success')
        return redirect(url_for('main.setup'))

    return render_template('setup.html', state=state, voters_created=voters_created)


@main_bp.route('/close_election', methods=['POST'])
def close_election():
    state = ElectionState.get()
    if state.status != 'open':
        flash('Election is not open.', 'warning')
        return redirect(url_for('main.index'))
    state.status    = 'closed'
    state.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Election has been closed. The Counter can now tally the ballots.', 'info')
    return redirect(url_for('main.index'))


@main_bp.route('/reset', methods=['POST'])
def reset():
    """Full reset — wipe all data (for demo purposes only)."""
    db.session.query(CountedBallot).delete()
    db.session.query(Ballot).delete()
    db.session.query(N2Fingerprint).delete()
    db.session.query(ValidN1).delete()
    db.session.query(Voter).delete()
    db.session.query(ElectionState).delete()
    db.session.commit()
    flash('System reset. You can set up a new election.', 'success')
    return redirect(url_for('main.index'))


@main_bp.route('/results')
def results():
    state   = ElectionState.get()
    counted = CountedBallot.query.all()
    valid   = [b for b in counted if b.is_valid]

    distribution = {}
    for b in valid:
        distribution[b.vote_value] = distribution.get(b.vote_value, 0) + 1

    avg = round(sum(b.vote_value for b in valid) / len(valid), 2) if valid else None

    # Sort by grade for display
    sorted_dist = sorted(distribution.items())

    return render_template('results.html',
                           state=state,
                           counted=counted,
                           valid=valid,
                           distribution=sorted_dist,
                           avg=avg)
