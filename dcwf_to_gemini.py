#!/usr/bin/env python3
"""
DCWF Task PDF Generator & Gemini Uploader

Reads DCWF tasks from Excel, generates PDF summaries with semantic mapping clues,
and uploads to Gemini file store.

Usage:
    python dcwf_to_gemini.py --gemini-key YOUR_GEMINI_KEY --input DCWFMASTER.xlsx
"""

import argparse
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


def call_gemini_api(api_key: str, prompt: str, model: str = "gemini-2.5-flash-lite", max_retries: int = 3) -> str:
    """Call Gemini API and return response text with retry logic."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000
        }
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from Gemini response
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    
                    # Check if response was truncated
                    finish_reason = candidate.get('finishReason', '')
                    if finish_reason == 'MAX_TOKENS':
                        raise Exception(f"Response truncated due to MAX_TOKENS limit. Increase maxOutputTokens.")
                    
                    if 'content' in candidate:
                        content = candidate['content']
                        # Check if content has parts
                        if 'parts' in content:
                            if len(content['parts']) > 0:
                                text = content['parts'][0].get('text', '')
                                if text:
                                    return text
                        # If no parts but has role, might be empty/incomplete response
                        elif 'role' in content:
                            raise Exception(f"Response incomplete - content has role but no parts. Finish reason: {finish_reason}")
                
                raise Exception(f"Unexpected Gemini API response format: {result}")
            else:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                raise  # Re-raise keyboard interrupts immediately
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            raise Exception(f"Network error after {max_retries} attempts: {e}")
        except Exception as e:
            # Catch any other exceptions and re-raise
            raise
    
    raise Exception(f"Failed after {max_retries} attempts")


def read_dcwf_tasks(file_path: str) -> pd.DataFrame:
    """Read DCWF tasks from Excel file."""
    df = pd.read_excel(file_path, sheet_name='Master Task & KSA List')
    df_clean = df[['DCWF #', 'DESCRIPTION']].dropna(subset=['DCWF #', 'DESCRIPTION'])
    df_clean.columns = ['task_id', 'description']
    df_clean['task_id'] = df_clean['task_id'].astype(str)
    print(f"Loaded {len(df_clean)} DCWF tasks")
    return df_clean


def generate_task_content(gemini_key: str, task_id: str, description: str, model: str = "gemini-2.5-flash-lite") -> dict:
    """Generate comprehensive task summary with semantic clues."""
    
    prompt = f"""You are an expert in the DCWF (Defense Cybersecurity Workforce Framework) and AI's impact on cybersecurity work.

For this DCWF task, generate a comprehensive summary that will be used for semantic search and artifact mapping. This knowledge base will be used by an AI agent via RAG (Retrieval Augmented Generation) to analyze artifacts (documents, articles, job postings, etc.) and determine how AI tools affect those artifacts.

TASK ID: {task_id}
TASK DESCRIPTION: {description}

Provide the following in JSON format:

{{
    "task_overview": "2-3 sentence summary of what this task involves and why it matters",
    
    "semantic_keywords": ["list", "of", "15-20", "keywords", "for", "vector", "similarity", "matching"],
    
    "artifact_mapping_clues": [
        "Phrase or pattern that would appear in articles about this task",
        "Another indicator phrase for semantic matching",
        "Technical terms that signal relevance to this task",
        "Industry buzzwords associated with this work",
        "5-8 total clues for artifact matching"
    ],
    
    "associated_job_titles": [
        "Job Title 1 (Entry Level)",
        "Job Title 2 (Mid Level)", 
        "Job Title 3 (Senior Level)",
        "4-6 relevant job titles"
    ],
    
    "relevant_ai_tools": [
        "AI Tool/Platform 1 - brief description of how it relates",
        "AI Tool/Platform 2 - brief description",
        "3-5 AI tools that could automate or augment this task"
    ],
    
    "ai_impact_clues_for_artifacts": {{
        "how_ai_affects_artifacts": "2-3 sentences describing how AI tools would impact artifacts (documents, job postings, articles) related to this task. Focus on what changes would appear in artifacts - e.g., new skills mentioned, tools referenced, job descriptions modified, etc.",
        "artifact_indicators": [
            "Specific phrases or terms that would appear in AI-affected artifacts",
            "Skills or tools that would be mentioned in job postings",
            "Changes in language or requirements in documents",
            "5-7 specific indicators that an artifact relates to AI-impacted work for this task"
        ],
        "classification_hints": "Guidance for the AI agent: When analyzing artifacts related to this task, look for these patterns to determine if AI would Replace, Augment, or create New requirements. Do NOT classify the task itself - provide clues for artifact analysis."
    }},
    
    "related_dcwf_tasks": ["List of 3-5 task IDs or descriptions that commonly accompany this task"],
    
    "required_skills": ["Skill 1", "Skill 2", "5-7 key skills needed"]
}}

Respond ONLY with valid JSON, no markdown formatting."""

    # Add system instruction to the prompt
    full_prompt = "You are a cybersecurity workforce expert. Respond only with valid JSON.\n\n" + prompt
    
    content = call_gemini_api(gemini_key, full_prompt, model)
    # Clean up potential markdown
    content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON for task {task_id}. Raw content: {content[:200]}...")
        return {
            "task_overview": content,
            "semantic_keywords": [],
            "artifact_mapping_clues": [],
            "associated_job_titles": [],
            "relevant_ai_tools": [],
            "ai_impact_clues_for_artifacts": {
                "how_ai_affects_artifacts": "Parse error",
                "artifact_indicators": [],
                "classification_hints": ""
            },
            "related_dcwf_tasks": [],
            "required_skills": []
        }


def create_pdf_styles():
    """Create PDF styles."""
    styles = getSampleStyleSheet()
    
    # Helper function to safely add styles
    def add_style(name, **kwargs):
        if name not in styles.byName:
            styles.add(ParagraphStyle(name=name, **kwargs))
    
    add_style('TaskTitle', parent=styles['Heading1'],
              fontSize=14, spaceAfter=6, alignment=TA_CENTER, textColor=HexColor('#1a365d'))
    
    add_style('TaskID', parent=styles['Normal'],
              fontSize=11, alignment=TA_CENTER, textColor=HexColor('#2c5282'), spaceAfter=10)
    
    add_style('Section', parent=styles['Heading2'],
              fontSize=11, spaceBefore=10, spaceAfter=4, textColor=HexColor('#2c5282'))
    
    add_style('Body', parent=styles['Normal'],
              fontSize=9, leading=12, alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=2)
    
    add_style('Bullet', parent=styles['Normal'],
              fontSize=9, leading=11, leftIndent=15, spaceBefore=1, spaceAfter=1)
    
    add_style('Keywords', parent=styles['Normal'],
              fontSize=8, textColor=HexColor('#4a5568'), spaceAfter=8)
    
    add_style('Footer', parent=styles['Normal'],
              fontSize=7, textColor=HexColor('#718096'), alignment=TA_CENTER)
    
    return styles


def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    for c in invalid:
        name = name.replace(c, '_')
    return name[:60].strip()


def create_task_pdf(task_id: str, description: str, content: dict, output_path: str, styles):
    """Generate PDF for a DCWF task."""
    
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=0.5*inch, leftMargin=0.5*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch
    )
    
    story = []
    
    # Header
    story.append(Paragraph("DCWF Task Summary", styles['TaskTitle']))
    story.append(Paragraph(f"Task ID: {task_id}", styles['TaskID']))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#2c5282')))
    story.append(Spacer(1, 6))
    
    # Task Description
    story.append(Paragraph("<b>Task Description</b>", styles['Section']))
    story.append(Paragraph(description, styles['Body']))
    
    # Overview
    if content.get('task_overview'):
        story.append(Paragraph("<b>Overview</b>", styles['Section']))
        story.append(Paragraph(content['task_overview'], styles['Body']))
    
    # Semantic Keywords (for vector matching)
    if content.get('semantic_keywords'):
        story.append(Paragraph("<b>Semantic Keywords (for Vector Similarity)</b>", styles['Section']))
        keywords = ", ".join(content['semantic_keywords'])
        story.append(Paragraph(f"<i>{keywords}</i>", styles['Keywords']))
    
    # Artifact Mapping Clues
    if content.get('artifact_mapping_clues'):
        story.append(Paragraph("<b>Artifact Mapping Clues</b>", styles['Section']))
        for clue in content['artifact_mapping_clues']:
            story.append(Paragraph(f"• {clue}", styles['Bullet']))
    
    # Job Titles
    if content.get('associated_job_titles'):
        story.append(Paragraph("<b>Associated Job Titles</b>", styles['Section']))
        for title in content['associated_job_titles']:
            story.append(Paragraph(f"• {title}", styles['Bullet']))
    
    # AI Tools
    if content.get('relevant_ai_tools'):
        story.append(Paragraph("<b>Relevant AI Tools</b>", styles['Section']))
        for tool in content['relevant_ai_tools']:
            story.append(Paragraph(f"• {tool}", styles['Bullet']))
    
    # AI Impact Clues for Artifacts
    if content.get('ai_impact_clues_for_artifacts'):
        ai_clues = content['ai_impact_clues_for_artifacts']
        story.append(Paragraph("<b>AI Impact Clues for Artifacts</b>", styles['Section']))
        story.append(Paragraph(f"<b>How AI Affects Artifacts:</b> {ai_clues.get('how_ai_affects_artifacts', 'N/A')}", styles['Body']))
        
        if ai_clues.get('artifact_indicators'):
            story.append(Paragraph("<b>Artifact Indicators:</b>", styles['Section']))
            for indicator in ai_clues['artifact_indicators']:
                story.append(Paragraph(f"• {indicator}", styles['Bullet']))
        
        if ai_clues.get('classification_hints'):
            story.append(Paragraph("<b>Classification Hints for AI Agent:</b>", styles['Section']))
            story.append(Paragraph(ai_clues['classification_hints'], styles['Body']))
    
    # Required Skills
    if content.get('required_skills'):
        story.append(Paragraph("<b>Required Skills</b>", styles['Section']))
        skills = ", ".join(content['required_skills'])
        story.append(Paragraph(skills, styles['Body']))
    
    # Related Tasks
    if content.get('related_dcwf_tasks'):
        story.append(Paragraph("<b>Related DCWF Tasks</b>", styles['Section']))
        for task in content['related_dcwf_tasks']:
            story.append(Paragraph(f"• {task}", styles['Bullet']))
    
    # Footer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#cbd5e0')))
    story.append(Paragraph(
        f"AI Horizon Forecasting Pipeline | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles['Footer']
    ))
    
    doc.build(story)


def upload_to_gemini(pdf_path: str, gemini_key: str, store_name: str = "test-cgav96x669ld", max_retries: int = 3) -> dict:
    """Upload PDF to Gemini Files API, then import into file search store."""
    
    filename = os.path.basename(pdf_path)
    file_size = os.path.getsize(pdf_path)
    
    # Step 1: Upload file using Files API
    upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={gemini_key}"
    
    file_name = None
    for attempt in range(max_retries):
        try:
            with open(pdf_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/pdf')
                }
                
                # Optional: include display name in metadata
                data = {
                    'name': filename  # Display name for citations
                }
                
                response = requests.post(
                    upload_url,
                    files=files,
                    data=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    upload_result = response.json()
                    # Get the file name (resource name like "files/abc123")
                    file_name = upload_result.get('file', {}).get('name', '')
                    if not file_name:
                        # Try alternative response structure
                        file_name = upload_result.get('name', '')
                    
                    if file_name:
                        break
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    return {"success": False, "error": f"File upload failed: {response.text}"}
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            return {"success": False, "error": f"Network error during file upload: {e}"}
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            return {"success": False, "error": f"File upload error: {str(e)}"}
    
    if not file_name:
        return {"success": False, "error": "No file name returned after upload"}
    
    # Step 2: Import file into file search store
    store_path = f"fileSearchStores/{store_name}"
    base_url = f"https://generativelanguage.googleapis.com/v1beta/{store_path}:importFile"
    
    # URL encode file_name for query parameters (it contains slashes like "files/abc123")
    from urllib.parse import quote
    file_name_encoded = quote(file_name, safe='')
    
    # According to docs, import_file takes file_name parameter
    # Try different approaches: query parameter vs JSON body with different field names
    import_attempts = [
        # Try in JSON body with different field names (most likely)
        {"url": f"{base_url}?key={gemini_key}", "json": {"file_name": file_name}},
        {"url": f"{base_url}?key={gemini_key}", "json": {"fileName": file_name}},
        {"url": f"{base_url}?key={gemini_key}", "json": {"file": file_name}},
        # Try as query parameter (URL encoded)
        {"url": f"{base_url}?key={gemini_key}&file_name={file_name_encoded}", "json": None},
        {"url": f"{base_url}?key={gemini_key}&fileName={file_name_encoded}", "json": None},
    ]
    
    last_error = None
    for attempt in range(max_retries):
        for import_attempt in import_attempts:
            try:
                headers = {"Content-Type": "application/json"} if import_attempt["json"] else {}
                
                import_response = requests.post(
                    import_attempt["url"],
                    headers=headers,
                    json=import_attempt["json"],
                    timeout=60
                )
                
                if import_response.status_code == 200:
                    result = import_response.json()
                    operation_name = result.get('name', '')
                    return {"success": True, "operation_name": operation_name, "file_uri": file_name}
                elif import_response.status_code == 400:
                    # Try next format
                    last_error = import_response.text
                    continue
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    break
                else:
                    last_error = import_response.text
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    break
                return {"success": False, "error": f"Network error during import: {e}", "file_uri": file_name}
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    break
                return {"success": False, "error": f"Import error: {str(e)}", "file_uri": file_name}
    
    return {"success": False, "error": f"Import failed: {last_error}", "file_uri": file_name}


def main():
    parser = argparse.ArgumentParser(description='Generate DCWF task PDFs and upload to Gemini')
    parser.add_argument('--gemini-key', required=True, help='Gemini API key')
    parser.add_argument('--input', required=True, help='Path to DCWFMASTER.xlsx')
    parser.add_argument('--output', default='./dcwf_pdfs_gemini25/', help='Output directory for PDFs')
    parser.add_argument('--store', default='test-cgav96x669ld', help='Gemini file store name')
    parser.add_argument('--model', default='gemini-2.5-flash-lite', help='Gemini model (default: gemini-2.5-flash-lite)')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between tasks (seconds)')
    parser.add_argument('--start', type=int, default=0, help='Start from task index')
    parser.add_argument('--limit', type=int, help='Limit number of tasks to process')
    parser.add_argument('--skip-upload', action='store_true', help='Skip Gemini upload (PDF only)')
    
    args = parser.parse_args()
    
    # Setup
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    styles = create_pdf_styles()
    
    # Load tasks
    df = read_dcwf_tasks(args.input)
    
    # Apply start/limit
    if args.limit:
        df = df.iloc[args.start:args.start + args.limit]
    else:
        df = df.iloc[args.start:]
    
    total = len(df)
    print(f"\nProcessing {total} tasks...")
    print("=" * 60)
    
    # Track results
    results = []
    successful = 0
    failed = 0
    
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        task_id = str(row['task_id'])
        description = str(row['description'])
        
        print(f"\n[{idx}/{total}] Task {task_id}")
        
        try:
            # Generate content
            print("  → Generating content with Gemini...")
            content = generate_task_content(args.gemini_key, task_id, description, args.model)
            
            # Create PDF
            safe_name = sanitize_filename(description[:40])
            pdf_filename = f"DCWF_{task_id}_{safe_name}.pdf"
            pdf_path = output_dir / pdf_filename
            
            print(f"  → Creating PDF: {pdf_filename}")
            create_task_pdf(task_id, description, content, str(pdf_path), styles)
            
            # Upload to Gemini
            if not args.skip_upload:
                print("  → Uploading to Gemini file store...")
                try:
                    upload_result = upload_to_gemini(str(pdf_path), args.gemini_key, args.store)
                    
                    if upload_result['success']:
                        print(f"  ✓ Uploaded: {upload_result.get('operation_name', 'OK')}")
                    else:
                        error_msg = upload_result.get('error', 'Unknown')
                        print(f"  ⚠ Upload issue: {error_msg}")
                        # If upload consistently fails, suggest skipping uploads
                        if "Cannot find field" in str(error_msg):
                            print(f"  💡 Tip: Upload API format issue. PDFs are saved locally. Use --skip-upload to skip uploads.")
                except KeyboardInterrupt:
                    raise  # Re-raise keyboard interrupts
                except Exception as e:
                    print(f"  ⚠ Upload error: {e}")
                    upload_result = {"success": False, "error": str(e)}
            else:
                upload_result = {"success": True, "skipped": True}
            
            results.append({
                "task_id": task_id,
                "pdf_path": str(pdf_path),
                "upload_success": upload_result.get('success', False),
                "file_uri": upload_result.get('file_uri', ''),
                "operation_name": upload_result.get('operation_name', '')
            })
            
            successful += 1
            
            # Rate limiting
            time.sleep(args.delay)
            
        except Exception as e:
            failed += 1
            print(f"  ✗ Error: {e}")
            results.append({
                "task_id": task_id,
                "error": str(e)
            })
    
    # Save results log
    log_path = output_dir / "upload_log.json"
    with open(log_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total: {total} | Success: {successful} | Failed: {failed}")
    print(f"PDFs saved to: {output_dir.absolute()}")
    print(f"Log saved to: {log_path}")


if __name__ == "__main__":
    main()
