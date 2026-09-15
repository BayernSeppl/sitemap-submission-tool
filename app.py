#!/usr/bin/env python3
"""
Sitemap Submission Tool - Automatisches Eintragungs-Tool für 10 Suchmaschinen
"""

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
import logging
import threading
import os

# Konfiguration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///submissions.db'
app.config['SECRET_KEY'] = 'sitemap-submission-2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DATENBANK ====================

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    sitemap_url = db.Column(db.String(500), nullable=False)
    search_engine = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='pending')
    message = db.Column(db.String(500), default='')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_code = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'sitemap_url': self.sitemap_url,
            'search_engine': self.search_engine,
            'status': self.status,
            'message': self.message,
            'submitted_at': self.submitted_at.strftime('%d.%m.%Y %H:%M:%S'),
            'response_code': self.response_code
        }

# ==================== SUCHMASCHINEN ====================

SEARCH_ENGINES = {
    'google': {'name': 'Google Search Console', 'endpoint': 'https://www.google.com/ping', 'param': 'sitemap', 'method': 'GET'},
    'bing': {'name': 'Bing Webmaster Tools', 'endpoint': 'https://www.bing.com/webmaster/ping.aspx', 'param': 'sitemap', 'method': 'GET'},
    'yandex': {'name': 'Yandex Webmaster', 'endpoint': 'https://blogs.yandex.ru/pings/', 'param': 'blogs', 'method': 'GET'},
    'baidu': {'name': 'Baidu Search', 'endpoint': 'https://data.zhanzhang.baidu.com/urls', 'param': 'url', 'method': 'POST'},
    'duckduckgo': {'name': 'DuckDuckGo', 'endpoint': 'https://duckduckgo.com/ping', 'param': 'sitemap', 'method': 'GET'},
    'ask': {'name': 'Ask.com', 'endpoint': 'https://submissions.ask.com/ping', 'param': 'sitemap', 'method': 'GET'},
    'sogou': {'name': 'Sogou Search', 'endpoint': 'https://www.sogou.com/sogou', 'param': 'url', 'method': 'POST'},
    'ecosia': {'name': 'Ecosia', 'endpoint': 'https://www.ecosia.org/ping', 'param': 'sitemap', 'method': 'GET'},
    'qwant': {'name': 'Qwant', 'endpoint': 'https://www.qwant.com/qwant/ping', 'param': 'sitemap', 'method': 'GET'},
    'startpage': {'name': 'Startpage', 'endpoint': 'https://www.startpage.com/ping', 'param': 'sitemap', 'method': 'GET'}
}

# ==================== FUNKTIONEN ====================

def submit_to_search_engine(website_url, sitemap_url, engine_key):
    """Submittet Sitemap an eine Suchmaschine"""
    engine = SEARCH_ENGINES.get(engine_key)
    if not engine:
        return False, f"Unbekannte Suchmaschine: {engine_key}", 0

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        if engine['method'] == 'GET':
            params = {engine['param']: sitemap_url}
            response = requests.get(engine['endpoint'], params=params, headers=headers, timeout=10)
        else:
            data = {engine['param']: sitemap_url}
            response = requests.post(engine['endpoint'], data=data, headers=headers, timeout=10)

        success = response.status_code in [200, 201, 202, 204]
        message = f"Status: {response.status_code}"
        logger.info(f"{engine['name']}: {message}")
        return success, message, response.status_code

    except Exception as e:
        logger.error(f"Error with {engine['name']}: {str(e)}")
        return False, str(e), 0

def submit_sitemap_async(website_url, sitemap_url, engines):
    """Submittet asynchron"""
    for engine_key in engines:
        success, message, status_code = submit_to_search_engine(website_url, sitemap_url, engine_key)
        submission = Submission(
            url=website_url,
            sitemap_url=sitemap_url,
            search_engine=SEARCH_ENGINES[engine_key]['name'],
            status='success' if success else 'failed',
            message=message,
            response_code=status_code
        )
        db.session.add(submission)
        db.session.commit()

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html', search_engines=SEARCH_ENGINES)

@app.route('/api/submit', methods=['POST'])
def api_submit():
    data = request.get_json()
    website_url = data.get('website_url', '').strip()
    sitemap_url = data.get('sitemap_url', '').strip()
    engines = data.get('engines', [])

    if not website_url or not sitemap_url or not engines:
        return jsonify({'error': 'Alle Felder erforderlich'}), 400

    if not sitemap_url.startswith('http'):
        sitemap_url = f"https://{sitemap_url}"
    if not website_url.startswith('http'):
        website_url = f"https://{website_url}"

    thread = threading.Thread(
        target=submit_sitemap_async,
        args=(website_url, sitemap_url, engines),
        daemon=True
    )
    thread.start()

    return jsonify({
        'message': 'Submission gestartet!',
        'website_url': website_url,
        'sitemap_url': sitemap_url,
        'engines_count': len(engines)
    })

@app.route('/api/submissions', methods=['GET'])
def api_submissions():
    page = request.args.get('page', 1, type=int)
    submissions = Submission.query.order_by(Submission.submitted_at.desc()).paginate(page=page, per_page=50)
    return jsonify({
        'submissions': [s.to_dict() for s in submissions.items],
        'total': submissions.total,
        'pages': submissions.pages,
        'current_page': page
    })

@app.route('/api/stats', methods=['GET'])
def api_stats():
    total = Submission.query.count()
    successful = Submission.query.filter_by(status='success').count()
    failed = Submission.query.filter_by(status='failed').count()
    return jsonify({
        'total_submissions': total,
        'successful': successful,
        'failed': failed,
        'success_rate': round((successful / total * 100) if total > 0 else 0, 2)
    })

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    Submission.query.delete()
    db.session.commit()
    return jsonify({'message': 'Verlauf gelöscht'})

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("\n" + "="*60)
    print("🚀 Sitemap Submission Tool")
    print("="*60)
    print("📍 Öffne: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=False, host='127.0.0.1', port=5000)
