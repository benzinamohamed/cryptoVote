from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import Ballot, ElectionState

anonymizer_bp = Blueprint('anonymizer', __name__)


@anonymizer_bp.route('/')
def dashboard():
    state   = ElectionState.get()
    ballots = Ballot.query.order_by(Ballot.timestamp.desc()).all()
    return render_template('anonymizer/dashboard.html',
                           state=state,
                           ballots=ballots)


@anonymizer_bp.route('/api/ballots')
def api_ballots():
    ballots = Ballot.query.all()
    return jsonify([{
        'id':             b.id,
        'encrypted_vote': b.encrypted_vote,
        'signature':      b.admin_signature,
        'timestamp':      b.timestamp.isoformat(),
    } for b in ballots])
