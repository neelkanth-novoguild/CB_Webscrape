import subprocess
import threading
import re
import psycopg2
import random


API_KEYS = [
    'api_key_1',
    'api_key_2',
    'api_key_3'
]

clip = ""


def get_clipboard_data():
    p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
    retcode = p.wait()
    data = p.stdout.read()
    return data.decode('utf-8')


def connect_to_db():
    try:
        connection = psycopg2.connect(
            host="localhost", 
            database="your_database_name",  
            user="your_username", 
            password="your_password" 
        )
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


def insert_resume_to_db(parsed_data, connection):
    api_key = random.choice(API_KEYS)
    print(f'Using API Key: {api_key}')
    
    try:
        with connection.cursor() as cursor:
            insert_query = """
            INSERT INTO resumes (name, email, phone, skills, experience)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                skills = EXCLUDED.skills,
                experience = EXCLUDED.experience;
            """
            cursor.execute(insert_query, (
                parsed_data['name'],
                parsed_data['email'],
                parsed_data['phone'],
                parsed_data['skills'],
                parsed_data['experience']
            ))
            connection.commit()
            print(f"Resume data for {parsed_data['name']} inserted into the database.")
    except Exception as e:
        print(f"Error inserting resume data: {e}")


def parse_resume(text):
    name = re.search(r'(?:Name:|^)\s*(.*)', text, re.IGNORECASE)
    email = re.search(r'[\w\.-]+@[\w\.-]+', text)
    phone = re.search(r'\(?\b[0-9]{3}[-.\s)]*[0-9]{3}[-.\s]*[0-9]{4}\b', text)
    skills = re.search(r'(?:Skills:|Technical Skills:|Skills\n)(.*)', text, re.IGNORECASE | re.DOTALL)
    experience = re.search(r'(?:Experience:|Work Experience:|Professional Experience:|Experience\n)(.*)', text, re.IGNORECASE | re.DOTALL)

    return {
        'name': name.group(1).strip() if name else 'N/A',
        'email': email.group(0) if email else 'N/A',
        'phone': phone.group(0) if phone else 'N/A',
        'skills': skills.group(1).strip() if skills else 'N/A',
        'experience': experience.group(1).strip() if experience else 'N/A'
    }


def check_for_clipboard_change(connection):
    global clip

    threading.Timer(0.5, check_for_clipboard_change, args=[connection]).start()

    clip2 = get_clipboard_data()

    if clip != clip2:
        clip = clip2
        print('Clipboard changed, parsing resume.')

        parsed_data = parse_resume(clip)

        insert_resume_to_db(parsed_data, connection)


if __name__ == "__main__":
    connection = connect_to_db()
    if connection:
        check_for_clipboard_change(connection)
    else:
        print("Failed to connect to the database. Exiting.")
