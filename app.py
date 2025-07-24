from flask import Flask, render_template, request, send_from_directory, Response, session, redirect, url_for
import os
import json
import time
import uuid
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.resume_reader import extract_resume_texts
from utils.gemini_ranker import rank_resumes_with_gemini
from utils.generate_pdf_report import generate_pdf_report

app = Flask(__name__)

TEMP_DIR='temp'
RESULTS_DIR='results'
UPLOAD_DIR='resumes'


load_dotenv()
app.secret_key = api_key=os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['TEMP'] = TEMP_DIR
os.makedirs(app.config['TEMP'], exist_ok=True)
app.config['RESULTS'] = RESULTS_DIR
os.makedirs(app.config['RESULTS'], exist_ok=True)


def cleanup_dirs():
    """Clean up old files"""
    cutoff_time = datetime.now() - timedelta(hours=1)
    for filename in os.listdir(TEMP_DIR):
        if filename.endswith('.pkl'):
            filepath = os.path.join(TEMP_DIR, filename)
            try:
                    if os.path.getctime(filepath) < cutoff_time.timestamp():
                        os.remove(filepath)
            except:
                pass

    for filename in os.listdir(RESULTS_DIR):
        if filename.endswith('.pdf'):
            filepath = os.path.join(RESULTS_DIR, filename)
            try:
                if os.path.getctime(filepath) < cutoff_time.timestamp():
                    os.remove(filepath)
            except:
                pass

    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith('.pdf'):
            filepath = os.path.join(UPLOAD_DIR, filename)
            try:
                    os.remove(filepath)
            except:
                pass

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        job_description = request.form['job_description']
        files = request.files.getlist('resumes')

        filepaths = []
        for file in files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            filepaths.append(filepath)

        resume_texts = extract_resume_texts(filepaths)
        ranked = rank_resumes_with_gemini(job_description, resume_texts)

        pdf_filename = "ranked_resumes.pdf"
        generate_pdf_report(ranked, output_path=RESULTS_DIR + "/" + pdf_filename)

        return render_template(
            'results.html',
            results=ranked,
            query=job_description,
            pdf_link=f"/download/{pdf_filename}"
        )

    return render_template('index.html')

@app.route('/process_with_progress', methods=['POST'])
def process_with_progress():
    """Stream resume processing progress using Server-Sent Events"""
    
    # Extract request data AND save files
    job_description = request.form['job_description']
    files = request.files.getlist('resumes')
    session_id = str(uuid.uuid4())
    
    # Save files immediately while request context is active
    filepaths = []
    for file in files:
        if file.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            filepaths.append(filepath)
    
    def generate_progress():
        try:
            if not filepaths:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No files uploaded'})}\n\n"
                return

            total_files = len(filepaths)

            # Extraction phase
            resume_texts = []

            for i, filepath in enumerate(filepaths):
                filename = os.path.basename(filepath)
                single_file_texts = extract_resume_texts([filepath])
                resume_texts.extend(single_file_texts)

            # AI analysis phase
            ranked_results = []
            for i, resume in enumerate(resume_texts):
                filename = resume.get('filename', f'Resume {i+1}')
                yield f"data: {json.dumps({'type': 'progress', 'processed': i, 'total': total_files, 'current_file': f'Analyzing {filename}', 'stage': 'ai_analysis'})}\n\n"
                result = rank_resumes_with_gemini(job_description, resume)
                ranked_results.append(result)
                time.sleep(1)

            # Report phase            
            ranked_results = sorted(ranked_results, key=lambda x: x['score'], reverse=True)
            pdf_filename = f"ranked_resumes_{session_id}.pdf"
            generate_pdf_report(ranked_results, output_path=RESULTS_DIR + "/" + pdf_filename)

            # Store results in temporary file
            result_data = {
                'results': ranked_results,
                'query': job_description,
                'pdf_link': f"/download/{pdf_filename}",
                'timestamp': datetime.now().isoformat()
            }
            
            result_file = os.path.join(TEMP_DIR, f"{session_id}.pkl")
            with open(result_file, 'wb') as f:
                pickle.dump(result_data, f)
            
            # Clean up old results
            cleanup_dirs()

            yield f"data: {json.dumps({'type': 'complete', 'redirect_url': f'/results/{session_id}'})}\n\n"

        except Exception as e:
            error_data = {'type': 'error', 'message': f'An error occurred: {str(e)}'}
            yield f"data: {json.dumps(error_data)}\n\n"

    return Response(generate_progress(), mimetype='text/plain')

@app.route('/results')
def results():
    """Original results route for backward compatibility"""
    if 'results' not in session:
        return redirect(url_for('index'))
    
    return render_template(
        'results.html',
        results=session['results'],
        query=session['query'],
        pdf_link=session['pdf_link']
    )

@app.route('/results/<session_id>')
def results_with_session(session_id):
    """New results route that uses session ID"""
    try:
        result_file = os.path.join(TEMP_DIR, f"{session_id}.pkl")
        
        if not os.path.exists(result_file):
            return "Results not found or expired. Please process your resumes again.", 404
            
        with open(result_file, 'rb') as f:
            result_data = pickle.load(f)
        
        return render_template(
            'results.html',
            results=result_data['results'],
            query=result_data['query'],
            pdf_link=result_data['pdf_link']
        )
        
    except Exception as e:
        return f"Error loading results: {str(e)}", 500

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(directory=RESULTS_DIR, path=filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)