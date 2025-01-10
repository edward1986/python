import requests
import subprocess
import logging
import random
import time
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

def send_email_with_attachment(recipient_email, subject, content, attachment_path):
    """Send the generated blog content and image via email."""
    try:
        sender_email = "edwardlorilla2013@gmail.com"
        sender_password = "giax bwty esxw dquw"

        # Set up the MIME message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject.replace("\n", " ").strip()

        # Attach the blog content
        message.attach(MIMEText(content, "plain"))

        # Attach the image
        if attachment_path:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={attachment_path.split('/')[-1]}",
            )
            message.attach(part)

        # Connect to the SMTP server
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(f"Email sent successfully to {recipient_email}.")
    except Exception as e:
        print(f"Error sending email: {e}")

def download_image(image_url, output_path):
    """Download an image from the given URL and save it to the specified path."""
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(output_path, 'wb') as file:
            file.write(response.content)
        print(f"Image downloaded successfully to {output_path}.")
    else:
        raise Exception(f"Failed to download image: {response.status_code}")

def generate_pollinations_image(prompt, width=768, height=768, seed=42, model='flux', output_path='generated_image.jpg'):
    """Generate an image using Pollinations API and download it."""
    try:
        image_url = f"https://pollinations.ai/p/{prompt}?width={width}&height={height}&seed={seed}&model={model}"
        download_image(image_url, output_path)
        return output_path
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None

def generate_content(prompt):
    """Generate content using the Ollama model."""
    result = subprocess.run(
        ["ollama", "run", "llama3", prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Error generating content: {result.stderr.strip()}")
    return result.stdout.strip()

def fetch_stackoverflow_questions(tag="python"):
    """Fetch questions tagged with a specific tag from Stack Overflow."""
    url = "https://api.stackexchange.com/2.3/questions"
    params = {
        "order": "desc",
        "sort": "activity",
        "tagged": tag,
        "site": "stackoverflow",
        "filter": "withbody"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch questions: {response.status_code}")

    data = response.json()
    if not data.get("items"):
        raise Exception("No questions found.")

    return data["items"]

def clean_question_data(questions):
    """Clean and format question data for easier readability."""
    cleaned_questions = []
    for question in questions:
        if question['is_answered']:
            soup = BeautifulSoup(question['body'], 'html.parser')
            clean_text = f"Title: {question['title']}\n\nBody:\n{soup.get_text().strip()}"
            cleaned_questions.append({
                "id": question['question_id'],
                "title": question['title'],
                "body": soup.get_text().strip(),
                "link": question['link'],
                "cleaned_text": clean_text
            })
    return cleaned_questions

def store_question_id(question_id, file_path="sent_questions.json"):
    """Store the ID of the sent question to avoid repetition."""
    try:
        # Load existing IDs
        try:
            with open(file_path, "r") as file:
                sent_ids = json.load(file)
        except FileNotFoundError:
            sent_ids = []

        # Append the new ID and save
        sent_ids.append(question_id)
        with open(file_path, "w") as file:
            json.dump(sent_ids, file)

        print(f"Stored question ID {question_id}.")

        # Push changes to GitHub
        os.system("git add sent_questions.json")
        os.system("git commit -m 'Update sent questions list'")
        os.system("git push")
    except Exception as e:
        print(f"Error storing question ID: {e}")

def main():
    try:
        # Fetch and clean Stack Overflow questions
        questions = fetch_stackoverflow_questions(tag="python")
        cleaned_questions = clean_question_data(questions)

        if not cleaned_questions:
            logger.info("No answered questions found.")
            return

        # Select a random cleaned question
        selected_question = random.choice(cleaned_questions)
        logger.info(f"Selected Question: {selected_question['title']} (ID: {selected_question['id']})")

        # Prepare the prompt
        prompt = f"Generate a response to the following Stack Overflow question:\n\n{selected_question['cleaned_text']}"

        # Generate content using Ollama
        response_content = generate_content(prompt)

        # Generate an image using Pollinations AI
        image_path = generate_pollinations_image(prompt=selected_question['title'])

        recipients = [
            "edwardlance.lorilla.edwardlancelorilla@blogger.com",
        ]
        for recipient in recipients:
            send_email_with_attachment(
                recipient_email=recipient,
                subject=selected_question['title'],
                content=response_content,
                attachment_path=image_path if image_path else None
            )

        # Store the question ID
        store_question_id(selected_question['id'])

        time.sleep(10)  # Respect API rate limits
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
