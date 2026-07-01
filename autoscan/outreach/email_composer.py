import json
import os
from google import genai
from google.genai import types

TRACKER_URL = os.getenv("TRACKER_URL", "http://localhost:8000")

class EmailComposer:
    def __init__(self, api_key: str, model: str = 'gemini-2.5-flash'):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _get_top_finding(self, findings):
        if not findings:
            return None
        sorted_findings = sorted(
            findings, 
            key=lambda f: 0 if f.severity.lower() == 'critical' else 1 if f.severity.lower() == 'high' else 2
        )
        return sorted_findings[0]

    def compose_initial_email(self, company, contact, findings, report_url: str, price: float, email_id: int = None) -> dict:
        num_issues = len(findings)
        top_finding = self._get_top_finding(findings)
        
        top_finding_title = top_finding.title if top_finding else "multiple vulnerabilities"
        top_finding_file = top_finding.file_path if top_finding and top_finding.file_path else "multiple repositories"

        contact_name = contact.first_name or contact.email.split('@')[0]
        contact_title = contact.position or "Engineering Team"

        prompt = f"""
Write a cold outreach email to {contact_name}, {contact_title} at {company.name}.
We found {num_issues} security issues in their public GitHub repos.
Top finding: {top_finding_title} in {top_finding_file}.
Price: ${price}. Keep it under 200 words. Professional but direct.
End with one clear CTA link: {report_url}

Please return ONLY a valid JSON object with the following keys:
- "subject": The email subject line (catchy but professional).
- "html_body": The HTML formatted version of the email body. Use basic tags like <p>, <br>, <strong>.
- "text_body": The plain text version of the email body.
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert cybersecurity sales professional. You write highly converting, concise B2B cold emails. You output strict JSON without any markdown formatting."
            )
        )
        
        content = response.text
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            email_data = json.loads(content)
        except json.JSONDecodeError:
            email_data = {
                "subject": f"Security findings for {company.name}",
                "html_body": f"<p>Hi {contact_name},</p><p>We found {num_issues} security issues in your GitHub repositories. Top finding: {top_finding_title}.</p><p>View full report here: <a href='{report_url}'>{report_url}</a></p>",
                "text_body": f"Hi {contact_name},\n\nWe found {num_issues} security issues in your GitHub repositories. Top finding: {top_finding_title}.\n\nView full report here: {report_url}"
            }

        if email_id is not None:
            email_data = self.add_tracking_pixel(email_data, email_id)
            
        return email_data

    def compose_followup_email(self, company, contact, sequence_num: int, email_id: int = None) -> dict:
        contact_name = contact.first_name or contact.email.split('@')[0]
        
        if sequence_num == 2:
            angle = "Checking in on the security report we generated. Highlight the risks of unpatched vulnerabilities."
        else:
            angle = "Final attempt to connect. Ask if there's someone else on the engineering/security team to speak with."
            
        prompt = f"""
Write follow-up email #{sequence_num} to {contact_name} at {company.name}.
Angle: {angle}
Keep it under 100 words. Professional and polite.
Do not include a new CTA link unless necessary, reference the previous email.

Please return ONLY a valid JSON object with the following keys:
- "subject": The email subject line (e.g. "Re: ...")
- "html_body": The HTML formatted version of the email body.
- "text_body": The plain text version of the email body.
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert cybersecurity sales professional. Output strict JSON without markdown formatting."
            )
        )
        
        content = response.text
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            email_data = json.loads(content)
        except json.JSONDecodeError:
            email_data = {
                "subject": f"Re: Security findings for {company.name}",
                "html_body": f"<p>Hi {contact_name},</p><p>Just checking in on my previous email regarding the security findings.</p>",
                "text_body": f"Hi {contact_name},\n\nJust checking in on my previous email regarding the security findings."
            }

        if email_id is not None:
            email_data = self.add_tracking_pixel(email_data, email_id)

        return email_data
        
    def add_tracking_pixel(self, email_data: dict, email_id: int) -> dict:
        tracking_pixel = f"<img src='{TRACKER_URL}/track/open/{email_id}' width='1' height='1' />"
        if "html_body" in email_data:
            if "</body>" in email_data["html_body"]:
                email_data["html_body"] = email_data["html_body"].replace("</body>", f"{tracking_pixel}</body>")
            else:
                email_data["html_body"] += tracking_pixel
        return email_data
