import google.generativeai as genai
from dotenv import load_dotenv
import os

# 🔐 Load your Gemini API key
load_dotenv("../.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

import re

def extract_score(text):
    text = text.lower()
    match_10 = re.search(r'(\d+(\.\d+)?)\s*/\s*10', text)
    match_100 = re.search(r'(\d+(\.\d+)?)\s*/\s*100', text)
    match_1000 = re.search(r'(\d+(\.\d+)?)\s*/\s*1000', text)
    match_out_of = re.search(r'(\d+(\.\d+)?)\s*out\s*of\s*(10|100|1000)', text)
    match_percent = re.search(r'(\d+(\.\d+)?)\s*%', text)

    if match_10:
        return round(float(match_10.group(1)), 1)
    elif match_100:
        return round(float(match_100.group(1)) / 10, 1)
    elif match_1000:
        return round(float(match_1000.group(1)) / 100, 1)
    elif match_out_of:
        score = float(match_out_of.group(1))
        base = int(match_out_of.group(3))
        return round(score / base * 10, 1)
    elif match_percent:
        return round(float(match_percent.group(1)) / 10, 1)
    return 0


def rank_resumes_with_gemini(job_desc, resume):
    resume_text = resume.get('text', '')
    filename = resume.get('filename', 'Unknown')
    
    # Skip if no text content
    if not resume_text:
        print(f"Warning: No text content found for {filename}")
        return{
            'filename': filename,
            'score': 0,
            'snippet': 'No content extracted',
            'full_content': '',
            'error': 'No text content found'
        }

    prompt = f"""You are a smart recruiter assistant.

                Given this job description:
                \"\"\"{job_desc}\"\"\"

                Evaluate the following resume:
                \"\"\"{resume_text}\"\"\"

                How well does it match the job description? Give a score out of 10 and explain briefly.
                """

    try:
        response = model.generate_content(prompt)
        content = response.text

        # Parse out score
        score = extract_score(content)
        data = {
            'filename': filename,
            'score': score,
            'snippet': resume_text[:400] + '...' if len(resume_text) > 400 else resume_text,
            'full_content': resume_text,
            'ai_feedback': content
        }
        return data
        
    except Exception as e:
        print(f"Error processing {filename} with Gemini: {e}")
        return{
            'filename': filename,
            'score': 0,
            'snippet': resume_text[:400] + '...' if len(resume_text) > 400 else resume_text,
            'full_content': resume_text,
            'error': f'AI processing failed: {str(e)}'
        } 