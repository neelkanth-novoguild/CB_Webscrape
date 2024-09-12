import subprocess
import threading
import re
import csv


def getClipboardData():
    p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
    retcode = p.wait()
    data = p.stdout.read()
    return data.decode('utf-8')


clip = getClipboardData()


def parse_resume(text):
    
    name = re.search(r'(?:Name:|^)\s*(.*)', text, re.IGNORECASE)
    email = re.search(r'[\w\.-]+@[\w\.-]+', text) 
    phone = re.search(r'\(?\b[0-9]{3}[-.\s)]*[0-9]{3}[-.\s]*[0-9]{4}\b', text)  
    skills = re.search(r'(?:Skills:|Technical Skills:|Skills\n)(.*)', text, re.IGNORECASE | re.DOTALL)
    experience = re.search(r'(?:Experience:|Work Experience:|Professional Experience:|Experience\n)(.*)', text, re.IGNORECASE | re.DOTALL)

    return {
        'name': name.group(1) if name else 'N/A',
        'email': email.group(0) if email else 'N/A',
        'phone': phone.group(0) if phone else 'N/A',
        'skills': skills.group(1).strip() if skills else 'N/A',
        'experience': experience.group(1).strip() if experience else 'N/A'
    }


def check_for_clipboard_change():
    global clip

    threading.Timer(0.5, check_for_clipboard_change).start()

    clip2 = getClipboardData()

    if clip != clip2:
        clip = clip2
        print('Clipboard changed, parsing resume.')

        parsed_data = parse_resume(clip)

        with open('../data/resume_data.csv', 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['name', 'email', 'phone', 'skills', 'experience'])
            writer.writerow(parsed_data)


check_for_clipboard_change()
