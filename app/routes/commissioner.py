from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import ValidN1, N2Fingerprint, ElectionState
from app.crypto.tth import tth, tth_steps

commissioner_bp = Blueprint('commissioner', __name__)


@commissioner_bp.route('/')
def dashboard():
    state        = ElectionState.get()
    n1_codes     = ValidN1.query.all()
    fingerprints = N2Fingerprint.query.all()
    return render_template('commissioner/dashboard.html',
                           state=state,
                           n1_codes=n1_codes,
                           fingerprints=fingerprints)


# ── Internal APIs called by Administrator and Anonymizer ──────────────────

@commissioner_bp.route('/api/verify_n1', methods=['POST'])
def api_verify_n1():
    code  = request.json.get('code', '').strip().upper()
    entry = ValidN1.query.filter_by(code=code).first()
    if not entry:
        return jsonify({'valid': False, 'reason': 'code not found'})
    if entry.is_used:
        return jsonify({'valid': False, 'reason': 'already used — double-vote attempt'})
    return jsonify({'valid': True})


@commissioner_bp.route('/api/use_n1', methods=['POST'])
def api_use_n1():
    """Mark N1 as consumed (called by Anonymizer after accepting a ballot)."""
    code  = request.json.get('code', '').strip().upper()
    entry = ValidN1.query.filter_by(code=code, is_used=False).first()
    if not entry:
        return jsonify({'success': False, 'reason': 'not found or already used'})
    entry.is_used = True
    db.session.commit()
    return jsonify({'success': True})


@commissioner_bp.route('/api/verify_n2', methods=['POST'])
def api_verify_n2():
    """Verify N2 fingerprint during counting phase."""
    n2_code     = request.json.get('n2_code', '').strip().upper()
    fingerprint = tth(n2_code)
    entry       = N2Fingerprint.query.filter_by(fingerprint=fingerprint).first()
    if entry:
        return jsonify({'valid': True, 'fingerprint': fingerprint})
    return jsonify({'valid': False, 'fingerprint': fingerprint})


@commissioner_bp.route('/api/tth_demo', methods=['POST'])
def api_tth_demo():
    """Return detailed TTH computation steps for educational display."""
    text  = request.json.get('text', '')
    steps = tth_steps(text)
    return jsonify(steps)
